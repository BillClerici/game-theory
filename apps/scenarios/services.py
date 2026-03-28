"""Scenario business logic — duplication, branching, version history."""
from __future__ import annotations

from typing import Any

from django.db import transaction

from apps.scenarios.models import Player, PlayerPosition, Scenario, ScenarioIssue


@transaction.atomic
def duplicate_scenario(scenario: Scenario, user: Any) -> Scenario:
    """Deep copy a scenario with all issues, players, and positions."""
    old_issues = list(scenario.issues.filter(is_active=True))
    old_players = list(scenario.players.filter(is_active=True))

    # Clone scenario
    new_scenario = Scenario.objects.create(
        title=f"{scenario.title} (Copy)",
        description=scenario.description,
        scenario_type=scenario.scenario_type,
        status=scenario.status,
        owner=user,
        is_public=False,
        version_number=1,
        created_by=user,
        updated_by=user,
    )

    # Clone issues
    issue_map: dict[str, ScenarioIssue] = {}  # old_id -> new_issue
    for old_issue in old_issues:
        new_issue = ScenarioIssue.objects.create(
            scenario=new_scenario,
            title=old_issue.title,
            description=old_issue.description,
            scale_min_label=old_issue.scale_min_label,
            scale_max_label=old_issue.scale_max_label,
            scale_min_value=old_issue.scale_min_value,
            scale_max_value=old_issue.scale_max_value,
            status_quo_position=old_issue.status_quo_position,
            sort_order=old_issue.sort_order,
        )
        issue_map[str(old_issue.pk)] = new_issue

    # Clone players and positions
    for old_player in old_players:
        new_player = Player.objects.create(
            scenario=new_scenario,
            name=old_player.name,
            description=old_player.description,
            player_type=old_player.player_type,
        )
        old_positions = PlayerPosition.objects.filter(
            player=old_player, is_active=True,
        ).select_related('issue', 'risk_profile')
        for old_pos in old_positions:
            new_issue = issue_map.get(str(old_pos.issue_id))
            if new_issue:
                PlayerPosition.objects.create(
                    player=new_player,
                    issue=new_issue,
                    position=old_pos.position,
                    capability=old_pos.capability,
                    salience=old_pos.salience,
                    flexibility=old_pos.flexibility,
                    risk_profile=old_pos.risk_profile,
                )

    return new_scenario


@transaction.atomic
def branch_scenario(scenario: Scenario, user: Any, version_label: str = "") -> Scenario:
    """Create a versioned branch linked to the parent."""
    # Find highest version number in chain
    max_version = scenario.version_number
    for child in Scenario.objects.filter(parent_version=scenario):
        max_version = max(max_version, child.version_number)

    new_scenario = duplicate_scenario(scenario, user)
    new_scenario.title = scenario.title  # keep original title
    new_scenario.parent_version = scenario
    new_scenario.version_number = max_version + 1
    new_scenario.version_label = version_label
    new_scenario.save()

    return new_scenario


def get_version_history(scenario: Scenario) -> list[Scenario]:
    """Walk the parent_version chain to get full version history."""
    # Find root
    root = scenario
    while root.parent_version_id:
        root = root.parent_version

    # Collect all descendants
    versions = [root]
    _collect_children(root, versions)
    return sorted(versions, key=lambda s: s.version_number)


def _collect_children(parent: Scenario, result: list[Scenario]) -> None:
    children = list(Scenario.objects.filter(parent_version=parent, is_active=True))
    for child in children:
        result.append(child)
        _collect_children(child, result)


def compare_scenarios(scenario_ids: list[str]) -> dict[str, Any]:
    """
    Build a comparison dataset across 2-4 scenario versions.
    Returns parameter diffs, outcome comparisons, and player position grids.
    """
    from apps.engine.models import SimulationRun

    scenarios = list(
        Scenario.objects.filter(pk__in=scenario_ids, is_active=True)
        .select_related("scenario_type", "status")
        .order_by("version_number")
    )
    if len(scenarios) < 2:
        return {"error": "Need at least 2 scenarios to compare."}

    comparison: dict[str, Any] = {
        "scenarios": [],
        "issues": [],
        "player_diffs": [],
        "outcomes": [],
    }

    # Collect all unique issue titles and player names across versions
    all_issue_titles: list[str] = []
    all_player_names: list[str] = []

    for s in scenarios:
        issues = list(s.issues.filter(is_active=True).order_by("sort_order"))
        players = list(s.players.filter(is_active=True).select_related("player_type").order_by("name"))
        latest_sim = SimulationRun.objects.filter(scenario=s).select_related("status").first()

        for i in issues:
            if i.title not in all_issue_titles:
                all_issue_titles.append(i.title)
        for p in players:
            if p.name not in all_player_names:
                all_player_names.append(p.name)

        sim_data = None
        prediction_outcomes = []
        if latest_sim:
            outcomes = list(
                latest_sim.prediction_outcomes.all().select_related("issue", "outcome_stability")
            )
            prediction_outcomes = [
                {
                    "issue_title": o.issue.title,
                    "predicted_position": float(o.predicted_position),
                    "confidence_score": float(o.confidence_score),
                    "weighted_median": float(o.weighted_median),
                    "weighted_mean": float(o.weighted_mean),
                    "winning_coalition_pct": float(o.winning_coalition_capability),
                    "stability": o.outcome_stability.label,
                }
                for o in outcomes
            ]
            sim_data = {
                "id": str(latest_sim.pk),
                "rounds": latest_sim.total_rounds_executed,
                "converged": latest_sim.converged,
                "deadlock": latest_sim.deadlock_detected,
                "predicted_outcome": float(latest_sim.predicted_outcome) if latest_sim.predicted_outcome else None,
                "confidence": float(latest_sim.confidence_score) if latest_sim.confidence_score else None,
                "execution_ms": latest_sim.execution_time_ms,
                "prediction_outcomes": prediction_outcomes,
            }

        # Build position map: {player_name: {issue_title: {position, capability, salience, flexibility}}}
        position_map: dict[str, dict[str, dict[str, float]]] = {}
        for player in players:
            positions = PlayerPosition.objects.filter(
                player=player, is_active=True,
            ).select_related("issue", "risk_profile")
            player_positions: dict[str, dict[str, float]] = {}
            for pp in positions:
                player_positions[pp.issue.title] = {
                    "position": float(pp.position),
                    "capability": float(pp.capability),
                    "salience": float(pp.salience),
                    "flexibility": float(pp.flexibility),
                    "risk_profile": pp.risk_profile.label,
                }
            position_map[player.name] = player_positions

        comparison["scenarios"].append({
            "id": str(s.pk),
            "title": s.title,
            "version": s.version_number,
            "label": s.version_label or f"v{s.version_number}",
            "status": s.status.label,
            "simulation": sim_data,
            "positions": position_map,
        })

    comparison["issues"] = all_issue_titles
    comparison["players"] = all_player_names

    # Build diffs: for each player × issue, show how values changed across versions
    for player_name in all_player_names:
        for issue_title in all_issue_titles:
            values_across = []
            for sc in comparison["scenarios"]:
                pos = sc["positions"].get(player_name, {}).get(issue_title)
                values_across.append(pos)

            # Check if anything changed
            non_none = [v for v in values_across if v is not None]
            if len(non_none) >= 2:
                positions = [v["position"] for v in non_none]
                if max(positions) != min(positions):
                    comparison["player_diffs"].append({
                        "player": player_name,
                        "issue": issue_title,
                        "values": values_across,
                    })

    return comparison
