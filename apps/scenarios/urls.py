from django.urls import path

from apps.scenarios.views import (
    AIResearchPlayersView,
    CompareSelectView,
    CompareView,
    IssueCreateView,
    IssueDeleteView,
    IssueEditView,
    PlayerCreateView,
    PlayerDeleteView,
    PlayerEditView,
    PlayerPositionEditView,
    RunSimulationView,
    ScenarioBranchView,
    ScenarioCreateView,
    ScenarioDeleteView,
    ScenarioDetailView,
    ScenarioDuplicateView,
    ScenarioEditView,
    ScenarioListView,
    ScenarioVersionsView,
    WhatIfBranchView,
)

urlpatterns = [
    # Scenarios
    path("", ScenarioListView.as_view(), name="scenario_list"),
    path("create/", ScenarioCreateView.as_view(), name="scenario_create"),
    path("<uuid:scenario_id>/", ScenarioDetailView.as_view(), name="scenario_detail"),
    path("<uuid:scenario_id>/edit/", ScenarioEditView.as_view(), name="scenario_edit"),
    path("<uuid:scenario_id>/delete/", ScenarioDeleteView.as_view(), name="scenario_delete"),
    path("<uuid:scenario_id>/duplicate/", ScenarioDuplicateView.as_view(), name="scenario_duplicate"),
    path("<uuid:scenario_id>/branch/", ScenarioBranchView.as_view(), name="scenario_branch"),
    path("<uuid:scenario_id>/versions/", ScenarioVersionsView.as_view(), name="scenario_versions"),
    path("<uuid:scenario_id>/what-if/", WhatIfBranchView.as_view(), name="what_if_branch"),
    path("<uuid:scenario_id>/compare/", CompareSelectView.as_view(), name="compare_select"),
    path("<uuid:scenario_id>/compare/results/", CompareView.as_view(), name="compare_results"),
    path("<uuid:scenario_id>/ai-research/", AIResearchPlayersView.as_view(), name="ai_research_players"),

    # Issues
    path("<uuid:scenario_id>/issues/create/", IssueCreateView.as_view(), name="issue_create"),
    path("<uuid:scenario_id>/issues/<uuid:issue_id>/edit/", IssueEditView.as_view(), name="issue_edit"),
    path("<uuid:scenario_id>/issues/<uuid:issue_id>/delete/", IssueDeleteView.as_view(), name="issue_delete"),

    # Players
    path("<uuid:scenario_id>/players/create/", PlayerCreateView.as_view(), name="player_create"),
    path("<uuid:scenario_id>/players/<uuid:player_id>/edit/", PlayerEditView.as_view(), name="player_edit"),
    path("<uuid:scenario_id>/players/<uuid:player_id>/delete/", PlayerDeleteView.as_view(), name="player_delete"),

    # Player positions
    path(
        "<uuid:scenario_id>/players/<uuid:player_id>/issues/<uuid:issue_id>/position/",
        PlayerPositionEditView.as_view(),
        name="player_position_edit",
    ),

    # Simulation
    path("<uuid:scenario_id>/simulate/", RunSimulationView.as_view(), name="run_simulation"),
]
