"""
BDM Expected Utility Computation Engine.

Implements Bruce Bueno de Mesquita's expected utility model:
- Pairwise EU calculation with risk profiles
- Multi-round negotiation simulation
- Convergence and deadlock detection
- Power-weighted median outcome prediction
"""
from __future__ import annotations

import time
from decimal import Decimal
from typing import Any

from apps.engine.models import PredictionOutcome, RoundResult, SimulationRun
from apps.lookup.models import LookupValue
from apps.scenarios.models import PlayerPosition, Scenario, ScenarioIssue

# Default engine parameters
DEFAULT_PARAMS: dict[str, Any] = {
    "max_rounds": 7,
    "convergence_threshold": 0.5,
    "deadlock_detection_enabled": True,
    "deadlock_capability_balance_threshold": 0.1,
    "position_shift_dampening": 0.8,
    "flexibility_weight": 1.0,
    "salience_resistance_weight": 1.0,
    "absolute_max_rounds": 15,
}

# Risk parameter mapping: code -> r value
RISK_PARAMS: dict[str, float] = {
    "RISK_AVERSE": 0.5,
    "RISK_NEUTRAL": 1.0,
    "RISK_ACCEPTANT": 1.5,
}


def _get_risk_param(risk_code: str) -> float:
    return RISK_PARAMS.get(risk_code, 1.0)


def _risk_adjusted_utility(raw_utility: float, risk_r: float) -> float:
    """Apply BDM risk transformation: 2 - 4 * (0.5^(1-r))."""
    if abs(raw_utility) < 1e-9:
        return 0.0
    risk_multiplier = 2.0 - 4.0 * (0.5 ** (1.0 - risk_r))
    return raw_utility * risk_multiplier


def _calculate_pairwise_eu(
    pos_i: float,
    cap_i: float,
    sal_i: float,
    risk_r_i: float,
    pos_j: float,
    all_positions: list[dict],
    status_quo: float,
) -> float:
    """
    Calculate expected utility for player i of challenging player j.

    EU_i(challenge_j) = P(success) * U(win) + P(failure) * U(lose) - U(status_quo)

    P(success) = sum of (cap*sal) for players who prefer i's position over j's
                 / total (cap*sal) of all engaged players.
    """
    if abs(pos_i - pos_j) < 1e-9:
        return 0.0

    # Calculate supporting and opposing capability
    support = 0.0
    oppose = 0.0
    for p in all_positions:
        pp = p["position"]
        cp_sal = p["capability"] * p["salience"] / 10000.0  # normalize 0-1
        dist_to_i = abs(pp - pos_i)
        dist_to_j = abs(pp - pos_j)
        if dist_to_i < dist_to_j:
            support += cp_sal
        elif dist_to_j < dist_to_i:
            oppose += cp_sal
        # Equal distance: neutral, doesn't contribute

    total = support + oppose
    if total < 1e-9:
        return 0.0

    p_success = support / total
    p_failure = 1.0 - p_success

    # Utility values weighted by salience
    sal_norm = sal_i / 100.0
    u_win = abs(pos_j - pos_i) * sal_norm  # gain if we move j to our position
    u_lose = -abs(pos_j - pos_i) * sal_norm * 0.5  # cost of failed challenge
    u_sq = abs(pos_i - status_quo) * sal_norm * 0.1  # mild cost of status quo if not preferred

    raw_eu = p_success * u_win + p_failure * u_lose - u_sq
    return _risk_adjusted_utility(raw_eu, risk_r_i)


def _compute_weighted_median(positions_weights: list[tuple[float, float]]) -> float:
    """Compute power-weighted median position."""
    if not positions_weights:
        return 50.0

    sorted_pw = sorted(positions_weights, key=lambda x: x[0])
    total_weight = sum(w for _, w in sorted_pw)
    if total_weight < 1e-9:
        return sorted_pw[len(sorted_pw) // 2][0]

    half = total_weight / 2.0
    cumulative = 0.0
    for pos, weight in sorted_pw:
        cumulative += weight
        if cumulative >= half:
            return pos
    return sorted_pw[-1][0]


def _compute_weighted_mean(positions_weights: list[tuple[float, float]]) -> float:
    """Compute salience-weighted mean position."""
    total_weight = sum(w for _, w in positions_weights)
    if total_weight < 1e-9:
        return 50.0
    return sum(pos * w for pos, w in positions_weights) / total_weight


def _compute_confidence(
    positions: list[float],
    winning_pct: float,
) -> float:
    """
    Confidence = function of position convergence and winning coalition dominance.
    Tighter cluster + higher coalition dominance = higher confidence.
    """
    if not positions:
        return 0.0

    # Convergence component: inverse of standard deviation normalized to 0-1
    mean_pos = sum(positions) / len(positions)
    variance = sum((p - mean_pos) ** 2 for p in positions) / len(positions)
    std_dev = variance ** 0.5
    convergence_score = max(0.0, 1.0 - std_dev / 50.0)  # 50 = half the scale

    # Coalition dominance component
    coalition_score = min(1.0, winning_pct / 100.0)

    return round(convergence_score * 0.6 + coalition_score * 0.4, 3)


def validate_scenario(scenario: Scenario) -> list[str]:
    """Validate a scenario is ready for simulation. Returns list of errors."""
    errors: list[str] = []

    issues = list(scenario.issues.filter(is_active=True))
    if not issues:
        errors.append("Scenario must have at least one issue.")

    players = list(scenario.players.filter(is_active=True))
    if len(players) < 3:
        errors.append(f"Scenario needs at least 3 players (has {len(players)}).")

    for issue in issues:
        positions = PlayerPosition.objects.filter(
            player__in=players,
            issue=issue,
            is_active=True,
        )
        if positions.count() < len(players):
            missing = len(players) - positions.count()
            errors.append(
                f"Issue '{issue.title}': {missing} player(s) missing positions."
            )

    return errors


def compute_data_quality_score(scenario: Scenario) -> dict[str, Any]:
    """
    Calculate composite quality score (0-100):
    - Completeness (30%): all fields populated
    - Diversity (25%): spread of positions and capabilities
    - Consistency (25%): no obviously contradictory combos
    - Granularity (20%): values aren't all round numbers
    """
    issues = list(scenario.issues.filter(is_active=True))
    players = list(scenario.players.filter(is_active=True))
    all_positions = list(
        PlayerPosition.objects.filter(
            player__in=players,
            issue__in=issues,
            is_active=True,
        ).select_related('player', 'issue', 'risk_profile')
    )

    warnings: list[str] = []
    completeness = 100.0
    diversity = 100.0
    consistency = 100.0
    granularity = 100.0

    total_expected = len(players) * len(issues)

    # Completeness
    if total_expected > 0:
        completeness = (len(all_positions) / total_expected) * 100.0
    else:
        completeness = 0.0

    if len(players) < 5:
        warnings.append(f"Only {len(players)} players. Model works best with 5+.")
        completeness = min(completeness, 80.0)

    # Diversity
    if all_positions:
        pos_values = [float(p.position) for p in all_positions]
        cap_values = [float(p.capability) for p in all_positions]

        pos_range = max(pos_values) - min(pos_values) if pos_values else 0
        cap_range = max(cap_values) - min(cap_values) if cap_values else 0

        if pos_range < 5:
            diversity = 20.0
            warnings.append("All players have nearly identical positions (trivial scenario).")
        else:
            diversity = min(100.0, pos_range * 2)

        if cap_range < 5:
            diversity = min(diversity, 40.0)
            warnings.append("All players have nearly identical capability.")

        # Check for dominant player
        total_cap = sum(cap_values)
        if total_cap > 0:
            max_cap = max(cap_values)
            if max_cap / total_cap > 0.8:
                warnings.append("One player has >80% of total capability — outcome is predetermined.")
                diversity = min(diversity, 30.0)

    # Granularity: penalize if all values are multiples of 25
    if all_positions:
        round_count = sum(
            1 for p in all_positions
            if float(p.position) % 25 == 0 and float(p.capability) % 25 == 0
        )
        if round_count == len(all_positions) and len(all_positions) > 2:
            granularity = 40.0
            warnings.append("All values are round numbers. More granular estimates improve accuracy.")

    score = (
        completeness * 0.30
        + diversity * 0.25
        + consistency * 0.25
        + granularity * 0.20
    )

    return {
        "score": round(score, 1),
        "completeness": round(completeness, 1),
        "diversity": round(diversity, 1),
        "consistency": round(consistency, 1),
        "granularity": round(granularity, 1),
        "warnings": warnings,
    }


def run_simulation(
    scenario: Scenario,
    user: Any,
    params: dict[str, Any] | None = None,
) -> SimulationRun:
    """
    Execute the BDM expected utility simulation.

    1. Load all player positions for each issue.
    2. For each round: calculate pairwise EU, resolve challenges, shift positions.
    3. Check convergence / deadlock.
    4. Compute final prediction (power-weighted median).
    5. Store all results.
    """
    start_time = time.time()

    # Merge with defaults
    engine_params = {**DEFAULT_PARAMS, **(params or {})}
    max_rounds = min(
        engine_params["max_rounds"],
        engine_params["absolute_max_rounds"],
    )
    convergence_threshold = engine_params["convergence_threshold"]
    dampening = engine_params["position_shift_dampening"]
    flex_weight = engine_params["flexibility_weight"]
    sal_resist_weight = engine_params["salience_resistance_weight"]

    # Get lookup values for status
    sim_status_parent = LookupValue.objects.get(parent__isnull=True, code="SIMULATION_STATUS")
    status_running = LookupValue.objects.get(parent=sim_status_parent, code="RUNNING")
    status_completed = LookupValue.objects.get(parent=sim_status_parent, code="COMPLETED")
    status_failed = LookupValue.objects.get(parent=sim_status_parent, code="FAILED")

    stability_parent = LookupValue.objects.get(parent__isnull=True, code="OUTCOME_STABILITY")

    # Update scenario status to Running
    scenario_status_parent = LookupValue.objects.get(parent__isnull=True, code="SCENARIO_STATUS")
    scenario.status = LookupValue.objects.get(parent=scenario_status_parent, code="RUNNING")
    scenario.save(update_fields=["status", "updated_at"])

    # Create run record
    sim_run = SimulationRun.objects.create(
        scenario=scenario,
        parameters=engine_params,
        status=status_running,
        created_by=user,
    )

    try:
        issues = list(scenario.issues.filter(is_active=True))
        players = list(scenario.players.filter(is_active=True))

        # Build working data: {issue_id: {player_id: {position, capability, salience, flexibility, risk_r}}}
        working: dict[str, dict[str, dict[str, float]]] = {}
        for issue in issues:
            working[str(issue.pk)] = {}
            positions = PlayerPosition.objects.filter(
                player__in=players,
                issue=issue,
                is_active=True,
            ).select_related('player', 'risk_profile')
            for pp in positions:
                working[str(issue.pk)][str(pp.player_id)] = {
                    "position": float(pp.position),
                    "capability": float(pp.capability),
                    "salience": float(pp.salience),
                    "flexibility": float(pp.flexibility),
                    "risk_r": _get_risk_param(pp.risk_profile.code),
                }

        converged = False
        deadlock = False
        rounds_executed = 0
        round_results_bulk: list[RoundResult] = []

        for round_num in range(1, max_rounds + 1):
            rounds_executed = round_num
            max_shift = 0.0

            for issue in issues:
                issue_key = str(issue.pk)
                issue_data = working[issue_key]
                status_quo = float(issue.status_quo_position)

                # Build flat list for EU calculation
                all_pos_list = [
                    {
                        "player_id": pid,
                        "position": d["position"],
                        "capability": d["capability"],
                        "salience": d["salience"],
                    }
                    for pid, d in issue_data.items()
                ]

                # Calculate challenges and pressure for each player
                pressure_map: dict[str, float] = {pid: 0.0 for pid in issue_data}
                challenges_made_map: dict[str, int] = {pid: 0 for pid in issue_data}
                challenges_received_map: dict[str, int] = {pid: 0 for pid in issue_data}
                challenge_positions: dict[str, list[tuple[float, float]]] = {
                    pid: [] for pid in issue_data
                }

                player_ids = list(issue_data.keys())
                for i_idx, pid_i in enumerate(player_ids):
                    d_i = issue_data[pid_i]
                    for j_idx, pid_j in enumerate(player_ids):
                        if i_idx == j_idx:
                            continue
                        d_j = issue_data[pid_j]

                        eu = _calculate_pairwise_eu(
                            pos_i=d_i["position"],
                            cap_i=d_i["capability"],
                            sal_i=d_i["salience"],
                            risk_r_i=d_i["risk_r"],
                            pos_j=d_j["position"],
                            all_positions=all_pos_list,
                            status_quo=status_quo,
                        )

                        if eu > 0:
                            # Player i challenges player j
                            weight = d_i["capability"] * d_i["salience"] / 10000.0
                            pressure_map[pid_j] += eu * weight
                            challenges_made_map[pid_i] += 1
                            challenges_received_map[pid_j] += 1
                            challenge_positions[pid_j].append(
                                (d_i["position"], weight)
                            )

                # Resolve position shifts
                for pid in player_ids:
                    d = issue_data[pid]
                    old_pos = d["position"]
                    pressure = pressure_map[pid]

                    if pressure > 0 and challenge_positions[pid]:
                        # Target position: weighted mean of challenger positions
                        total_w = sum(w for _, w in challenge_positions[pid])
                        if total_w > 0:
                            target = sum(
                                p * w for p, w in challenge_positions[pid]
                            ) / total_w
                        else:
                            target = old_pos

                        # Shift magnitude
                        flexibility_factor = (d["flexibility"] / 100.0) * flex_weight
                        salience_resistance = 1.0 - (
                            (d["salience"] / 100.0) * sal_resist_weight * 0.5
                        )
                        shift_magnitude = (
                            pressure
                            * flexibility_factor
                            * salience_resistance
                            * dampening
                        )

                        # Apply shift toward target, capped
                        direction = target - old_pos
                        if abs(direction) > 0:
                            max_possible = abs(direction)
                            actual_shift = min(shift_magnitude, max_possible)
                            new_pos = old_pos + (
                                actual_shift if direction > 0 else -actual_shift
                            )
                            # Clamp to 0-100
                            new_pos = max(0.0, min(100.0, new_pos))
                        else:
                            new_pos = old_pos
                    else:
                        new_pos = old_pos

                    shift = abs(new_pos - old_pos)
                    max_shift = max(max_shift, shift)

                    # Record round result
                    round_results_bulk.append(RoundResult(
                        simulation_run=sim_run,
                        round_number=round_num,
                        player_id=pid,
                        issue=issue,
                        position_start=Decimal(str(round(old_pos, 2))),
                        position_end=Decimal(str(round(new_pos, 2))),
                        pressure_received=Decimal(str(round(pressure, 4))),
                        challenges_made=challenges_made_map[pid],
                        challenges_received=challenges_received_map[pid],
                    ))

                    # Update working position
                    issue_data[pid]["position"] = new_pos

            # Check convergence
            if max_shift < convergence_threshold:
                converged = True
                break

            # Check deadlock
            if engine_params["deadlock_detection_enabled"] and round_num >= 3:
                for issue in issues:
                    issue_key = str(issue.pk)
                    positions = [
                        d["position"] for d in working[issue_key].values()
                    ]
                    if len(positions) >= 4:
                        sorted_pos = sorted(positions)
                        mid = len(sorted_pos) // 2
                        low_avg = sum(sorted_pos[:mid]) / mid
                        high_avg = sum(sorted_pos[mid:]) / (len(sorted_pos) - mid)
                        gap = high_avg - low_avg

                        low_cap = sum(
                            d["capability"] * d["salience"]
                            for d in working[issue_key].values()
                            if d["position"] <= (low_avg + high_avg) / 2
                        )
                        high_cap = sum(
                            d["capability"] * d["salience"]
                            for d in working[issue_key].values()
                            if d["position"] > (low_avg + high_avg) / 2
                        )
                        total_cap = low_cap + high_cap
                        if total_cap > 0:
                            balance = abs(low_cap - high_cap) / total_cap
                            if (
                                balance < engine_params["deadlock_capability_balance_threshold"]
                                and gap > 20
                            ):
                                deadlock = True

        # Bulk create round results
        RoundResult.objects.bulk_create(round_results_bulk)

        # Compute final predictions
        for issue in issues:
            issue_key = str(issue.pk)
            issue_data = working[issue_key]

            # Power-weighted median (cap * sal)
            pw_positions = [
                (d["position"], d["capability"] * d["salience"] / 10000.0)
                for d in issue_data.values()
            ]
            w_median = _compute_weighted_median(pw_positions)

            # Salience-weighted mean
            sw_positions = [
                (d["position"], d["salience"] / 100.0)
                for d in issue_data.values()
            ]
            w_mean = _compute_weighted_mean(sw_positions)

            # Winning coalition: players within 10 units of median
            final_positions = [d["position"] for d in issue_data.values()]
            winning_cap = sum(
                d["capability"] * d["salience"]
                for d in issue_data.values()
                if abs(d["position"] - w_median) <= 10.0
            )
            total_cap = sum(
                d["capability"] * d["salience"]
                for d in issue_data.values()
            )
            winning_pct = (winning_cap / total_cap * 100.0) if total_cap > 0 else 0.0

            confidence = _compute_confidence(final_positions, winning_pct)

            # Determine stability
            if deadlock:
                stability_code = "DEADLOCKED"
            elif confidence >= 0.6:
                stability_code = "STABLE"
            else:
                stability_code = "FRAGILE"

            stability = LookupValue.objects.get(
                parent=stability_parent, code=stability_code,
            )

            PredictionOutcome.objects.create(
                simulation_run=sim_run,
                issue=issue,
                predicted_position=Decimal(str(round(w_median, 2))),
                confidence_score=Decimal(str(confidence)),
                weighted_median=Decimal(str(round(w_median, 2))),
                weighted_mean=Decimal(str(round(w_mean, 2))),
                winning_coalition_capability=Decimal(str(round(winning_pct, 2))),
                outcome_stability=stability,
            )

        # Update simulation run
        elapsed_ms = int((time.time() - start_time) * 1000)
        sim_run.total_rounds_executed = rounds_executed
        sim_run.converged = converged
        sim_run.deadlock_detected = deadlock
        sim_run.execution_time_ms = elapsed_ms
        sim_run.status = status_completed

        # Set primary predicted outcome (first issue's median)
        first_outcome = sim_run.prediction_outcomes.first()
        if first_outcome:
            sim_run.predicted_outcome = first_outcome.predicted_position
            sim_run.confidence_score = first_outcome.confidence_score
            sim_run.secondary_prediction = first_outcome.weighted_mean

        sim_run.save()

        # Update scenario status to Completed
        scenario.status = LookupValue.objects.get(parent=scenario_status_parent, code="COMPLETED")
        scenario.save(update_fields=["status", "updated_at"])

    except Exception:
        sim_run.status = status_failed
        sim_run.execution_time_ms = int((time.time() - start_time) * 1000)
        sim_run.save()
        # Revert scenario status to Ready (it was valid enough to attempt)
        scenario.status = LookupValue.objects.get(parent=scenario_status_parent, code="READY")
        scenario.save(update_fields=["status", "updated_at"])
        raise

    return sim_run
