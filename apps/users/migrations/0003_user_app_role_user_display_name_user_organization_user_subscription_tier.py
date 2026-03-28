import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lookup', '0001_initial'),
        ('users', '0002_user_roles'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='display_name',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='user',
            name='organization',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='user',
            name='app_role',
            field=models.ForeignKey(blank=True, help_text='FK to LookupValue under USER_ROLE parent.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='lookup.lookupvalue'),
        ),
        migrations.AddField(
            model_name='user',
            name='subscription_tier',
            field=models.ForeignKey(blank=True, help_text='FK to LookupValue under SUBSCRIPTION_TIER parent.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='lookup.lookupvalue'),
        ),
    ]
