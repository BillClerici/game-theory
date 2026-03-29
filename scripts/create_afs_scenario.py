"""Create the AFS Mainframe to AFS Vision scenario."""
import os, sys, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
django.setup()

from decimal import Decimal
from django.contrib.auth import get_user_model
from apps.lookup.models import LookupValue
from apps.scenarios.models import Scenario, ScenarioIssue, Player, PlayerPosition

User = get_user_model()
user = User.objects.get(email="bill@1200investing.com")

type_parent = LookupValue.objects.get(parent__isnull=True, code="SCENARIO_TYPE")
scenario_type = LookupValue.objects.get(parent=type_parent, code="CORPORATE")
status_parent = LookupValue.objects.get(parent__isnull=True, code="SCENARIO_STATUS")
draft_status = LookupValue.objects.get(parent=status_parent, code="DRAFT")
pt_parent = LookupValue.objects.get(parent__isnull=True, code="PLAYER_TYPE")
individual = LookupValue.objects.get(parent=pt_parent, code="INDIVIDUAL")
org = LookupValue.objects.get(parent=pt_parent, code="ORGANIZATION")
institution = LookupValue.objects.get(parent=pt_parent, code="INSTITUTION")
coalition = LookupValue.objects.get(parent=pt_parent, code="COALITION_BLOC")
risk_parent = LookupValue.objects.get(parent__isnull=True, code="RISK_PROFILE")
risk_averse = LookupValue.objects.get(parent=risk_parent, code="RISK_AVERSE")
risk_neutral = LookupValue.objects.get(parent=risk_parent, code="RISK_NEUTRAL")
risk_acceptant = LookupValue.objects.get(parent=risk_parent, code="RISK_ACCEPTANT")

scenario = Scenario.objects.create(
    title="AFS Mainframe to AFS Vision Transformation",
    description="Predicting the delivery outcome of a major core banking system conversion from AFS Mainframe to AFS Vision (Fiserv) at a mid-size financial institution. The transformation involves data migration, parallel running, regulatory compliance, staff retraining, and integration with dozens of downstream systems. Most large-scale core banking conversions experience significant delays and scope reductions.",
    scenario_type=scenario_type,
    status=draft_status,
    owner=user,
    created_by=user,
    updated_by=user,
)

i1 = ScenarioIssue.objects.create(
    scenario=scenario,
    title="Delivery Timeline",
    description="Will the transformation be delivered on the planned timeline?",
    scale_min_label="Project shelved or 2+ years delayed",
    scale_max_label="On-time delivery per original schedule",
    status_quo_position=30,
    sort_order=0,
)
i2 = ScenarioIssue.objects.create(
    scenario=scenario,
    title="Scope Completeness",
    description="How much of the planned scope will be delivered at go-live?",
    scale_min_label="Minimal viable conversion (core only, heavy workarounds)",
    scale_max_label="Full feature parity with enhancements and automation",
    status_quo_position=25,
    sort_order=1,
)
i3 = ScenarioIssue.objects.create(
    scenario=scenario,
    title="Budget Adherence",
    description="Will the project stay within budget?",
    scale_min_label="200%+ budget overrun or project abandoned",
    scale_max_label="At or under original budget",
    status_quo_position=25,
    sort_order=2,
)
issues = [i1, i2, i3]

players = [
    {"name": "CIO / Executive Sponsor", "desc": "Championed the transformation to the board. Career reputation tied to success. Controls project funding and can adjust timeline.", "type": individual,
     "pos": [
         {"pos": 75, "cap": 80, "sal": 85, "flex": 40, "risk": risk_neutral},
         {"pos": 70, "cap": 75, "sal": 70, "flex": 45, "risk": risk_neutral},
         {"pos": 65, "cap": 80, "sal": 75, "flex": 50, "risk": risk_neutral},
     ]},
    {"name": "Fiserv (AFS Vision Vendor)", "desc": "Selling and implementing AFS Vision. Wants a successful reference client. Product roadmap is fixed with limited customization.", "type": org,
     "pos": [
         {"pos": 80, "cap": 65, "sal": 60, "flex": 20, "risk": risk_neutral},
         {"pos": 55, "cap": 60, "sal": 50, "flex": 15, "risk": risk_neutral},
         {"pos": 70, "cap": 55, "sal": 55, "flex": 20, "risk": risk_neutral},
     ]},
    {"name": "Project Manager / PMO", "desc": "Running day-to-day delivery. Sees the real status. Moderate power but high salience.", "type": individual,
     "pos": [
         {"pos": 50, "cap": 45, "sal": 95, "flex": 55, "risk": risk_averse},
         {"pos": 45, "cap": 40, "sal": 90, "flex": 60, "risk": risk_averse},
         {"pos": 40, "cap": 35, "sal": 85, "flex": 50, "risk": risk_averse},
     ]},
    {"name": "Business Unit Leaders", "desc": "Heads of lending, deposits, treasury. Need the system to work daily. Want full scope but resistant to change during busy periods.", "type": coalition,
     "pos": [
         {"pos": 45, "cap": 55, "sal": 75, "flex": 35, "risk": risk_averse},
         {"pos": 85, "cap": 60, "sal": 85, "flex": 30, "risk": risk_averse},
         {"pos": 50, "cap": 45, "sal": 60, "flex": 40, "risk": risk_averse},
     ]},
    {"name": "Core Banking Operations Team", "desc": "Run AFS Mainframe daily. Deep institutional knowledge. Fear job changes and loss of expertise advantage.", "type": coalition,
     "pos": [
         {"pos": 25, "cap": 40, "sal": 90, "flex": 25, "risk": risk_averse},
         {"pos": 30, "cap": 35, "sal": 85, "flex": 20, "risk": risk_averse},
         {"pos": 35, "cap": 30, "sal": 70, "flex": 30, "risk": risk_averse},
     ]},
    {"name": "IT Infrastructure & Data Migration", "desc": "Must provision environments, handle data migration, manage parallel running, integrate with 40+ downstream systems.", "type": coalition,
     "pos": [
         {"pos": 35, "cap": 50, "sal": 80, "flex": 40, "risk": risk_averse},
         {"pos": 40, "cap": 55, "sal": 75, "flex": 35, "risk": risk_averse},
         {"pos": 30, "cap": 50, "sal": 80, "flex": 35, "risk": risk_averse},
     ]},
    {"name": "Compliance / Risk / Audit", "desc": "Regulatory requirements for core banking are strict. Can veto go-live if compliance gaps exist. OCC and FDIC expectations.", "type": institution,
     "pos": [
         {"pos": 30, "cap": 70, "sal": 65, "flex": 10, "risk": risk_averse},
         {"pos": 60, "cap": 65, "sal": 80, "flex": 10, "risk": risk_averse},
         {"pos": 40, "cap": 60, "sal": 55, "flex": 15, "risk": risk_averse},
     ]},
    {"name": "Board / Executive Committee", "desc": "Controls overall budget and strategic direction. Gets quarterly updates. Will change direction if ROI story weakens.", "type": coalition,
     "pos": [
         {"pos": 65, "cap": 75, "sal": 45, "flex": 50, "risk": risk_averse},
         {"pos": 55, "cap": 65, "sal": 40, "flex": 55, "risk": risk_averse},
         {"pos": 80, "cap": 80, "sal": 70, "flex": 30, "risk": risk_averse},
     ]},
    {"name": "End Users (Branch & Operations)", "desc": "Must learn the new system. Training burden is significant. Low formal power but high adoption impact.", "type": coalition,
     "pos": [
         {"pos": 35, "cap": 25, "sal": 80, "flex": 50, "risk": risk_averse},
         {"pos": 70, "cap": 20, "sal": 75, "flex": 55, "risk": risk_neutral},
         {"pos": 30, "cap": 15, "sal": 50, "flex": 60, "risk": risk_neutral},
     ]},
    {"name": "Systems Integrator (Consulting Firm)", "desc": "External implementation partner. Billable hours incentive may not align with fast delivery. Deep expertise but expensive.", "type": org,
     "pos": [
         {"pos": 60, "cap": 50, "sal": 55, "flex": 45, "risk": risk_neutral},
         {"pos": 65, "cap": 50, "sal": 50, "flex": 40, "risk": risk_neutral},
         {"pos": 35, "cap": 40, "sal": 45, "flex": 50, "risk": risk_neutral},
     ]},
]

for pd in players:
    player = Player.objects.create(
        scenario=scenario,
        name=pd["name"],
        description=pd["desc"],
        player_type=pd["type"],
    )
    for j, p in enumerate(pd["pos"]):
        PlayerPosition.objects.create(
            player=player,
            issue=issues[j],
            position=Decimal(str(p["pos"])),
            capability=Decimal(str(p["cap"])),
            salience=Decimal(str(p["sal"])),
            flexibility=Decimal(str(p["flex"])),
            risk_profile=p["risk"],
        )
    print(f"  Player: {pd['name']}")

print(f"\nScenario: {scenario.pk}")
print(f"URL: http://localhost:8001/scenarios/{scenario.pk}/")
