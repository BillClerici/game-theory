from django.conf import settings
from django.db import models
from apps.core.models import BaseModel
from apps.lookup.models import LookupValue


class ConversationSession(BaseModel):
    """A conversation thread between a user and the LLM, tied to a scenario."""
    scenario = models.ForeignKey(
        'scenarios.Scenario',
        on_delete=models.CASCADE,
        related_name='conversations',
        null=True,
        blank=True,
        help_text="Null until the scenario is created from the conversation.",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversations',
    )
    session_type = models.ForeignKey(
        LookupValue,
        on_delete=models.PROTECT,
        related_name='+',
        help_text="FK to LookupValue under CONVERSATION_SESSION_TYPE parent.",
    )
    status = models.ForeignKey(
        LookupValue,
        on_delete=models.PROTECT,
        related_name='+',
        help_text="FK to LookupValue under CONVERSATION_STATUS parent.",
    )
    extracted_scenario_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Accumulated structured data extracted from the conversation.",
    )
    total_tokens_used = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self) -> str:
        return f"Conversation {self.pk} ({self.session_type.label})"


class ConversationMessage(BaseModel):
    """An individual message in a conversation thread."""
    session = models.ForeignKey(
        ConversationSession,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    role = models.CharField(
        max_length=20,
        choices=[('user', 'User'), ('assistant', 'Assistant'), ('system', 'System')],
    )
    content = models.TextField()
    structured_data = models.JSONField(
        null=True,
        blank=True,
        help_text="Structured parameters extracted from this message via tool use.",
    )
    message_order = models.PositiveIntegerField()
    token_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['message_order']

    def __str__(self) -> str:
        return f"{self.role}: {self.content[:50]}..."
