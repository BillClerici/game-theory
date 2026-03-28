from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('engine', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='simulationrun',
            name='analysis_report',
            field=models.TextField(blank=True, help_text='LLM-generated strategic analysis of simulation results.'),
        ),
    ]
