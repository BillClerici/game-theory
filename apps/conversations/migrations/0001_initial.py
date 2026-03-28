import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('lookup', '0001_initial'),
        ('scenarios', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConversationSession',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('extracted_scenario_data', models.JSONField(blank=True, default=dict, help_text='Accumulated structured data extracted from the conversation.')),
                ('total_tokens_used', models.PositiveIntegerField(default=0)),
                ('scenario', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='conversations', to='scenarios.scenario')),
                ('session_type', models.ForeignKey(help_text='FK to LookupValue under CONVERSATION_SESSION_TYPE parent.', on_delete=django.db.models.deletion.PROTECT, related_name='+', to='lookup.lookupvalue')),
                ('status', models.ForeignKey(help_text='FK to LookupValue under CONVERSATION_STATUS parent.', on_delete=django.db.models.deletion.PROTECT, related_name='+', to='lookup.lookupvalue')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conversations', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='ConversationMessage',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('role', models.CharField(choices=[('user', 'User'), ('assistant', 'Assistant'), ('system', 'System')], max_length=20)),
                ('content', models.TextField()),
                ('structured_data', models.JSONField(blank=True, help_text='Structured parameters extracted from this message via tool use.', null=True)),
                ('message_order', models.PositiveIntegerField()),
                ('token_count', models.PositiveIntegerField(default=0)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='conversations.conversationsession')),
            ],
            options={
                'ordering': ['message_order'],
            },
        ),
    ]
