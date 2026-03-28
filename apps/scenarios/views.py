"""Scenario management views — CRUD for scenarios, issues, players, positions + simulation."""
from __future__ import annotations

import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from apps.engine.services import compute_data_quality_score, run_simulation, validate_scenario
from apps.engine.models import SimulationRun
from apps.lookup.models import LookupValue
from apps.scenarios.forms import PlayerForm, PlayerPositionForm, ScenarioForm, ScenarioIssueForm
from apps.scenarios.models import Player, PlayerPosition, Scenario, ScenarioIssue
from apps.scenarios.services import branch_scenario, compare_scenarios, duplicate_scenario, get_version_history


class OwnerRequiredMixin(LoginRequiredMixin):
    """Ensure the current user owns the scenario."""

    def get_scenario(self):
        return get_object_or_404(Scenario, pk=self.kwargs["scenario_id"], owner=self.request.user)


# ── Scenario CRUD ──

class ScenarioListView(LoginRequiredMixin, ListView):
    model = Scenario
    template_name = "scenarios/scenario_list.html"

    def get_queryset(self):
        qs = Scenario.objects.filter(owner=self.request.user)
        status_filter = self.request.GET.get("status", "")
        if status_filter:
            qs = qs.filter(status__code=status_filter)
        search = self.request.GET.get("q", "")
        if search:
            qs = qs.filter(title__icontains=search)
        return qs.select_related("scenario_type", "status")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "My Scenarios"
        # Get status options for filter dropdown
        status_parent = LookupValue.objects.filter(parent__isnull=True, code="SCENARIO_STATUS").first()
        ctx["status_options"] = LookupValue.objects.filter(parent=status_parent) if status_parent else []
        ctx["current_status"] = self.request.GET.get("status", "")
        ctx["search_query"] = self.request.GET.get("q", "")
        return ctx


class ScenarioCreateView(LoginRequiredMixin, CreateView):
    model = Scenario
    form_class = ScenarioForm
    template_name = "admin/form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Create Scenario"
        ctx["icon"] = "psychology"
        ctx["cancel_url"] = reverse("scenario_list")
        return ctx

    def form_valid(self, form):
        scenario = form.save(commit=False)
        scenario.owner = self.request.user
        scenario.created_by = self.request.user
        scenario.updated_by = self.request.user
        # Default status = draft
        status_parent = LookupValue.objects.get(parent__isnull=True, code="SCENARIO_STATUS")
        scenario.status = LookupValue.objects.get(parent=status_parent, code="DRAFT")
        scenario.save()
        messages.success(self.request, f'Scenario "{scenario.title}" created.')
        return redirect("scenario_detail", scenario_id=scenario.pk)


class ScenarioEditView(LoginRequiredMixin, UpdateView):
    model = Scenario
    form_class = ScenarioForm
    template_name = "admin/form.html"
    pk_url_kwarg = "scenario_id"

    def get_queryset(self):
        return Scenario.objects.filter(owner=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = f"Edit Scenario: {self.object.title}"
        ctx["icon"] = "edit"
        ctx["cancel_url"] = reverse("scenario_detail", args=[self.object.pk])
        return ctx

    def form_valid(self, form):
        scenario = form.save(commit=False)
        scenario.updated_by = self.request.user
        scenario.save()
        messages.success(self.request, f'Scenario "{scenario.title}" updated.')
        return redirect("scenario_detail", scenario_id=scenario.pk)


class ScenarioDeleteView(LoginRequiredMixin, View):
    def get(self, request, scenario_id):
        scenario = get_object_or_404(Scenario, pk=scenario_id, owner=request.user)
        return render(request, "admin/delete.html", {
            "object_name": scenario.title,
            "cancel_url": reverse("scenario_list"),
        })

    def post(self, request, scenario_id):
        scenario = get_object_or_404(Scenario, pk=scenario_id, owner=request.user)
        scenario.is_active = False
        scenario.save(update_fields=["is_active", "updated_at"])
        messages.success(request, f'Scenario "{scenario.title}" archived.')
        return redirect("scenario_list")


class ScenarioDetailView(LoginRequiredMixin, View):
    """Main scenario workspace — shows issues, players, simulation results."""

    def get(self, request, scenario_id):
        scenario = get_object_or_404(
            Scenario.objects.select_related("scenario_type", "status", "owner"),
            pk=scenario_id,
            owner=request.user,
        )
        issues = scenario.issues.filter(is_active=True)
        players = scenario.players.filter(is_active=True).select_related("player_type")

        issues = list(issues)
        players = list(players)

        # Build position grid: {player_id: {issue_id: position_obj}}
        positions = PlayerPosition.objects.filter(
            player__in=players,
            issue__in=issues,
            is_active=True,
        ).select_related("player", "issue", "risk_profile")
        position_grid: dict = {}
        for pp in positions:
            position_grid.setdefault(str(pp.player_id), {})[str(pp.issue_id)] = pp

        # Attach position_display list to each player for template rendering
        for player in players:
            display = []
            player_positions = position_grid.get(str(player.pk), {})
            for issue in issues:
                pp = player_positions.get(str(issue.pk))
                edit_url = reverse(
                    "player_position_edit",
                    args=[scenario.pk, player.pk, issue.pk],
                )
                if pp:
                    display.append({
                        "has_position": True,
                        "position": pp.position,
                        "capability": pp.capability,
                        "salience": pp.salience,
                        "edit_url": edit_url,
                    })
                else:
                    display.append({
                        "has_position": False,
                        "edit_url": edit_url,
                    })
            player.position_display = display

        # Data quality
        quality = compute_data_quality_score(scenario)
        validation_errors = validate_scenario(scenario)

        # Latest simulation
        latest_sim = SimulationRun.objects.filter(
            scenario=scenario,
        ).select_related("status").first()

        prediction_outcomes = []
        round_data = []
        if latest_sim:
            prediction_outcomes = list(
                latest_sim.prediction_outcomes.all().select_related("issue", "outcome_stability")
            )
            # Round data for visualization
            round_data = list(
                latest_sim.round_results.all()
                .select_related("player", "issue")
                .order_by("round_number", "player__name")
            )

        # Build JSON for stakeholder map visualization
        position_data = []
        for pp in positions:
            position_data.append({
                "name": pp.player.name,
                "position": float(pp.position),
                "capability": float(pp.capability),
                "salience": float(pp.salience),
                "player_id": str(pp.player_id),
            })

        # Build JSON for timeline chart
        round_data_json = [
            {
                "round_number": r.round_number,
                "player_name": r.player.name,
                "player_id": str(r.player_id),
                "position_start": float(r.position_start),
                "position_end": float(r.position_end),
            }
            for r in round_data
        ]

        return render(request, "scenarios/scenario_detail.html", {
            "scenario": scenario,
            "issues": issues,
            "players": players,
            "position_grid": position_grid,
            "quality": quality,
            "validation_errors": validation_errors,
            "latest_sim": latest_sim,
            "prediction_outcomes": prediction_outcomes,
            "round_data": round_data,
            "position_data_json": json.dumps(position_data),
            "round_data_json": json.dumps(round_data_json),
        })


class ScenarioDuplicateView(LoginRequiredMixin, View):
    def post(self, request, scenario_id):
        scenario = get_object_or_404(Scenario, pk=scenario_id, owner=request.user)
        new_scenario = duplicate_scenario(scenario, request.user)
        messages.success(request, f'Scenario duplicated as "{new_scenario.title}".')
        return redirect("scenario_detail", scenario_id=new_scenario.pk)


class ScenarioBranchView(LoginRequiredMixin, View):
    def post(self, request, scenario_id):
        scenario = get_object_or_404(Scenario, pk=scenario_id, owner=request.user)
        label = request.POST.get("version_label", "")
        new_scenario = branch_scenario(scenario, request.user, label)
        messages.success(request, f'Branch v{new_scenario.version_number} created.')
        return redirect("scenario_detail", scenario_id=new_scenario.pk)


class ScenarioVersionsView(LoginRequiredMixin, View):
    def get(self, request, scenario_id):
        scenario = get_object_or_404(Scenario, pk=scenario_id, owner=request.user)
        versions = get_version_history(scenario)
        return render(request, "scenarios/scenario_versions.html", {
            "scenario": scenario,
            "versions": versions,
        })


# ── Issue CRUD ──

class IssueCreateView(LoginRequiredMixin, CreateView):
    model = ScenarioIssue
    form_class = ScenarioIssueForm
    template_name = "admin/form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        scenario = get_object_or_404(Scenario, pk=self.kwargs["scenario_id"], owner=self.request.user)
        ctx["page_title"] = f"Add Issue to {scenario.title}"
        ctx["icon"] = "topic"
        ctx["cancel_url"] = reverse("scenario_detail", args=[scenario.pk])
        return ctx

    def form_valid(self, form):
        scenario = get_object_or_404(Scenario, pk=self.kwargs["scenario_id"], owner=self.request.user)
        issue = form.save(commit=False)
        issue.scenario = scenario
        issue.save()
        messages.success(self.request, f'Issue "{issue.title}" added.')
        return redirect("scenario_detail", scenario_id=scenario.pk)


class IssueEditView(LoginRequiredMixin, UpdateView):
    model = ScenarioIssue
    form_class = ScenarioIssueForm
    template_name = "admin/form.html"
    pk_url_kwarg = "issue_id"

    def get_queryset(self):
        return ScenarioIssue.objects.filter(
            scenario_id=self.kwargs["scenario_id"],
            scenario__owner=self.request.user,
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = f"Edit Issue: {self.object.title}"
        ctx["icon"] = "edit"
        ctx["cancel_url"] = reverse("scenario_detail", args=[self.kwargs["scenario_id"]])
        return ctx

    def form_valid(self, form):
        form.save()
        messages.success(self.request, f'Issue "{form.instance.title}" updated.')
        return redirect("scenario_detail", scenario_id=self.kwargs["scenario_id"])


class IssueDeleteView(LoginRequiredMixin, View):
    def get(self, request, scenario_id, issue_id):
        issue = get_object_or_404(
            ScenarioIssue, pk=issue_id, scenario_id=scenario_id, scenario__owner=request.user,
        )
        return render(request, "admin/delete.html", {
            "object_name": issue.title,
            "cancel_url": reverse("scenario_detail", args=[scenario_id]),
        })

    def post(self, request, scenario_id, issue_id):
        issue = get_object_or_404(
            ScenarioIssue, pk=issue_id, scenario_id=scenario_id, scenario__owner=request.user,
        )
        issue.is_active = False
        issue.save(update_fields=["is_active", "updated_at"])
        messages.success(request, f'Issue "{issue.title}" removed.')
        return redirect("scenario_detail", scenario_id=scenario_id)


# ── Player CRUD ──

class PlayerCreateView(LoginRequiredMixin, CreateView):
    model = Player
    form_class = PlayerForm
    template_name = "admin/form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        scenario = get_object_or_404(Scenario, pk=self.kwargs["scenario_id"], owner=self.request.user)
        ctx["page_title"] = f"Add Player to {scenario.title}"
        ctx["icon"] = "person_add"
        ctx["cancel_url"] = reverse("scenario_detail", args=[scenario.pk])
        return ctx

    def form_valid(self, form):
        scenario = get_object_or_404(Scenario, pk=self.kwargs["scenario_id"], owner=self.request.user)
        player = form.save(commit=False)
        player.scenario = scenario
        player.save()
        messages.success(self.request, f'Player "{player.name}" added.')
        return redirect("scenario_detail", scenario_id=scenario.pk)


class PlayerEditView(LoginRequiredMixin, UpdateView):
    model = Player
    form_class = PlayerForm
    template_name = "admin/form.html"
    pk_url_kwarg = "player_id"

    def get_queryset(self):
        return Player.objects.filter(
            scenario_id=self.kwargs["scenario_id"],
            scenario__owner=self.request.user,
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = f"Edit Player: {self.object.name}"
        ctx["icon"] = "edit"
        ctx["cancel_url"] = reverse("scenario_detail", args=[self.kwargs["scenario_id"]])
        return ctx

    def form_valid(self, form):
        form.save()
        messages.success(self.request, f'Player "{form.instance.name}" updated.')
        return redirect("scenario_detail", scenario_id=self.kwargs["scenario_id"])


class PlayerDeleteView(LoginRequiredMixin, View):
    def get(self, request, scenario_id, player_id):
        player = get_object_or_404(
            Player, pk=player_id, scenario_id=scenario_id, scenario__owner=request.user,
        )
        return render(request, "admin/delete.html", {
            "object_name": player.name,
            "cancel_url": reverse("scenario_detail", args=[scenario_id]),
        })

    def post(self, request, scenario_id, player_id):
        player = get_object_or_404(
            Player, pk=player_id, scenario_id=scenario_id, scenario__owner=request.user,
        )
        player.is_active = False
        player.save(update_fields=["is_active", "updated_at"])
        messages.success(request, f'Player "{player.name}" removed.')
        return redirect("scenario_detail", scenario_id=scenario_id)


# ── Player Position ──

class PlayerPositionEditView(LoginRequiredMixin, View):
    """Edit a single player's position on a single issue."""

    def get(self, request, scenario_id, player_id, issue_id):
        scenario = get_object_or_404(Scenario, pk=scenario_id, owner=request.user)
        player = get_object_or_404(Player, pk=player_id, scenario=scenario)
        issue = get_object_or_404(ScenarioIssue, pk=issue_id, scenario=scenario)

        position, _ = PlayerPosition.objects.get_or_create(
            player=player,
            issue=issue,
            defaults={
                "position": 50,
                "capability": 50,
                "salience": 50,
                "flexibility": 50,
                "risk_profile": LookupValue.objects.get(
                    parent__code="RISK_PROFILE", code="RISK_NEUTRAL",
                ),
            },
        )
        form = PlayerPositionForm(instance=position)
        return render(request, "admin/form.html", {
            "form": form,
            "page_title": f"{player.name} — {issue.title}",
            "icon": "tune",
            "cancel_url": reverse("scenario_detail", args=[scenario_id]),
        })

    def post(self, request, scenario_id, player_id, issue_id):
        scenario = get_object_or_404(Scenario, pk=scenario_id, owner=request.user)
        player = get_object_or_404(Player, pk=player_id, scenario=scenario)
        issue = get_object_or_404(ScenarioIssue, pk=issue_id, scenario=scenario)

        position, _ = PlayerPosition.objects.get_or_create(
            player=player,
            issue=issue,
            defaults={
                "position": 50,
                "capability": 50,
                "salience": 50,
                "flexibility": 50,
                "risk_profile": LookupValue.objects.get(
                    parent__code="RISK_PROFILE", code="RISK_NEUTRAL",
                ),
            },
        )
        form = PlayerPositionForm(request.POST, instance=position)
        if form.is_valid():
            form.save()
            messages.success(request, f"Position for {player.name} on {issue.title} saved.")
            return redirect("scenario_detail", scenario_id=scenario_id)

        return render(request, "admin/form.html", {
            "form": form,
            "page_title": f"{player.name} — {issue.title}",
            "icon": "tune",
            "cancel_url": reverse("scenario_detail", args=[scenario_id]),
        })


# ── Simulation ──

class RunSimulationView(LoginRequiredMixin, View):
    def post(self, request, scenario_id):
        scenario = get_object_or_404(Scenario, pk=scenario_id, owner=request.user)

        errors = validate_scenario(scenario)
        if errors:
            for err in errors:
                messages.error(request, err)
            return redirect("scenario_detail", scenario_id=scenario_id)

        try:
            sim_run = run_simulation(scenario, request.user)
            messages.success(
                request,
                f"Simulation complete in {sim_run.execution_time_ms}ms. "
                f"Predicted outcome: {sim_run.predicted_outcome} "
                f"(confidence: {sim_run.confidence_score})",
            )
        except Exception as e:
            messages.error(request, f"Simulation failed: {e}")

        return redirect("scenario_detail", scenario_id=scenario_id)


# ── What-If Branch ──

class WhatIfBranchView(LoginRequiredMixin, View):
    """Create a branch and redirect to AI Modify chat for quick parameter changes."""

    def post(self, request, scenario_id):
        scenario = get_object_or_404(Scenario, pk=scenario_id, owner=request.user)
        label = request.POST.get("version_label", "What-If")
        new_scenario = branch_scenario(scenario, request.user, label)
        messages.success(request, f'What-If branch v{new_scenario.version_number} created.')
        return redirect("modifier_chat_new", scenario_id=new_scenario.pk)


# ── Compare ──

class CompareSelectView(LoginRequiredMixin, View):
    """Select which versions to compare."""

    def get(self, request, scenario_id):
        scenario = get_object_or_404(Scenario, pk=scenario_id, owner=request.user)
        versions = get_version_history(scenario)

        # Annotate each version with latest sim info
        for v in versions:
            v.latest_sim = SimulationRun.objects.filter(scenario=v).select_related("status").first()

        return render(request, "scenarios/compare_select.html", {
            "scenario": scenario,
            "versions": versions,
        })


class CompareView(LoginRequiredMixin, View):
    """Side-by-side comparison of selected scenario versions."""

    def get(self, request, scenario_id):
        scenario = get_object_or_404(Scenario, pk=scenario_id, owner=request.user)

        selected_ids = request.GET.getlist("v")
        if len(selected_ids) < 2:
            messages.error(request, "Select at least 2 versions to compare.")
            return redirect("compare_select", scenario_id=scenario_id)
        if len(selected_ids) > 4:
            selected_ids = selected_ids[:4]

        comparison = compare_scenarios(selected_ids)

        if "error" in comparison:
            messages.error(request, comparison["error"])
            return redirect("compare_select", scenario_id=scenario_id)

        return render(request, "scenarios/compare.html", {
            "scenario": scenario,
            "comparison": comparison,
            "comparison_json": json.dumps(comparison),
        })
