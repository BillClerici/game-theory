import django.core.validators
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
            name='SimulationRun',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('total_rounds_executed', models.PositiveIntegerField(default=0)),
                ('converged', models.BooleanField(default=False)),
                ('deadlock_detected', models.BooleanField(default=False)),
                ('predicted_outcome', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ('confidence_score', models.DecimalField(blank=True, decimal_places=3, max_digits=4, null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(1)])),
                ('secondary_prediction', models.DecimalField(blank=True, decimal_places=2, help_text='Salience-weighted mean as cross-check.', max_digits=6, null=True)),
                ('execution_time_ms', models.PositiveIntegerField(default=0)),
                ('parameters', models.JSONField(blank=True, default=dict, help_text='Snapshot of all engine config used for this run.')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('scenario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='simulation_runs', to='scenarios.scenario')),
                ('status', models.ForeignKey(help_text='FK to LookupValue under SIMULATION_STATUS parent.', on_delete=django.db.models.deletion.PROTECT, related_name='+', to='lookup.lookupvalue')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='RoundResult',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('round_number', models.PositiveIntegerField()),
                ('position_start', models.DecimalField(decimal_places=2, max_digits=6)),
                ('position_end', models.DecimalField(decimal_places=2, max_digits=6)),
                ('pressure_received', models.DecimalField(decimal_places=4, default=0, max_digits=10)),
                ('challenges_made', models.PositiveIntegerField(default=0)),
                ('challenges_received', models.PositiveIntegerField(default=0)),
                ('issue', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='round_results', to='scenarios.scenarioissue')),
                ('player', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='round_results', to='scenarios.player')),
                ('simulation_run', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='round_results', to='engine.simulationrun')),
            ],
            options={
                'ordering': ['round_number', 'player__name'],
                'unique_together': {('simulation_run', 'round_number', 'player', 'issue')},
            },
        ),
        migrations.CreateModel(
            name='PredictionOutcome',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('predicted_position', models.DecimalField(decimal_places=2, max_digits=6)),
                ('confidence_score', models.DecimalField(decimal_places=3, max_digits=4, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(1)])),
                ('weighted_median', models.DecimalField(decimal_places=2, max_digits=6)),
                ('weighted_mean', models.DecimalField(decimal_places=2, max_digits=6)),
                ('winning_coalition_capability', models.DecimalField(decimal_places=2, help_text='Percentage of total capability supporting the outcome.', max_digits=6)),
                ('narrative_summary', models.TextField(blank=True, help_text='LLM-generated plain language explanation.')),
                ('issue', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='prediction_outcomes', to='scenarios.scenarioissue')),
                ('outcome_stability', models.ForeignKey(help_text='FK to LookupValue under OUTCOME_STABILITY parent.', on_delete=django.db.models.deletion.PROTECT, related_name='+', to='lookup.lookupvalue')),
                ('simulation_run', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='prediction_outcomes', to='engine.simulationrun')),
            ],
            options={
                'ordering': ['issue__sort_order'],
                'unique_together': {('simulation_run', 'issue')},
            },
        ),
    ]
