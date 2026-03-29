"""
Seed 6 detailed case studies with full scenarios, players, positions,
and actual simulation results from the BDM engine.
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from apps.engine.services import run_simulation
from apps.lookup.models import LookupValue
from apps.scenarios.models import Player, PlayerPosition, Scenario, ScenarioIssue

User = get_user_model()

CASE_STUDIES = [
    # ── BEGINNER 1 ──
    {
        "title": "Choosing a Family Vacation Destination",
        "description": "A family of four must decide where to go on vacation. Each family member has different preferences, influence levels, and willingness to compromise. A classic example of multi-stakeholder decision-making in everyday life.",
        "difficulty": "beginner",
        "scenario_type": "PERSONAL",
        "issues": [
            {
                "title": "Vacation Destination",
                "description": "The choice ranges from a relaxing beach resort to an adventurous mountain trip.",
                "scale_min_label": "Beach resort (relaxation-focused)",
                "scale_max_label": "Mountain adventure (activity-focused)",
                "status_quo_position": 50,
            },
        ],
        "players": [
            {"name": "Dad", "description": "Wants a relaxing beach vacation. Works hard all year and wants to unwind. Has significant influence as the primary income earner.", "player_type": "INDIVIDUAL",
             "positions": [{"position": 15, "capability": 65, "salience": 70, "flexibility": 55, "risk_profile": "RISK_AVERSE"}]},
            {"name": "Mom", "description": "Prefers a mix of relaxation and activities. Acts as the family mediator and trip planner. High influence on logistics.", "player_type": "INDIVIDUAL",
             "positions": [{"position": 45, "capability": 70, "salience": 85, "flexibility": 70, "risk_profile": "RISK_NEUTRAL"}]},
            {"name": "Teenage Daughter", "description": "Wants adventure and Instagram-worthy experiences. Mountains, hiking, zip-lining. Very vocal about preferences.", "player_type": "INDIVIDUAL",
             "positions": [{"position": 85, "capability": 35, "salience": 90, "flexibility": 40, "risk_profile": "RISK_ACCEPTANT"}]},
            {"name": "Young Son (10)", "description": "Wants to go wherever there's a pool and fun activities. Flexible but easily influenced by his sister.", "player_type": "INDIVIDUAL",
             "positions": [{"position": 60, "capability": 15, "salience": 75, "flexibility": 80, "risk_profile": "RISK_NEUTRAL"}]},
        ],
    },
    # ── BEGINNER 2 ──
    {
        "title": "Negotiating a Used Car Price",
        "description": "A buyer is negotiating the price of a 3-year-old sedan at a dealership. The model captures the buyer, seller, the KBB fair market value as an anchor, and a competing online listing.",
        "difficulty": "beginner",
        "scenario_type": "NEGOTIATION",
        "issues": [
            {
                "title": "Sale Price",
                "description": "The final negotiated price for the used vehicle.",
                "scale_min_label": "Wholesale value ($15,000)",
                "scale_max_label": "Full asking price ($22,000)",
                "status_quo_position": 80,
            },
        ],
        "players": [
            {"name": "Buyer", "description": "Pre-approved for financing, has done research, can walk away. Wants the best deal.", "player_type": "INDIVIDUAL",
             "positions": [{"position": 25, "capability": 50, "salience": 85, "flexibility": 60, "risk_profile": "RISK_NEUTRAL"}]},
            {"name": "Dealer Sales Rep", "description": "Commission-driven. Wants to close the deal today at the highest margin possible.", "player_type": "INDIVIDUAL",
             "positions": [{"position": 80, "capability": 55, "salience": 75, "flexibility": 50, "risk_profile": "RISK_AVERSE"}]},
            {"name": "Dealer Manager", "description": "Approves final pricing. Protects margins but has flexibility for aged inventory.", "player_type": "INDIVIDUAL",
             "positions": [{"position": 70, "capability": 75, "salience": 55, "flexibility": 40, "risk_profile": "RISK_NEUTRAL"}]},
            {"name": "KBB Fair Market Value", "description": "Online pricing benchmark. Sets expectations for both parties. Not a negotiator but an influential anchor.", "player_type": "INSTITUTION",
             "positions": [{"position": 45, "capability": 30, "salience": 20, "flexibility": 5, "risk_profile": "RISK_NEUTRAL"}]},
            {"name": "Competing Online Listing", "description": "A similar car listed on Carvana for $18,500. Gives the buyer walk-away leverage.", "player_type": "ORGANIZATION",
             "positions": [{"position": 35, "capability": 35, "salience": 30, "flexibility": 10, "risk_profile": "RISK_NEUTRAL"}]},
        ],
    },
    # ── MEDIUM 1 ──
    {
        "title": "Office Relocation Decision",
        "description": "A 200-person tech company is deciding whether to move to a new downtown office, stay in the current suburban location, or go hybrid-remote. Multiple stakeholders with competing interests.",
        "difficulty": "medium",
        "scenario_type": "CORPORATE",
        "issues": [
            {
                "title": "Office Location Strategy",
                "description": "The spectrum from fully remote to a premium downtown office.",
                "scale_min_label": "Fully remote (no office)",
                "scale_max_label": "Premium downtown office",
                "status_quo_position": 35,
            },
        ],
        "players": [
            {"name": "CEO", "description": "Believes in-person culture drives innovation. Wants a flagship downtown office to attract talent and impress clients.", "player_type": "INDIVIDUAL",
             "positions": [{"position": 85, "capability": 80, "salience": 75, "flexibility": 35, "risk_profile": "RISK_ACCEPTANT"}]},
            {"name": "CFO", "description": "Focused on cost. Remote saves $2M/year. Downtown adds $1.5M. Prefers a modest hybrid approach.", "player_type": "INDIVIDUAL",
             "positions": [{"position": 30, "capability": 70, "salience": 80, "flexibility": 45, "risk_profile": "RISK_AVERSE"}]},
            {"name": "VP Engineering", "description": "Engineers overwhelmingly prefer remote. Losing talent to remote-first competitors. High attrition risk.", "player_type": "INDIVIDUAL",
             "positions": [{"position": 10, "capability": 60, "salience": 90, "flexibility": 30, "risk_profile": "RISK_NEUTRAL"}]},
            {"name": "VP Sales", "description": "Needs a professional client-facing space. Doesn't care about daily attendance but wants impressive meeting rooms.", "player_type": "INDIVIDUAL",
             "positions": [{"position": 65, "capability": 50, "salience": 60, "flexibility": 70, "risk_profile": "RISK_NEUTRAL"}]},
            {"name": "HR Director", "description": "Concerned about culture and equity. Wants a policy that's fair to both remote and in-office employees.", "player_type": "INDIVIDUAL",
             "positions": [{"position": 45, "capability": 40, "salience": 85, "flexibility": 60, "risk_profile": "RISK_AVERSE"}]},
            {"name": "Employee Council", "description": "Represents the workforce. 70% prefer remote/hybrid. Will push back hard on mandatory in-office.", "player_type": "COALITION_BLOC",
             "positions": [{"position": 20, "capability": 45, "salience": 95, "flexibility": 40, "risk_profile": "RISK_NEUTRAL"}]},
        ],
    },
    # ── MEDIUM 2 ──
    {
        "title": "Restaurant Franchise Expansion",
        "description": "A successful single-location restaurant owner is deciding whether to expand. The franchise company, the bank, the landlord of the new location, and the existing staff all have stakes in the outcome.",
        "difficulty": "medium",
        "scenario_type": "MARKET",
        "issues": [
            {
                "title": "Expansion Scope",
                "description": "How aggressively to expand — from staying single-location to opening multiple new franchises.",
                "scale_min_label": "Stay single location (no expansion)",
                "scale_max_label": "Open 3 new franchise locations",
                "status_quo_position": 10,
            },
        ],
        "players": [
            {"name": "Restaurant Owner", "description": "Excited about growth but worried about overextending. Wants 1 new location to start.", "player_type": "INDIVIDUAL",
             "positions": [{"position": 40, "capability": 70, "salience": 95, "flexibility": 50, "risk_profile": "RISK_NEUTRAL"}]},
            {"name": "Franchise Company", "description": "Wants rapid expansion. More locations = more franchise fees. Pushing for 3 locations.", "player_type": "ORGANIZATION",
             "positions": [{"position": 90, "capability": 60, "salience": 70, "flexibility": 25, "risk_profile": "RISK_ACCEPTANT"}]},
            {"name": "Bank (Lender)", "description": "Will finance expansion but conservative on risk. Prefers 1 location with proven financials before more.", "player_type": "INSTITUTION",
             "positions": [{"position": 35, "capability": 75, "salience": 60, "flexibility": 30, "risk_profile": "RISK_AVERSE"}]},
            {"name": "Spouse/Business Partner", "description": "Concerned about family time and financial risk. Supportive but cautious.", "player_type": "INDIVIDUAL",
             "positions": [{"position": 20, "capability": 50, "salience": 90, "flexibility": 45, "risk_profile": "RISK_AVERSE"}]},
            {"name": "General Manager (Current Location)", "description": "Would run the new location. Excited about the opportunity but nervous about the workload.", "player_type": "INDIVIDUAL",
             "positions": [{"position": 55, "capability": 30, "salience": 80, "flexibility": 65, "risk_profile": "RISK_NEUTRAL"}]},
        ],
    },
    # ── COMPLEX 1 ──
    {
        "title": "EU Carbon Tax Policy Negotiation",
        "description": "The European Union is negotiating a new carbon border adjustment mechanism (CBAM). Multiple countries, industry groups, and environmental organizations are trying to shape the final policy.",
        "difficulty": "complex",
        "scenario_type": "GEOPOLITICAL",
        "issues": [
            {
                "title": "Carbon Tax Rate",
                "description": "The carbon price per ton of CO2 embedded in imported goods.",
                "scale_min_label": "No carbon tax (industry wins)",
                "scale_max_label": "€150/ton aggressive tax (climate wins)",
                "status_quo_position": 25,
            },
        ],
        "players": [
            {"name": "European Commission", "description": "Proposing the policy. Wants a meaningful but politically viable carbon price around €75-90/ton.", "player_type": "INSTITUTION",
             "positions": [{"position": 55, "capability": 80, "salience": 85, "flexibility": 40, "risk_profile": "RISK_NEUTRAL"}]},
            {"name": "Germany", "description": "Largest economy. Export-heavy industry worried about competitiveness. Wants moderate policy with exemptions.", "player_type": "GOVERNMENT",
             "positions": [{"position": 40, "capability": 75, "salience": 80, "flexibility": 45, "risk_profile": "RISK_AVERSE"}]},
            {"name": "France", "description": "Pro-climate policy. Nuclear energy gives them competitive advantage. Pushing for aggressive pricing.", "player_type": "GOVERNMENT",
             "positions": [{"position": 75, "capability": 65, "salience": 75, "flexibility": 35, "risk_profile": "RISK_NEUTRAL"}]},
            {"name": "Poland", "description": "Coal-dependent economy. Strongly opposes high carbon pricing. Will block if too aggressive.", "player_type": "GOVERNMENT",
             "positions": [{"position": 10, "capability": 45, "salience": 95, "flexibility": 20, "risk_profile": "RISK_AVERSE"}]},
            {"name": "European Steel Industry", "description": "Major lobby group. Fears competitive disadvantage against non-EU producers. Wants low rates or full exemptions.", "player_type": "COALITION_BLOC",
             "positions": [{"position": 15, "capability": 50, "salience": 90, "flexibility": 25, "risk_profile": "RISK_AVERSE"}]},
            {"name": "Environmental NGOs", "description": "Greenpeace, WWF, etc. Pushing for the highest possible carbon price. Significant public influence.", "player_type": "COALITION_BLOC",
             "positions": [{"position": 90, "capability": 35, "salience": 95, "flexibility": 15, "risk_profile": "RISK_ACCEPTANT"}]},
            {"name": "China (Trade Partner)", "description": "Opposes unilateral carbon tariffs. Threatens WTO challenge and retaliatory measures.", "player_type": "GOVERNMENT",
             "positions": [{"position": 5, "capability": 55, "salience": 65, "flexibility": 15, "risk_profile": "RISK_NEUTRAL"}]},
            {"name": "Nordic Countries Bloc", "description": "Sweden, Denmark, Finland. Already have high domestic carbon prices. Want EU-wide alignment.", "player_type": "COALITION_BLOC",
             "positions": [{"position": 80, "capability": 30, "salience": 70, "flexibility": 40, "risk_profile": "RISK_NEUTRAL"}]},
        ],
    },
    # ── COMPLEX 2 ──
    {
        "title": "Hospital Merger & Acquisition",
        "description": "A large healthcare system is acquiring a community hospital. The negotiation involves price, staff retention guarantees, service preservation, and community oversight — with regulators, unions, and community groups all weighing in.",
        "difficulty": "complex",
        "scenario_type": "CORPORATE",
        "issues": [
            {
                "title": "Acquisition Terms",
                "description": "The overall deal terms from most favorable to the acquirer to most favorable to the community/staff.",
                "scale_min_label": "Pure financial acquisition (cost-cutting, restructuring)",
                "scale_max_label": "Community-first deal (full protections, premium price)",
                "status_quo_position": 30,
            },
        ],
        "players": [
            {"name": "Acquiring Health System CEO", "description": "Wants efficient acquisition. Focused on synergies and eliminating redundancy. Some community commitments for PR.", "player_type": "INDIVIDUAL",
             "positions": [{"position": 25, "capability": 80, "salience": 75, "flexibility": 40, "risk_profile": "RISK_NEUTRAL"}]},
            {"name": "Community Hospital Board", "description": "Fiduciary duty to get best deal for the hospital. Wants premium price AND community protections.", "player_type": "ORGANIZATION",
             "positions": [{"position": 75, "capability": 65, "salience": 90, "flexibility": 35, "risk_profile": "RISK_AVERSE"}]},
            {"name": "Nurses Union", "description": "Protecting jobs, wages, and working conditions. Will campaign publicly against a bad deal.", "player_type": "COALITION_BLOC",
             "positions": [{"position": 85, "capability": 45, "salience": 95, "flexibility": 20, "risk_profile": "RISK_AVERSE"}]},
            {"name": "State Attorney General", "description": "Must approve hospital mergers. Focused on healthcare access and anti-competitive concerns.", "player_type": "GOVERNMENT",
             "positions": [{"position": 65, "capability": 70, "salience": 60, "flexibility": 30, "risk_profile": "RISK_AVERSE"}]},
            {"name": "Community Coalition", "description": "Local residents, patient advocates, and city council members. Want ER and maternity services preserved.", "player_type": "COALITION_BLOC",
             "positions": [{"position": 80, "capability": 30, "salience": 90, "flexibility": 30, "risk_profile": "RISK_NEUTRAL"}]},
            {"name": "Acquiring System CFO", "description": "Running the numbers. Needs the deal to hit ROI targets within 3 years. Strict on financial terms.", "player_type": "INDIVIDUAL",
             "positions": [{"position": 15, "capability": 60, "salience": 85, "flexibility": 20, "risk_profile": "RISK_AVERSE"}]},
            {"name": "Medical Staff Leadership", "description": "Physicians concerned about autonomy, referral patterns, and EMR changes. Moderate influence.", "player_type": "COALITION_BLOC",
             "positions": [{"position": 55, "capability": 40, "salience": 70, "flexibility": 50, "risk_profile": "RISK_NEUTRAL"}]},
        ],
    },
]


class Command(BaseCommand):
    help = "Seed case study scenarios with full data and run simulations (idempotent)"

    def handle(self, *args, **options):
        # Use first superuser as owner
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            self.stderr.write("No superuser found. Create one first.")
            return

        status_parent = LookupValue.objects.get(parent__isnull=True, code="SCENARIO_STATUS")
        completed_status = LookupValue.objects.get(parent=status_parent, code="COMPLETED")
        type_parent = LookupValue.objects.get(parent__isnull=True, code="SCENARIO_TYPE")
        player_type_parent = LookupValue.objects.get(parent__isnull=True, code="PLAYER_TYPE")
        risk_parent = LookupValue.objects.get(parent__isnull=True, code="RISK_PROFILE")

        for cs in CASE_STUDIES:
            # Idempotent: skip if already exists
            if Scenario.objects.filter(title=cs["title"]).exists():
                self.stdout.write(f"  [exists] {cs['title']}")
                continue

            scenario_type = LookupValue.objects.get(parent=type_parent, code=cs["scenario_type"])

            scenario = Scenario.objects.create(
                title=cs["title"],
                description=cs["description"],
                scenario_type=scenario_type,
                status=completed_status,
                owner=user,
                is_public=True,
                created_by=user,
                updated_by=user,
            )
            # Store difficulty in metadata-like version_label
            scenario.version_label = cs["difficulty"]
            scenario.save(update_fields=["version_label"])

            # Create issues
            issue_objects = []
            for i, issue_data in enumerate(cs["issues"]):
                issue = ScenarioIssue.objects.create(
                    scenario=scenario,
                    title=issue_data["title"],
                    description=issue_data.get("description", ""),
                    scale_min_label=issue_data["scale_min_label"],
                    scale_max_label=issue_data["scale_max_label"],
                    status_quo_position=issue_data["status_quo_position"],
                    sort_order=i,
                )
                issue_objects.append(issue)

            # Create players and positions
            for player_data in cs["players"]:
                pt_lv = LookupValue.objects.get(parent=player_type_parent, code=player_data["player_type"])
                player = Player.objects.create(
                    scenario=scenario,
                    name=player_data["name"],
                    description=player_data["description"],
                    player_type=pt_lv,
                )
                for j, pos_data in enumerate(player_data["positions"]):
                    rp_lv = LookupValue.objects.get(parent=risk_parent, code=pos_data["risk_profile"])
                    PlayerPosition.objects.create(
                        player=player,
                        issue=issue_objects[j],
                        position=Decimal(str(pos_data["position"])),
                        capability=Decimal(str(pos_data["capability"])),
                        salience=Decimal(str(pos_data["salience"])),
                        flexibility=Decimal(str(pos_data["flexibility"])),
                        risk_profile=rp_lv,
                    )

            # Run simulation
            try:
                sim_run = run_simulation(scenario, user)
                self.stdout.write(self.style.SUCCESS(
                    f"  [+] {cs['title']} — outcome={sim_run.predicted_outcome}, "
                    f"confidence={sim_run.confidence_score}, rounds={sim_run.total_rounds_executed}"
                ))
            except Exception as e:
                self.stderr.write(f"  [!] {cs['title']} — simulation failed: {e}")

        self.stdout.write(self.style.SUCCESS("Case study seed complete."))
