from django.views.generic import TemplateView

from apps.scenarios.models import Scenario
from apps.engine.models import SimulationRun


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
        return ctx


class ApplicationConfigView(TemplateView):
    template_name = "application_config.html"


class MethodologyView(TemplateView):
    template_name = "methodology.html"
