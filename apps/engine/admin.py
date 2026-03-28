from django.contrib import admin
from apps.engine.models import PredictionOutcome, RoundResult, SimulationRun


@admin.register(SimulationRun)
class SimulationRunAdmin(admin.ModelAdmin):
    list_display = ("scenario", "status", "total_rounds_executed", "converged", "predicted_outcome", "created_at")
    list_filter = ("converged", "deadlock_detected")


@admin.register(RoundResult)
class RoundResultAdmin(admin.ModelAdmin):
    list_display = ("simulation_run", "round_number", "player", "issue", "position_start", "position_end")
    list_filter = ("round_number",)


@admin.register(PredictionOutcome)
class PredictionOutcomeAdmin(admin.ModelAdmin):
    list_display = ("simulation_run", "issue", "predicted_position", "confidence_score", "outcome_stability")
