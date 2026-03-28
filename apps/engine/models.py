from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from apps.core.models import BaseModel
from apps.lookup.models import LookupValue


class SimulationRun(BaseModel):
    """An execution of the BDM engine against a scenario."""
    scenario = models.ForeignKey(
        'scenarios.Scenario',
        on_delete=models.CASCADE,
        related_name='simulation_runs',
    )
    total_rounds_executed = models.PositiveIntegerField(default=0)
    converged = models.BooleanField(default=False)
    deadlock_detected = models.BooleanField(default=False)
    predicted_outcome = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )
    confidence_score = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
    )
    secondary_prediction = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Salience-weighted mean as cross-check.",
    )
    execution_time_ms = models.PositiveIntegerField(default=0)
    parameters = models.JSONField(
        default=dict,
        blank=True,
        help_text="Snapshot of all engine config used for this run.",
    )
    status = models.ForeignKey(
        LookupValue,
        on_delete=models.PROTECT,
        related_name='+',
        help_text="FK to LookupValue under SIMULATION_STATUS parent.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='+',
    )
    analysis_report = models.TextField(
        blank=True,
        help_text="LLM-generated strategic analysis of simulation results.",
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"Run {self.pk} — {self.scenario.title}"


class RoundResult(BaseModel):
    """Per-round state for a player on an issue during a simulation."""
    simulation_run = models.ForeignKey(
        SimulationRun,
        on_delete=models.CASCADE,
        related_name='round_results',
    )
    round_number = models.PositiveIntegerField()
    player = models.ForeignKey(
        'scenarios.Player',
        on_delete=models.CASCADE,
        related_name='round_results',
    )
    issue = models.ForeignKey(
        'scenarios.ScenarioIssue',
        on_delete=models.CASCADE,
        related_name='round_results',
    )
    position_start = models.DecimalField(max_digits=6, decimal_places=2)
    position_end = models.DecimalField(max_digits=6, decimal_places=2)
    pressure_received = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0,
    )
    challenges_made = models.PositiveIntegerField(default=0)
    challenges_received = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [('simulation_run', 'round_number', 'player', 'issue')]
        ordering = ['round_number', 'player__name']

    def __str__(self) -> str:
        return f"Round {self.round_number}: {self.player.name} on {self.issue.title}"


class PredictionOutcome(BaseModel):
    """Final predicted outcome for a specific issue within a simulation run."""
    simulation_run = models.ForeignKey(
        SimulationRun,
        on_delete=models.CASCADE,
        related_name='prediction_outcomes',
    )
    issue = models.ForeignKey(
        'scenarios.ScenarioIssue',
        on_delete=models.CASCADE,
        related_name='prediction_outcomes',
    )
    predicted_position = models.DecimalField(max_digits=6, decimal_places=2)
    confidence_score = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
    )
    weighted_median = models.DecimalField(max_digits=6, decimal_places=2)
    weighted_mean = models.DecimalField(max_digits=6, decimal_places=2)
    winning_coalition_capability = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text="Percentage of total capability supporting the outcome.",
    )
    outcome_stability = models.ForeignKey(
        LookupValue,
        on_delete=models.PROTECT,
        related_name='+',
        help_text="FK to LookupValue under OUTCOME_STABILITY parent.",
    )
    narrative_summary = models.TextField(
        blank=True,
        help_text="LLM-generated plain language explanation.",
    )

    class Meta:
        unique_together = [('simulation_run', 'issue')]
        ordering = ['issue__sort_order']

    def __str__(self) -> str:
        return f"Prediction: {self.issue.title} = {self.predicted_position}"
