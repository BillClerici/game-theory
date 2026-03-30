from django.db.models import Count
from django.views.generic import TemplateView

from apps.scenarios.models import Scenario
from apps.engine.models import PredictionOutcome, SimulationRun


class LandingPageView(TemplateView):
    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        if user.is_authenticated:
            ctx["recent_scenarios"] = (
                Scenario.objects.filter(owner=user)
                .select_related("scenario_type", "status")[:6]
            )
            ctx["total_scenarios"] = Scenario.objects.filter(owner=user).count()
            ctx["completed_sims"] = SimulationRun.objects.filter(
                scenario__owner=user,
                status__code="COMPLETED",
            ).count()
            ctx["total_predictions"] = PredictionOutcome.objects.filter(
                simulation_run__scenario__owner=user,
            ).count()
            ctx["total_comparisons"] = (
                Scenario.objects.filter(owner=user)
                .annotate(sim_count=Count("simulation_runs"))
                .filter(sim_count__gt=1)
                .count()
            )
        return ctx


class ApplicationConfigView(TemplateView):
    template_name = "application_config.html"


class MethodologyView(TemplateView):
    template_name = "methodology.html"


class ScenarioGuideView(TemplateView):
    template_name = "scenario_guide.html"


class CaseStudyListView(TemplateView):
    template_name = "case_studies/list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.engine.models import SimulationRun
        # Case studies are public scenarios with version_label = difficulty
        qs = Scenario.objects.filter(is_public=True, version_label__in=["beginner", "medium", "complex"]).select_related("scenario_type", "status")

        search = self.request.GET.get("q", "")
        if search:
            qs = qs.filter(title__icontains=search)
        difficulty = self.request.GET.get("difficulty", "")
        if difficulty:
            qs = qs.filter(version_label=difficulty)
        sort = self.request.GET.get("sort", "difficulty")
        if sort == "title":
            qs = qs.order_by("title")
        elif sort == "type":
            qs = qs.order_by("scenario_type__label")
        else:
            order_map = {"beginner": 0, "medium": 1, "complex": 2}
            qs = sorted(qs, key=lambda s: order_map.get(s.version_label, 9))

        studies = []
        for s in qs:
            sim = SimulationRun.objects.filter(scenario=s).select_related("status").first()
            studies.append({"scenario": s, "sim": sim})
        ctx["studies"] = studies
        ctx["search_query"] = search
        ctx["current_difficulty"] = difficulty
        ctx["current_sort"] = sort
        return ctx


class CaseStudyDetailView(TemplateView):
    template_name = "case_studies/detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        import json
        from apps.engine.models import SimulationRun
        from apps.scenarios.models import PlayerPosition

        scenario = Scenario.objects.select_related("scenario_type", "status").get(
            pk=kwargs["scenario_id"], is_public=True,
        )
        issues = list(scenario.issues.filter(is_active=True))
        players = list(scenario.players.filter(is_active=True).select_related("player_type"))

        # Position data
        positions = PlayerPosition.objects.filter(
            player__in=players, issue__in=issues, is_active=True,
        ).select_related("player", "issue", "risk_profile")

        player_data = []
        for player in players:
            pps = [pp for pp in positions if pp.player_id == player.pk]
            player_data.append({"player": player, "positions": pps})

        # Simulation
        sim = SimulationRun.objects.filter(scenario=scenario).select_related("status").first()
        outcomes = []
        round_data = []
        if sim:
            outcomes = list(sim.prediction_outcomes.all().select_related("issue", "outcome_stability"))
            round_data = list(
                sim.round_results.all().select_related("player", "issue").order_by("round_number", "player__name")
            )

        # JSON for charts
        position_json = [
            {"name": pp.player.name, "position": float(pp.position), "capability": float(pp.capability), "salience": float(pp.salience)}
            for pp in positions
        ]
        round_json = [
            {"round": r.round_number, "player": r.player.name, "pos_start": float(r.position_start), "pos_end": float(r.position_end),
             "shift": round(float(r.position_end) - float(r.position_start), 2), "pressure": float(r.pressure_received)}
            for r in round_data
        ]

        ctx.update({
            "scenario": scenario,
            "issues": issues,
            "players": players,
            "player_data": player_data,
            "sim": sim,
            "outcomes": outcomes,
            "round_data": round_data,
            "position_json": json.dumps(position_json),
            "round_json": json.dumps(round_json),
        })
        return ctx
