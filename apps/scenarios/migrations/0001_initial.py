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
    ]

    operations = [
        migrations.CreateModel(
            name='Scenario',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('is_public', models.BooleanField(default=False)),
                ('version_number', models.PositiveIntegerField(default=1)),
                ('version_label', models.CharField(blank=True, max_length=200)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='owned_scenarios', to=settings.AUTH_USER_MODEL)),
                ('parent_version', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='child_versions', to='scenarios.scenario')),
                ('scenario_type', models.ForeignKey(help_text='FK to LookupValue under SCENARIO_TYPE parent.', on_delete=django.db.models.deletion.PROTECT, related_name='+', to='lookup.lookupvalue')),
                ('status', models.ForeignKey(help_text='FK to LookupValue under SCENARIO_STATUS parent.', on_delete=django.db.models.deletion.PROTECT, related_name='+', to='lookup.lookupvalue')),
                ('updated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='ScenarioIssue',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('scale_min_label', models.CharField(help_text="Label for the 0 end of the scale.", max_length=200)),
                ('scale_max_label', models.CharField(help_text="Label for the 100 end of the scale.", max_length=200)),
                ('scale_min_value', models.IntegerField(default=0)),
                ('scale_max_value', models.IntegerField(default=100)),
                ('status_quo_position', models.IntegerField(help_text='Current state on the scale.', validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('scenario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='issues', to='scenarios.scenario')),
            ],
            options={
                'ordering': ['sort_order', 'title'],
                'unique_together': {('scenario', 'sort_order')},
            },
        ),
        migrations.CreateModel(
            name='Player',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('player_type', models.ForeignKey(help_text='FK to LookupValue under PLAYER_TYPE parent.', on_delete=django.db.models.deletion.PROTECT, related_name='+', to='lookup.lookupvalue')),
                ('scenario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='players', to='scenarios.scenario')),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='PlayerPosition',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('position', models.DecimalField(decimal_places=2, help_text='Where this player wants the outcome to land (0-100).', max_digits=5, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('capability', models.DecimalField(decimal_places=2, help_text='Relative power/influence (0-100).', max_digits=5, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('salience', models.DecimalField(decimal_places=2, help_text='How much the player cares about this issue (0-100).', max_digits=5, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('flexibility', models.DecimalField(decimal_places=2, help_text='Willingness to compromise (0-100).', max_digits=5, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('issue', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='player_positions', to='scenarios.scenarioissue')),
                ('player', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='positions', to='scenarios.player')),
                ('risk_profile', models.ForeignKey(help_text='FK to LookupValue under RISK_PROFILE parent.', on_delete=django.db.models.deletion.PROTECT, related_name='+', to='lookup.lookupvalue')),
            ],
            options={
                'ordering': ['player__name'],
                'unique_together': {('player', 'issue')},
            },
        ),
    ]
