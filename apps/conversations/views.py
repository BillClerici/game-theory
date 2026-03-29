"""Chat views for scenario builder conversation and simulation analysis."""
from __future__ import annotations

import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.conversations.models import ConversationSession
from apps.conversations.services import (
    analyze_simulation,
    send_message,
    send_modifier_message,
    start_modifier_session,
    start_session,
)
from apps.scenarios.models import Scenario


class ScenarioBuilderChatView(LoginRequiredMixin, View):
    """Start or resume a scenario builder chat session."""

    def get(self, request, session_id=None):
        if session_id:
            session = get_object_or_404(
                ConversationSession, pk=session_id, user=request.user,
            )
        else:
            session = start_session(request.user)
            return redirect("chat_session", session_id=session.pk)

        chat_messages = list(
            session.messages.filter(role__in=["user", "assistant"]).order_by("message_order")
        )

        return render(request, "conversations/chat.html", {
            "session": session,
            "chat_messages": chat_messages,
            "scenario_created": session.scenario_id is not None,
            "scenario_id": str(session.scenario_id) if session.scenario_id else None,
        })


class ChatSendMessageView(LoginRequiredMixin, View):
    """AJAX endpoint to send a message and get LLM response."""

    def post(self, request, session_id):
        session = get_object_or_404(
            ConversationSession, pk=session_id, user=request.user,
        )

        try:
            body = json.loads(request.body)
            user_message = body.get("message", "").strip()
        except (json.JSONDecodeError, AttributeError):
            user_message = request.POST.get("message", "").strip()

        if not user_message:
            return JsonResponse({"error": "Empty message"}, status=400)

        try:
            result = send_message(session, user_message)
            return JsonResponse({
                "assistant_message": result["assistant_message"],
                "scenario_created": result["scenario_created"],
                "scenario_id": result.get("scenario_id"),
            })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


class SimulationAnalysisView(LoginRequiredMixin, View):
    """Run LLM analysis on simulation results."""

    def post(self, request, scenario_id):
        scenario = get_object_or_404(Scenario, pk=scenario_id, owner=request.user)
        force_refresh = request.GET.get("refresh") == "1"
        optimize_for = request.GET.get("optimize_for", "")

        try:
            analysis = analyze_simulation(
                scenario, request.user,
                force_refresh=force_refresh,
                optimize_for_player_id=optimize_for or None,
            )
            return JsonResponse({"analysis": analysis})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    def get(self, request, scenario_id):
        """Show analysis page. If a cached report exists, render it directly."""
        from apps.engine.models import SimulationRun
        from apps.scenarios.models import Player

        scenario = get_object_or_404(
            Scenario.objects.select_related("scenario_type", "status"),
            pk=scenario_id,
            owner=request.user,
        )

        optimize_for = request.GET.get("optimize_for", "")
        optimize_player = None
        if optimize_for:
            optimize_player = Player.objects.filter(pk=optimize_for, scenario=scenario).first()

        # Check for specific run or default to latest
        run_id = request.GET.get("run")
        if run_id:
            sim_run = SimulationRun.objects.filter(
                pk=run_id, scenario=scenario,
            ).select_related("status").first()
        else:
            sim_run = SimulationRun.objects.filter(
                scenario=scenario,
            ).select_related("status").first()

        # Only use cached report for general analysis (no player focus)
        cached_report = ""
        if sim_run and not optimize_for:
            cached_report = sim_run.analysis_report or ""

        return render(request, "conversations/analysis.html", {
            "scenario": scenario,
            "sim_run": sim_run,
            "cached_report": cached_report,
            "optimize_for": optimize_for,
            "optimize_player": optimize_player,
        })


class AnalysisHistoryView(LoginRequiredMixin, View):
    """List all simulation runs with their analysis reports."""

    def get(self, request, scenario_id):
        from apps.engine.models import SimulationRun

        scenario = get_object_or_404(Scenario, pk=scenario_id, owner=request.user)
        runs = SimulationRun.objects.filter(
            scenario=scenario,
        ).select_related("status").order_by("-created_at")

        return render(request, "conversations/analysis_history.html", {
            "scenario": scenario,
            "runs": runs,
        })


class ScenarioModifierChatView(LoginRequiredMixin, View):
    """Start or resume a modifier chat for an existing scenario."""

    def get(self, request, scenario_id, session_id=None):
        scenario = get_object_or_404(Scenario, pk=scenario_id, owner=request.user)

        if session_id:
            session = get_object_or_404(
                ConversationSession, pk=session_id, user=request.user, scenario=scenario,
            )
        else:
            session = start_modifier_session(scenario, request.user)
            return redirect("modifier_chat_session", scenario_id=scenario.pk, session_id=session.pk)

        chat_messages = list(
            session.messages.filter(role__in=["user", "assistant"]).order_by("message_order")
        )

        return render(request, "conversations/modifier_chat.html", {
            "session": session,
            "scenario": scenario,
            "chat_messages": chat_messages,
        })


class ModifierSendMessageView(LoginRequiredMixin, View):
    """AJAX endpoint for modifier chat messages."""

    def post(self, request, session_id):
        session = get_object_or_404(
            ConversationSession, pk=session_id, user=request.user,
        )

        try:
            body = json.loads(request.body)
            user_message = body.get("message", "").strip()
        except (json.JSONDecodeError, AttributeError):
            user_message = request.POST.get("message", "").strip()

        if not user_message:
            return JsonResponse({"error": "Empty message"}, status=400)

        try:
            result = send_modifier_message(session, user_message)
            return JsonResponse({"assistant_message": result["assistant_message"]})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
