from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from apps.core.models import BaseModel
from apps.lookup.models import LookupValue


class Scenario(BaseModel):
    """
    A prediction project. Contains issues, players, and simulation runs.
    Supports versioning via parent_version self-FK.
    """
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    scenario_type = models.ForeignKey(
        LookupValue,
        on_delete=models.PROTECT,
        related_name='+',
        help_text="FK to LookupValue under SCENARIO_TYPE parent.",
    )
    status = models.ForeignKey(
        LookupValue,
        on_delete=models.PROTECT,
        related_name='+',
        help_text="FK to LookupValue under SCENARIO_STATUS parent.",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_scenarios',
    )
    is_public = models.BooleanField(default=False)
    parent_version = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='child_versions',
    )
    version_number = models.PositiveIntegerField(default=1)
    version_label = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='+',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='+',
    )

    class Meta:
        ordering = ['-updated_at']

    def __str__(self) -> str:
        return self.title


class ScenarioIssue(BaseModel):
    """
    Defines what decision is at stake within a scenario.
    Uses a 0-100 numeric scale with labeled endpoints.
    """
    scenario = models.ForeignKey(
        Scenario,
        on_delete=models.CASCADE,
        related_name='issues',
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    scale_min_label = models.CharField(
        max_length=200,
        help_text="Label for the 0 end of the scale (e.g. 'Full free trade').",
    )
    scale_max_label = models.CharField(
        max_length=200,
        help_text="Label for the 100 end of the scale (e.g. 'Complete embargo').",
    )
    scale_min_value = models.IntegerField(default=0)
    scale_max_value = models.IntegerField(default=100)
    status_quo_position = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Current state on the scale. Anchors the model.",
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'title']
        unique_together = [('scenario', 'sort_order')]

    def __str__(self) -> str:
        return f"{self.scenario.title} — {self.title}"


class Player(BaseModel):
    """A stakeholder who can influence the scenario outcome."""
    scenario = models.ForeignKey(
        Scenario,
        on_delete=models.CASCADE,
        related_name='players',
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    player_type = models.ForeignKey(
        LookupValue,
        on_delete=models.PROTECT,
        related_name='+',
        help_text="FK to LookupValue under PLAYER_TYPE parent.",
    )

    class Meta:
        ordering = ['name']

    def __str__(self) -> str:
        return f"{self.name} ({self.scenario.title})"


class PlayerPosition(BaseModel):
    """
    A player's stance on a specific issue.
    All numeric fields are 0-100.
    """
    player = models.ForeignKey(
        Player,
        on_delete=models.CASCADE,
        related_name='positions',
    )
    issue = models.ForeignKey(
        ScenarioIssue,
        on_delete=models.CASCADE,
        related_name='player_positions',
    )
    position = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Where this player wants the outcome to land (0-100).",
    )
    capability = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Relative power/influence (0-100).",
    )
    salience = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="How much the player cares about this issue (0-100).",
    )
    flexibility = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Willingness to compromise (0-100, higher = more flexible).",
    )
    risk_profile = models.ForeignKey(
        LookupValue,
        on_delete=models.PROTECT,
        related_name='+',
        help_text="FK to LookupValue under RISK_PROFILE parent.",
    )

    class Meta:
        unique_together = [('player', 'issue')]
        ordering = ['player__name']

    def __str__(self) -> str:
        return f"{self.player.name} on {self.issue.title}: pos={self.position}"
