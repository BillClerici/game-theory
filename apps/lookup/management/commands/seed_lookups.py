from django.core.management.base import BaseCommand
from apps.lookup.models import LookupValue


LOOKUP_SEED = {
    # Existing GSD lookups
    'CUSTOMER_TYPE': ['Enterprise', 'SMB', 'Startup', 'Individual'],
    'EMPLOYEE_TYPE': ['Full-time', 'Part-time', 'Contractor', 'Intern'],
    'BUSINESS_CATEGORY': ['Financial Services', 'Healthcare', 'Technology', 'Retail'],
    'STATUS': ['Active', 'Inactive', 'Pending', 'Suspended'],
    # Game Theory domain lookups
    'SCENARIO_TYPE': [
        ('GEOPOLITICAL', 'Geopolitical'),
        ('CORPORATE', 'Corporate'),
        ('LEGISLATIVE', 'Legislative'),
        ('LEGAL', 'Legal'),
        ('MARKET', 'Market'),
        ('NEGOTIATION', 'Negotiation'),
        ('PERSONAL', 'Personal'),
        ('CUSTOM', 'Custom'),
    ],
    'SCENARIO_STATUS': [
        ('DRAFT', 'Draft'),
        ('READY', 'Ready'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('ARCHIVED', 'Archived'),
    ],
    'PLAYER_TYPE': [
        ('INDIVIDUAL', 'Individual'),
        ('ORGANIZATION', 'Organization'),
        ('GOVERNMENT', 'Government'),
        ('COALITION_BLOC', 'Coalition / Bloc'),
        ('INSTITUTION', 'Institution'),
        ('OTHER', 'Other'),
    ],
    'RISK_PROFILE': [
        ('RISK_AVERSE', 'Risk Averse'),
        ('RISK_NEUTRAL', 'Risk Neutral'),
        ('RISK_ACCEPTANT', 'Risk Acceptant'),
    ],
    'USER_ROLE': [
        ('ADMIN', 'Admin'),
        ('ANALYST', 'Analyst'),
        ('VIEWER', 'Viewer'),
    ],
    'SUBSCRIPTION_TIER': [
        ('FREE', 'Free'),
        ('PRO', 'Pro'),
        ('ENTERPRISE', 'Enterprise'),
    ],
    'SIMULATION_STATUS': [
        ('QUEUED', 'Queued'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ],
    'OUTCOME_STABILITY': [
        ('STABLE', 'Stable'),
        ('FRAGILE', 'Fragile'),
        ('DEADLOCKED', 'Deadlocked'),
    ],
    'COALITION_TYPE': [
        ('DETECTED', 'Detected'),
        ('USER_DEFINED', 'User Defined'),
        ('HYPOTHETICAL', 'Hypothetical'),
    ],
    'RECOMMENDATION_TYPE': [
        ('POSITION_SHIFT', 'Position Shift'),
        ('COALITION_BUILD', 'Coalition Build'),
        ('COALITION_FRACTURE', 'Coalition Fracture'),
        ('SALIENCE_INCREASE', 'Salience Increase'),
        ('CAPABILITY_REDUCTION', 'Capability Reduction'),
        ('ALLIANCE_FORMATION', 'Alliance Formation'),
    ],
    'CONVERSATION_SESSION_TYPE': [
        ('SCENARIO_BUILDER', 'Scenario Builder'),
        ('ANALYSIS_REVIEW', 'Analysis Review'),
        ('STRATEGY_ADVISOR', 'Strategy Advisor'),
        ('GENERAL', 'General'),
    ],
    'CONVERSATION_STATUS': [
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('ABANDONED', 'Abandoned'),
    ],
    'SENSITIVITY_TYPE': [
        ('OAT', 'One-at-a-Time'),
        ('MONTE_CARLO', 'Monte Carlo'),
    ],
}


class Command(BaseCommand):
    help = "Seed the LookupValue table with default types and values (idempotent)"

    def handle(self, *args, **options):
        for type_code, values in LOOKUP_SEED.items():
            parent, created = LookupValue.all_objects.get_or_create(
                parent=None,
                code=type_code,
                defaults={'label': type_code.replace('_', ' ').title()},
            )
            status = "created" if created else "exists"
            self.stdout.write(f"  [{status}] Type: {type_code}")

            for i, val in enumerate(values):
                if isinstance(val, tuple):
                    val_code, val_label = val
                else:
                    val_label = val
                    val_code = val_label.upper().replace(' ', '_').replace('-', '_')

                _, val_created = LookupValue.all_objects.get_or_create(
                    parent=parent,
                    code=val_code,
                    defaults={'label': val_label, 'sort_order': i},
                )
                if val_created:
                    self.stdout.write(self.style.SUCCESS(f"    [+] {val_label}"))

        self.stdout.write(self.style.SUCCESS("Lookup seed complete."))
