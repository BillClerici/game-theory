"""
Load scenario data from fixture and reassign all user references
to the first superuser (or a specified email).

Usage:
    python manage.py load_scenario_data
    python manage.py load_scenario_data --email bill@example.com
    python manage.py load_scenario_data --file data/scenario_data.json
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

USER_FK_FIELDS = {"owner", "created_by", "updated_by", "user"}


class Command(BaseCommand):
    help = "Load scenario fixture data, reassigning all user FKs to a local user"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default="data/scenario_data.json",
            help="Path to the fixture JSON file (default: data/scenario_data.json)",
        )
        parser.add_argument(
            "--email",
            default="",
            help="Email of user to assign data to. Defaults to first superuser.",
        )

    def handle(self, *args, **options):
        filepath = Path(options["file"])
        if not filepath.exists():
            self.stderr.write(f"File not found: {filepath}")
            return

        # Find target user
        email = options["email"]
        if email:
            user = User.objects.filter(email=email).first()
            if not user:
                self.stderr.write(f"User {email} not found.")
                return
        else:
            user = User.objects.filter(is_superuser=True).first()
            if not user:
                self.stderr.write("No superuser found. Create one first or use --email.")
                return

        self.stdout.write(f"Assigning all data to: {user.email} ({user.pk})")

        # Load and patch the fixture
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        user_pk = str(user.pk)
        patched = 0
        for obj in data:
            fields = obj.get("fields", {})
            for field_name in USER_FK_FIELDS:
                if field_name in fields and fields[field_name] is not None:
                    fields[field_name] = user_pk
                    patched += 1

        self.stdout.write(f"Patched {patched} user references across {len(data)} objects")

        # Define which FK fields reference which model
        FK_TO_MODEL = {
            "scenario": "scenarios.scenario",
            "issue": "scenarios.scenarioissue",
            "player": "scenarios.player",
            "position": "scenarios.playerposition",
            "simulation_run": "engine.simulationrun",
            "session": "conversations.conversationsession",
        }

        # Iteratively strip orphaned records until stable
        clean_data = data
        total_stripped = 0
        while True:
            pk_sets: dict[str, set[str]] = {}
            for obj in clean_data:
                pk_sets.setdefault(obj["model"], set()).add(str(obj["pk"]))

            kept = []
            stripped = 0
            for obj in clean_data:
                fields = obj.get("fields", {})
                orphan = False
                for fk_field, target_model in FK_TO_MODEL.items():
                    if fk_field in fields and fields[fk_field]:
                        if target_model in pk_sets and str(fields[fk_field]) not in pk_sets[target_model]:
                            orphan = True
                            break
                if orphan:
                    stripped += 1
                else:
                    kept.append(obj)

            total_stripped += stripped
            clean_data = kept
            if stripped == 0:
                break

        if total_stripped:
            self.stdout.write(self.style.WARNING(f"Stripped {total_stripped} orphaned records"))

        # Sort objects by model dependency order before loading
        MODEL_ORDER = {
            'scenarios.scenario': 0,
            'scenarios.scenarioissue': 1,
            'scenarios.player': 2,
            'scenarios.playerposition': 3,
            'engine.simulationrun': 4,
            'engine.roundresult': 5,
            'engine.predictionoutcome': 6,
            'conversations.conversationsession': 7,
            'conversations.conversationmessage': 8,
        }
        clean_data.sort(key=lambda obj: MODEL_ORDER.get(obj['model'], 99))

        # Write patched fixture to temp file and load it
        temp_path = filepath.parent / "_patched_scenario_data.json"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(clean_data, f)

        from django.core.management import call_command
        call_command("loaddata", str(temp_path), verbosity=1)

        # Clean up temp file
        temp_path.unlink(missing_ok=True)

        # Count what was loaded
        from apps.scenarios.models import Scenario, ScenarioIssue, Player, PlayerPosition
        from apps.engine.models import SimulationRun, RoundResult, PredictionOutcome
        from apps.conversations.models import ConversationSession, ConversationMessage

        self.stdout.write(self.style.SUCCESS(
            f"\nLoaded:\n"
            f"  Scenarios:       {Scenario.objects.count()}\n"
            f"  Issues:          {ScenarioIssue.objects.count()}\n"
            f"  Players:         {Player.objects.count()}\n"
            f"  Positions:       {PlayerPosition.objects.count()}\n"
            f"  Simulation Runs: {SimulationRun.objects.count()}\n"
            f"  Round Results:   {RoundResult.objects.count()}\n"
            f"  Pred. Outcomes:  {PredictionOutcome.objects.count()}\n"
            f"  Chat Sessions:   {ConversationSession.objects.count()}\n"
            f"  Chat Messages:   {ConversationMessage.objects.count()}\n"
            f"\nAll assigned to: {user.email}"
        ))
