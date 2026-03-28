from django.contrib import admin
from apps.scenarios.models import Player, PlayerPosition, Scenario, ScenarioIssue


@admin.register(Scenario)
class ScenarioAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "scenario_type", "status", "version_number", "is_active")
    list_filter = ("is_active",)
    search_fields = ("title", "description")


@admin.register(ScenarioIssue)
class ScenarioIssueAdmin(admin.ModelAdmin):
    list_display = ("title", "scenario", "sort_order", "status_quo_position", "is_active")
    list_filter = ("is_active",)


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ("name", "scenario", "player_type", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(PlayerPosition)
class PlayerPositionAdmin(admin.ModelAdmin):
    list_display = ("player", "issue", "position", "capability", "salience")
    list_filter = ("risk_profile",)
