"""
GraphQL types, queries, and mutations for Scenarios, Issues, Players, and Simulations.
Designed as the primary API for both web and future mobile clients.
"""
import uuid
from decimal import Decimal
from typing import Any, Optional

import strawberry
from strawberry.types import Info

from apps.api.schema import (
    LookupValueType,
    PageInfo,
    get_request,
    paginate,
    require_auth,
)
from apps.engine.models import PredictionOutcome, RoundResult, SimulationRun
from apps.engine.services import (
    compute_data_quality_score,
    run_simulation,
    validate_scenario,
)
from apps.lookup.models import LookupValue
from apps.scenarios.models import Player, PlayerPosition, Scenario, ScenarioIssue
from apps.scenarios.services import branch_scenario, duplicate_scenario


# ── Types ──


@strawberry.type
class PlayerPositionType:
    id: uuid.UUID
    position: float
    capability: float
    salience: float
    flexibility: float
    issue_id: uuid.UUID
    player_id: uuid.UUID

    @strawberry.field
    def risk_profile(self) -> LookupValueType:
        return self._risk_profile  # noqa: set in resolver

    @strawberry.field
    def issue_title(self) -> str:
        return self._issue_title


@strawberry.type
class PlayerType:
    id: uuid.UUID
    name: str
    description: str
    is_active: bool

    @strawberry.field
    def player_type(self) -> LookupValueType:
        return self._player_type

    @strawberry.field
    def positions(self) -> list[PlayerPositionType]:
        return self._positions


@strawberry.type
class ScenarioIssueType:
    id: uuid.UUID
    title: str
    description: str
    scale_min_label: str
    scale_max_label: str
    scale_min_value: int
    scale_max_value: int
    status_quo_position: int
    sort_order: int
    is_active: bool


@strawberry.type
class ScenarioType:
    id: uuid.UUID
    title: str
    description: str
    is_public: bool
    version_number: int
    version_label: str
    is_active: bool
    created_at: str
    updated_at: str

    @strawberry.field
    def scenario_type(self) -> LookupValueType:
        return self._scenario_type

    @strawberry.field
    def status(self) -> LookupValueType:
        return self._status

    @strawberry.field
    def owner_email(self) -> str:
        return self._owner_email

    @strawberry.field
    def issues(self) -> list[ScenarioIssueType]:
        return self._issues

    @strawberry.field
    def players(self) -> list[PlayerType]:
        return self._players

    @strawberry.field
    def issue_count(self) -> int:
        return len(self._issues)

    @strawberry.field
    def player_count(self) -> int:
        return len(self._players)


@strawberry.type
class RoundResultType:
    round_number: int
    player_name: str
    player_id: str
    issue_title: str
    issue_id: str
    position_start: float
    position_end: float
    pressure_received: float
    challenges_made: int
    challenges_received: int


@strawberry.type
class PredictionOutcomeType:
    id: uuid.UUID
    issue_title: str
    issue_id: uuid.UUID
    predicted_position: float
    confidence_score: float
    weighted_median: float
    weighted_mean: float
    winning_coalition_capability: float
    outcome_stability: str
    narrative_summary: str


@strawberry.type
class SimulationRunType:
    id: uuid.UUID
    total_rounds_executed: int
    converged: bool
    deadlock_detected: bool
    predicted_outcome: Optional[float]
    confidence_score: Optional[float]
    secondary_prediction: Optional[float]
    execution_time_ms: int
    status: str
    created_at: str

    @strawberry.field
    def prediction_outcomes(self) -> list[PredictionOutcomeType]:
        return self._prediction_outcomes

    @strawberry.field
    def round_results(self) -> list[RoundResultType]:
        return self._round_results


@strawberry.type
class DataQualityType:
    score: float
    completeness: float
    diversity: float
    consistency: float
    granularity: float
    warnings: list[str]


@strawberry.type
class ValidationResultType:
    valid: bool
    errors: list[str]


@strawberry.type
class ScenarioConnection:
    items: list[ScenarioType]
    page_info: PageInfo


# ── Resolvers / Helpers ──


def _resolve_scenario(s: Scenario) -> ScenarioType:
    """Build a ScenarioType from a Scenario model instance."""
    issues = list(s.issues.filter(is_active=True))
    players_qs = s.players.filter(is_active=True).select_related("player_type")
    players = []
    for p in players_qs:
        positions_qs = PlayerPosition.objects.filter(
            player=p, is_active=True,
        ).select_related("risk_profile", "issue")
        pos_list = []
        for pp in positions_qs:
            pt = PlayerPositionType(
                id=pp.pk,
                position=float(pp.position),
                capability=float(pp.capability),
                salience=float(pp.salience),
                flexibility=float(pp.flexibility),
                issue_id=pp.issue_id,
                player_id=pp.player_id,
            )
            pt._risk_profile = pp.risk_profile
            pt._issue_title = pp.issue.title
            pos_list.append(pt)

        player_type = PlayerType(
            id=p.pk,
            name=p.name,
            description=p.description,
            is_active=p.is_active,
        )
        player_type._player_type = p.player_type
        player_type._positions = pos_list
        players.append(player_type)

    issue_types = [
        ScenarioIssueType(
            id=i.pk,
            title=i.title,
            description=i.description,
            scale_min_label=i.scale_min_label,
            scale_max_label=i.scale_max_label,
            scale_min_value=i.scale_min_value,
            scale_max_value=i.scale_max_value,
            status_quo_position=i.status_quo_position,
            sort_order=i.sort_order,
            is_active=i.is_active,
        )
        for i in issues
    ]

    st = ScenarioType(
        id=s.pk,
        title=s.title,
        description=s.description,
        is_public=s.is_public,
        version_number=s.version_number,
        version_label=s.version_label,
        is_active=s.is_active,
        created_at=s.created_at.isoformat(),
        updated_at=s.updated_at.isoformat(),
    )
    st._scenario_type = s.scenario_type
    st._status = s.status
    st._owner_email = s.owner.email
    st._issues = issue_types
    st._players = players
    return st


def _resolve_simulation_run(run: SimulationRun) -> SimulationRunType:
    outcomes = list(
        run.prediction_outcomes.all().select_related("issue", "outcome_stability")
    )
    outcome_types = [
        PredictionOutcomeType(
            id=o.pk,
            issue_title=o.issue.title,
            issue_id=o.issue_id,
            predicted_position=float(o.predicted_position),
            confidence_score=float(o.confidence_score),
            weighted_median=float(o.weighted_median),
            weighted_mean=float(o.weighted_mean),
            winning_coalition_capability=float(o.winning_coalition_capability),
            outcome_stability=o.outcome_stability.label,
            narrative_summary=o.narrative_summary,
        )
        for o in outcomes
    ]

    rounds = list(
        run.round_results.all().select_related("player", "issue").order_by("round_number")
    )
    round_types = [
        RoundResultType(
            round_number=r.round_number,
            player_name=r.player.name,
            player_id=str(r.player_id),
            issue_title=r.issue.title,
            issue_id=str(r.issue_id),
            position_start=float(r.position_start),
            position_end=float(r.position_end),
            pressure_received=float(r.pressure_received),
            challenges_made=r.challenges_made,
            challenges_received=r.challenges_received,
        )
        for r in rounds
    ]

    srt = SimulationRunType(
        id=run.pk,
        total_rounds_executed=run.total_rounds_executed,
        converged=run.converged,
        deadlock_detected=run.deadlock_detected,
        predicted_outcome=float(run.predicted_outcome) if run.predicted_outcome else None,
        confidence_score=float(run.confidence_score) if run.confidence_score else None,
        secondary_prediction=float(run.secondary_prediction) if run.secondary_prediction else None,
        execution_time_ms=run.execution_time_ms,
        status=run.status.label,
        created_at=run.created_at.isoformat(),
    )
    srt._prediction_outcomes = outcome_types
    srt._round_results = round_types
    return srt


# ── Queries ──


@strawberry.type
class ScenarioQuery:
    @strawberry.field
    def scenarios(
        self,
        info: Info,
        page: int = 1,
        page_size: int = 25,
        search: str = "",
        order_by: str = "-updated_at",
        status: str = "",
    ) -> ScenarioConnection:
        require_auth(info)
        user = get_request(info).user
        qs = Scenario.objects.filter(owner=user).select_related("scenario_type", "status", "owner")
        if status:
            qs = qs.filter(status__code=status)
        items, page_info = paginate(qs, page, page_size, search, ["title", "description"], order_by)
        return ScenarioConnection(
            items=[_resolve_scenario(s) for s in items],
            page_info=page_info,
        )

    @strawberry.field
    def scenario(self, info: Info, id: uuid.UUID) -> Optional[ScenarioType]:
        require_auth(info)
        user = get_request(info).user
        s = Scenario.objects.filter(pk=id, owner=user).select_related(
            "scenario_type", "status", "owner",
        ).first()
        return _resolve_scenario(s) if s else None

    @strawberry.field
    def simulation_run(self, info: Info, id: uuid.UUID) -> Optional[SimulationRunType]:
        require_auth(info)
        user = get_request(info).user
        run = SimulationRun.objects.filter(
            pk=id, scenario__owner=user,
        ).select_related("status", "scenario").first()
        return _resolve_simulation_run(run) if run else None

    @strawberry.field
    def simulation_runs(
        self,
        info: Info,
        scenario_id: uuid.UUID,
        page: int = 1,
        page_size: int = 10,
    ) -> list[SimulationRunType]:
        require_auth(info)
        user = get_request(info).user
        runs = SimulationRun.objects.filter(
            scenario_id=scenario_id, scenario__owner=user,
        ).select_related("status")[:page_size]
        return [_resolve_simulation_run(r) for r in runs]

    @strawberry.field
    def scenario_data_quality(self, info: Info, scenario_id: uuid.UUID) -> DataQualityType:
        require_auth(info)
        user = get_request(info).user
        scenario = Scenario.objects.get(pk=scenario_id, owner=user)
        result = compute_data_quality_score(scenario)
        return DataQualityType(**result)

    @strawberry.field
    def scenario_validation(self, info: Info, scenario_id: uuid.UUID) -> ValidationResultType:
        require_auth(info)
        user = get_request(info).user
        scenario = Scenario.objects.get(pk=scenario_id, owner=user)
        errors = validate_scenario(scenario)
        return ValidationResultType(valid=len(errors) == 0, errors=errors)


# ── Input Types ──


@strawberry.input
class ScenarioInput:
    title: str
    description: str = ""
    scenario_type_id: uuid.UUID = strawberry.UNSET
    is_public: bool = False


@strawberry.input
class ScenarioIssueInput:
    title: str
    description: str = ""
    scale_min_label: str = "Minimum"
    scale_max_label: str = "Maximum"
    status_quo_position: int = 50
    sort_order: int = 0


@strawberry.input
class PlayerInput:
    name: str
    description: str = ""
    player_type_id: uuid.UUID = strawberry.UNSET


@strawberry.input
class PlayerPositionInput:
    position: float = 50.0
    capability: float = 50.0
    salience: float = 50.0
    flexibility: float = 50.0
    risk_profile_id: uuid.UUID = strawberry.UNSET


@strawberry.input
class BulkPositionEntry:
    player_id: uuid.UUID
    issue_id: uuid.UUID
    position: float
    capability: float
    salience: float
    flexibility: float
    risk_profile_id: uuid.UUID


@strawberry.input
class SimulationParamsInput:
    max_rounds: int = 7
    convergence_threshold: float = 0.5
    deadlock_detection_enabled: bool = True
    position_shift_dampening: float = 0.8


# ── Mutations ──


@strawberry.type
class ScenarioMutation:
    @strawberry.mutation
    def create_scenario(self, info: Info, input: ScenarioInput) -> ScenarioType:
        require_auth(info)
        user = get_request(info).user
        status_parent = LookupValue.objects.get(parent__isnull=True, code="SCENARIO_STATUS")
        draft_status = LookupValue.objects.get(parent=status_parent, code="DRAFT")
        scenario = Scenario.objects.create(
            title=input.title,
            description=input.description,
            scenario_type_id=input.scenario_type_id,
            status=draft_status,
            owner=user,
            created_by=user,
            updated_by=user,
        )
        return _resolve_scenario(scenario)

    @strawberry.mutation
    def update_scenario(self, info: Info, id: uuid.UUID, input: ScenarioInput) -> ScenarioType:
        require_auth(info)
        user = get_request(info).user
        s = Scenario.objects.get(pk=id, owner=user)
        s.title = input.title
        s.description = input.description
        if input.scenario_type_id is not strawberry.UNSET:
            s.scenario_type_id = input.scenario_type_id
        s.is_public = input.is_public
        s.updated_by = user
        s.save()
        return _resolve_scenario(s)

    @strawberry.mutation
    def delete_scenario(self, info: Info, id: uuid.UUID) -> bool:
        require_auth(info)
        user = get_request(info).user
        s = Scenario.objects.get(pk=id, owner=user)
        s.is_active = False
        s.save(update_fields=["is_active", "updated_at"])
        return True

    @strawberry.mutation
    def duplicate_scenario(self, info: Info, id: uuid.UUID) -> ScenarioType:
        require_auth(info)
        user = get_request(info).user
        scenario = Scenario.objects.get(pk=id, owner=user)
        new_s = duplicate_scenario(scenario, user)
        return _resolve_scenario(new_s)

    @strawberry.mutation
    def branch_scenario(
        self, info: Info, id: uuid.UUID, version_label: str = "",
    ) -> ScenarioType:
        require_auth(info)
        user = get_request(info).user
        scenario = Scenario.objects.get(pk=id, owner=user)
        new_s = branch_scenario(scenario, user, version_label)
        return _resolve_scenario(new_s)

    # Issues
    @strawberry.mutation
    def create_issue(
        self, info: Info, scenario_id: uuid.UUID, input: ScenarioIssueInput,
    ) -> ScenarioIssueType:
        require_auth(info)
        user = get_request(info).user
        scenario = Scenario.objects.get(pk=scenario_id, owner=user)
        issue = ScenarioIssue.objects.create(
            scenario=scenario,
            title=input.title,
            description=input.description,
            scale_min_label=input.scale_min_label,
            scale_max_label=input.scale_max_label,
            status_quo_position=input.status_quo_position,
            sort_order=input.sort_order,
        )
        return ScenarioIssueType(
            id=issue.pk,
            title=issue.title,
            description=issue.description,
            scale_min_label=issue.scale_min_label,
            scale_max_label=issue.scale_max_label,
            scale_min_value=issue.scale_min_value,
            scale_max_value=issue.scale_max_value,
            status_quo_position=issue.status_quo_position,
            sort_order=issue.sort_order,
            is_active=issue.is_active,
        )

    @strawberry.mutation
    def update_issue(
        self, info: Info, scenario_id: uuid.UUID, issue_id: uuid.UUID, input: ScenarioIssueInput,
    ) -> ScenarioIssueType:
        require_auth(info)
        user = get_request(info).user
        issue = ScenarioIssue.objects.get(
            pk=issue_id, scenario_id=scenario_id, scenario__owner=user,
        )
        issue.title = input.title
        issue.description = input.description
        issue.scale_min_label = input.scale_min_label
        issue.scale_max_label = input.scale_max_label
        issue.status_quo_position = input.status_quo_position
        issue.sort_order = input.sort_order
        issue.save()
        return ScenarioIssueType(
            id=issue.pk,
            title=issue.title,
            description=issue.description,
            scale_min_label=issue.scale_min_label,
            scale_max_label=issue.scale_max_label,
            scale_min_value=issue.scale_min_value,
            scale_max_value=issue.scale_max_value,
            status_quo_position=issue.status_quo_position,
            sort_order=issue.sort_order,
            is_active=issue.is_active,
        )

    @strawberry.mutation
    def delete_issue(self, info: Info, scenario_id: uuid.UUID, issue_id: uuid.UUID) -> bool:
        require_auth(info)
        user = get_request(info).user
        issue = ScenarioIssue.objects.get(
            pk=issue_id, scenario_id=scenario_id, scenario__owner=user,
        )
        issue.is_active = False
        issue.save(update_fields=["is_active", "updated_at"])
        return True

    # Players
    @strawberry.mutation
    def create_player(
        self, info: Info, scenario_id: uuid.UUID, input: PlayerInput,
    ) -> PlayerType:
        require_auth(info)
        user = get_request(info).user
        scenario = Scenario.objects.get(pk=scenario_id, owner=user)
        player = Player.objects.create(
            scenario=scenario,
            name=input.name,
            description=input.description,
            player_type_id=input.player_type_id,
        )
        pt = PlayerType(
            id=player.pk,
            name=player.name,
            description=player.description,
            is_active=player.is_active,
        )
        pt._player_type = player.player_type
        pt._positions = []
        return pt

    @strawberry.mutation
    def update_player(
        self, info: Info, scenario_id: uuid.UUID, player_id: uuid.UUID, input: PlayerInput,
    ) -> PlayerType:
        require_auth(info)
        user = get_request(info).user
        player = Player.objects.get(
            pk=player_id, scenario_id=scenario_id, scenario__owner=user,
        )
        player.name = input.name
        player.description = input.description
        if input.player_type_id is not strawberry.UNSET:
            player.player_type_id = input.player_type_id
        player.save()
        pt = PlayerType(
            id=player.pk,
            name=player.name,
            description=player.description,
            is_active=player.is_active,
        )
        pt._player_type = player.player_type
        pt._positions = []
        return pt

    @strawberry.mutation
    def delete_player(self, info: Info, scenario_id: uuid.UUID, player_id: uuid.UUID) -> bool:
        require_auth(info)
        user = get_request(info).user
        player = Player.objects.get(
            pk=player_id, scenario_id=scenario_id, scenario__owner=user,
        )
        player.is_active = False
        player.save(update_fields=["is_active", "updated_at"])
        return True

    # Player Positions
    @strawberry.mutation
    def update_player_position(
        self,
        info: Info,
        scenario_id: uuid.UUID,
        player_id: uuid.UUID,
        issue_id: uuid.UUID,
        input: PlayerPositionInput,
    ) -> PlayerPositionType:
        require_auth(info)
        user = get_request(info).user
        # Verify ownership
        Scenario.objects.get(pk=scenario_id, owner=user)
        position, _ = PlayerPosition.objects.update_or_create(
            player_id=player_id,
            issue_id=issue_id,
            defaults={
                "position": Decimal(str(input.position)),
                "capability": Decimal(str(input.capability)),
                "salience": Decimal(str(input.salience)),
                "flexibility": Decimal(str(input.flexibility)),
                "risk_profile_id": input.risk_profile_id,
            },
        )
        pt = PlayerPositionType(
            id=position.pk,
            position=float(position.position),
            capability=float(position.capability),
            salience=float(position.salience),
            flexibility=float(position.flexibility),
            issue_id=position.issue_id,
            player_id=position.player_id,
        )
        pt._risk_profile = position.risk_profile
        pt._issue_title = position.issue.title
        return pt

    @strawberry.mutation
    def bulk_update_positions(
        self,
        info: Info,
        scenario_id: uuid.UUID,
        entries: list[BulkPositionEntry],
    ) -> list[PlayerPositionType]:
        require_auth(info)
        user = get_request(info).user
        Scenario.objects.get(pk=scenario_id, owner=user)
        results = []
        for entry in entries:
            position, _ = PlayerPosition.objects.update_or_create(
                player_id=entry.player_id,
                issue_id=entry.issue_id,
                defaults={
                    "position": Decimal(str(entry.position)),
                    "capability": Decimal(str(entry.capability)),
                    "salience": Decimal(str(entry.salience)),
                    "flexibility": Decimal(str(entry.flexibility)),
                    "risk_profile_id": entry.risk_profile_id,
                },
            )
            pt = PlayerPositionType(
                id=position.pk,
                position=float(position.position),
                capability=float(position.capability),
                salience=float(position.salience),
                flexibility=float(position.flexibility),
                issue_id=position.issue_id,
                player_id=position.player_id,
            )
            pt._risk_profile = position.risk_profile
            pt._issue_title = position.issue.title
            results.append(pt)
        return results

    # Simulation
    @strawberry.mutation
    def run_simulation(
        self,
        info: Info,
        scenario_id: uuid.UUID,
        params: Optional[SimulationParamsInput] = None,
    ) -> SimulationRunType:
        require_auth(info)
        user = get_request(info).user
        scenario = Scenario.objects.get(pk=scenario_id, owner=user)
        errors = validate_scenario(scenario)
        if errors:
            raise ValueError(f"Validation failed: {'; '.join(errors)}")
        engine_params = {}
        if params:
            engine_params = {
                "max_rounds": params.max_rounds,
                "convergence_threshold": params.convergence_threshold,
                "deadlock_detection_enabled": params.deadlock_detection_enabled,
                "position_shift_dampening": params.position_shift_dampening,
            }
        sim_run = run_simulation(scenario, user, engine_params or None)
        return _resolve_simulation_run(sim_run)
