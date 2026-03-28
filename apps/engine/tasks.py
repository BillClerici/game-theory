"""Celery tasks for async simulation execution."""
from __future__ import annotations

import uuid
from typing import Any

from celery import shared_task
from django.contrib.auth import get_user_model

User = get_user_model()


@shared_task(bind=True, max_retries=1, default_retry_delay=5)
def run_simulation_task(
    self,
    scenario_id: str,
    user_id: str,
    params: dict[str, Any] | None = None,
) -> str:
    """Run BDM simulation as an async Celery task. Returns simulation run ID."""
    from apps.engine.services import run_simulation
    from apps.scenarios.models import Scenario

    scenario = Scenario.objects.get(pk=uuid.UUID(scenario_id))
    user = User.objects.get(pk=uuid.UUID(user_id))
    sim_run = run_simulation(scenario, user, params)
    return str(sim_run.pk)
