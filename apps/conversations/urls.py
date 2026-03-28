from django.urls import path
from apps.conversations.views import (
    AnalysisHistoryView,
    ChatSendMessageView,
    ModifierSendMessageView,
    ScenarioBuilderChatView,
    ScenarioModifierChatView,
    SimulationAnalysisView,
)

urlpatterns = [
    # Scenario builder chat
    path("new/", ScenarioBuilderChatView.as_view(), name="chat_new"),
    path("<uuid:session_id>/", ScenarioBuilderChatView.as_view(), name="chat_session"),
    path("<uuid:session_id>/send/", ChatSendMessageView.as_view(), name="chat_send"),

    # Scenario modifier chat
    path("modify/<uuid:scenario_id>/", ScenarioModifierChatView.as_view(), name="modifier_chat_new"),
    path("modify/<uuid:scenario_id>/<uuid:session_id>/", ScenarioModifierChatView.as_view(), name="modifier_chat_session"),
    path("modifier/<uuid:session_id>/send/", ModifierSendMessageView.as_view(), name="modifier_chat_send"),

    # Simulation analysis
    path("analysis/<uuid:scenario_id>/", SimulationAnalysisView.as_view(), name="simulation_analysis"),
    path("analysis/<uuid:scenario_id>/history/", AnalysisHistoryView.as_view(), name="analysis_history"),
]
