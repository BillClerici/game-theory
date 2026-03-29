"""
Conversational AI service using LangGraph + Claude for:
1. Guided scenario creation with web research
2. Post-simulation analysis and outcome engineering advice
3. Conversational scenario modification (update players, issues, positions)

Uses LangGraph for multi-step orchestration and Tavily for web search.
"""
from __future__ import annotations

import json
import logging
import os
from decimal import Decimal
from typing import Any, Annotated

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from apps.conversations.models import ConversationMessage, ConversationSession
from apps.lookup.models import LookupValue
from apps.scenarios.models import Player, PlayerPosition, Scenario, ScenarioIssue

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-20250514"


# ── System Prompts ──

SCENARIO_BUILDER_PROMPT = """You are an expert game theory analyst specializing in Bruce Bueno de Mesquita's (BDM) expected utility model. You are guiding a user through creating a prediction scenario.

Your job is to have a natural conversation to gather all the information needed to build a complete BDM scenario. You must extract:

1. **The Scenario**: A title, description, and type (geopolitical, corporate, legislative, legal, market, negotiation, personal, or custom).

2. **Issues**: What decision(s) or outcome(s) are at stake. For each issue you need:
   - A clear title
   - Scale endpoints: what does 0 mean? What does 100 mean?
   - The status quo position (where things stand today, 0-100)

3. **Players/Stakeholders**: Who can influence the outcome. For each player:
   - Name, description, type (individual, organization, government, coalition_bloc, institution, other)
   - For each issue: position (0-100), capability (0-100), salience (0-100), flexibility (0-100)
   - Risk profile: risk_averse, risk_neutral, or risk_acceptant

## Conversation Flow

**Phase 1 - Understand**: Ask the user to describe their situation. Ask clarifying questions. Use web_search if you need current data about real-world entities, market conditions, or public figures involved.

**Phase 2 - Identify Players**: Ask who the key players are. For each, extract parameters conversationally. Suggest players they may not have considered. Use web_search to research players and get better parameter estimates when dealing with public figures, companies, or governments.

**Phase 3 - Validate**: Present a complete summary table. Flag inconsistencies. Ask for confirmation.

**Phase 4 - Create**: When confirmed, call create_scenario with all the data.

## Guidelines
- Be conversational, not robotic. Don't dump all questions at once.
- Help uncertain users with examples and benchmarks.
- Challenge vague answers — "very powerful" should become a number.
- Use web_search proactively when the scenario involves real-world entities.
- ALWAYS extract at least 3 players (BDM minimum).
- Present a summary and get confirmation before calling create_scenario."""


SIMULATION_ANALYST_PROMPT = """You are an expert game theory analyst. You have just received the results of a BDM expected utility simulation. Your job is to:

1. **Explain the results** in plain language — what does the predicted outcome mean in the context of this specific scenario?

2. **Analyze the strategic dynamics** — why did players move the way they did? Who formed natural coalitions? What drove convergence or deadlock?

3. **Identify leverage points** — which players are most influential? Where are the swing points?

4. **Recommend outcome engineering strategies** — give the user 3-5 specific, actionable recommendations for how to shift the outcome in their favor. For each:
   - What to do (target player, approach)
   - Expected impact on the outcome
   - Difficulty/feasibility
   - Potential counter-moves

5. **Use web_search** if the scenario involves real-world entities — research current events, relationships, or leverage points that could inform strategy.

Be specific and grounded in the model outputs. Reference actual numbers from the simulation. Frame advice as actionable moves, not generic platitudes."""


# ── Tools ──

@tool
def web_search(query: str) -> str:
    """Search the web for current information about entities, market conditions, or events relevant to the scenario."""
    try:
        from tavily import TavilyClient
        api_key = os.environ.get("TAVILY_API_KEY", "")
        if not api_key:
            return "Web search unavailable (no API key configured)."
        client = TavilyClient(api_key=api_key)
        result = client.search(query=query, max_results=5, search_depth="basic")
        summaries = []
        for r in result.get("results", []):
            summaries.append(f"**{r.get('title', '')}**: {r.get('content', '')[:300]}")
        return "\n\n".join(summaries) if summaries else "No results found."
    except Exception as e:
        logger.warning(f"Web search failed: {e}")
        return f"Web search failed: {e}"


@tool
def create_scenario(
    title: str,
    description: str,
    scenario_type: str,
    issues: list[dict],
    players: list[dict],
) -> str:
    """Create a complete BDM scenario with all issues, players, and positions.
    Call this only after the user has confirmed all the data.

    Args:
        title: Short descriptive title for the scenario
        description: Detailed description of the scenario context
        scenario_type: One of: geopolitical, corporate, legislative, legal, market, negotiation, personal, custom
        issues: List of issues, each with: title, description, scale_min_label, scale_max_label, status_quo_position (0-100)
        players: List of players, each with: name, description, player_type (individual/organization/government/coalition_bloc/institution/other), positions (list of: issue_index, position, capability, salience, flexibility, risk_profile)
    """
    # This is a placeholder — actual creation happens in _handle_create_scenario
    return json.dumps({
        "title": title,
        "description": description,
        "scenario_type": scenario_type,
        "issues": issues,
        "players": players,
    })


BUILDER_TOOLS = [web_search, create_scenario]
ANALYST_TOOLS = [web_search]


# ── LangGraph State ──

class ConversationState(TypedDict):
    messages: Annotated[list, add_messages]
    session_id: str
    user_id: str
    scenario_created: bool
    scenario_id: str


# ── Graph Nodes ──

def _get_llm() -> ChatAnthropic:
    return ChatAnthropic(
        model=MODEL,
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        max_tokens=4096,
    )


def scenario_builder_node(state: ConversationState) -> dict:
    """Main conversational node for scenario building."""
    llm = _get_llm().bind_tools(BUILDER_TOOLS)
    system = SystemMessage(content=SCENARIO_BUILDER_PROMPT)
    messages = [system] + state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}


def analyst_node(state: ConversationState) -> dict:
    """Post-simulation analysis node."""
    llm = _get_llm().bind_tools(ANALYST_TOOLS)
    system = SystemMessage(content=SIMULATION_ANALYST_PROMPT)
    messages = [system] + state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}


def tool_handler_node(state: ConversationState) -> dict:
    """Handle tool calls — web search runs directly, create_scenario builds the real objects."""
    messages = state["messages"]
    last = messages[-1]

    results = []
    scenario_created = state.get("scenario_created", False)
    scenario_id = state.get("scenario_id", "")

    if isinstance(last, AIMessage) and last.tool_calls:
        for tc in last.tool_calls:
            if tc["name"] == "web_search":
                result = web_search.invoke(tc["args"])
                results.append(ToolMessage(content=result, tool_call_id=tc["id"]))
            elif tc["name"] == "create_scenario":
                try:
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    user = User.objects.get(pk=state["user_id"])
                    scenario = _create_scenario_from_data(tc["args"], user)

                    # Link to session
                    session = ConversationSession.objects.get(pk=state["session_id"])
                    session.scenario = scenario
                    session.extracted_scenario_data = tc["args"]
                    session.save(update_fields=["scenario", "extracted_scenario_data", "updated_at"])

                    scenario_created = True
                    scenario_id = str(scenario.pk)
                    result_msg = (
                        f"Scenario '{scenario.title}' created successfully with "
                        f"{scenario.players.count()} players and "
                        f"{scenario.issues.count()} issue(s). "
                        f"Scenario ID: {scenario_id}"
                    )
                    results.append(ToolMessage(content=result_msg, tool_call_id=tc["id"]))
                except Exception as e:
                    logger.exception("Failed to create scenario")
                    results.append(ToolMessage(
                        content=f"Error creating scenario: {e}",
                        tool_call_id=tc["id"],
                    ))

    return {
        "messages": results,
        "scenario_created": scenario_created,
        "scenario_id": scenario_id,
    }


def _should_use_tools(state: ConversationState) -> str:
    """Route: if last message has tool calls, go to tool handler. Otherwise end."""
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        return "tools"
    return END


# ── Build Graphs ──

def _build_builder_graph() -> StateGraph:
    graph = StateGraph(ConversationState)
    graph.add_node("builder", scenario_builder_node)
    graph.add_node("tools", tool_handler_node)
    graph.add_edge(START, "builder")
    graph.add_conditional_edges("builder", _should_use_tools, {"tools": "tools", END: END})
    graph.add_edge("tools", "builder")  # after tool execution, go back to LLM
    return graph.compile()


def _build_analyst_graph() -> StateGraph:
    graph = StateGraph(ConversationState)
    graph.add_node("analyst", analyst_node)
    graph.add_node("tools", tool_handler_node)
    graph.add_edge(START, "analyst")
    graph.add_conditional_edges("analyst", _should_use_tools, {"tools": "tools", END: END})
    graph.add_edge("tools", "analyst")
    return graph.compile()


# Cache compiled graphs
_builder_graph = None
_analyst_graph = None


def _get_builder_graph():
    global _builder_graph
    if _builder_graph is None:
        _builder_graph = _build_builder_graph()
    return _builder_graph


def _get_analyst_graph():
    global _analyst_graph
    if _analyst_graph is None:
        _analyst_graph = _build_analyst_graph()
    return _analyst_graph


# ── Scenario Creation Helper ──

def _create_scenario_from_data(data: dict[str, Any], user: Any) -> Scenario:
    """Create a complete scenario from structured data."""
    type_parent = LookupValue.objects.get(parent__isnull=True, code="SCENARIO_TYPE")
    type_code = data["scenario_type"].upper()
    scenario_type = LookupValue.objects.get(parent=type_parent, code=type_code)

    status_parent = LookupValue.objects.get(parent__isnull=True, code="SCENARIO_STATUS")
    draft_status = LookupValue.objects.get(parent=status_parent, code="DRAFT")

    player_type_parent = LookupValue.objects.get(parent__isnull=True, code="PLAYER_TYPE")
    risk_parent = LookupValue.objects.get(parent__isnull=True, code="RISK_PROFILE")

    scenario = Scenario.objects.create(
        title=data["title"],
        description=data.get("description", ""),
        scenario_type=scenario_type,
        status=draft_status,
        owner=user,
        created_by=user,
        updated_by=user,
    )

    issue_objects = []
    for i, issue_data in enumerate(data.get("issues", [])):
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

    for player_data in data.get("players", []):
        pt_code = player_data["player_type"].upper()
        player_type_lv = LookupValue.objects.get(parent=player_type_parent, code=pt_code)

        player = Player.objects.create(
            scenario=scenario,
            name=player_data["name"],
            description=player_data.get("description", ""),
            player_type=player_type_lv,
        )

        for pos_data in player_data.get("positions", []):
            issue_idx = pos_data.get("issue_index", 0)
            if issue_idx < len(issue_objects):
                rp_code = pos_data.get("risk_profile", "risk_neutral").upper()
                risk_lv = LookupValue.objects.get(parent=risk_parent, code=rp_code)

                PlayerPosition.objects.create(
                    player=player,
                    issue=issue_objects[issue_idx],
                    position=Decimal(str(pos_data["position"])),
                    capability=Decimal(str(pos_data["capability"])),
                    salience=Decimal(str(pos_data["salience"])),
                    flexibility=Decimal(str(pos_data["flexibility"])),
                    risk_profile=risk_lv,
                )

    return scenario


# ── Public API ──

def start_session(user: Any) -> ConversationSession:
    """Start a new scenario builder conversation session."""
    session_type_parent = LookupValue.objects.get(
        parent__isnull=True, code="CONVERSATION_SESSION_TYPE",
    )
    session_type = LookupValue.objects.get(
        parent=session_type_parent, code="SCENARIO_BUILDER",
    )
    status_parent = LookupValue.objects.get(
        parent__isnull=True, code="CONVERSATION_STATUS",
    )
    active_status = LookupValue.objects.get(parent=status_parent, code="ACTIVE")

    session = ConversationSession.objects.create(
        user=user,
        session_type=session_type,
        status=active_status,
    )

    greeting = (
        "Hi! I'm your game theory analyst. I'll help you build a prediction scenario "
        "using the BDM expected utility model.\n\n"
        "**Tell me about the situation you're trying to predict.** What decision or "
        "negotiation are you facing? What outcome are you trying to influence?\n\n"
        "Just describe it naturally — I'll help structure it into a formal model. "
        "If it involves real-world entities, I can also research current information "
        "to help set accurate parameters."
    )
    ConversationMessage.objects.create(
        session=session,
        role="assistant",
        content=greeting,
        message_order=0,
        token_count=0,
    )

    return session


def send_message(
    session: ConversationSession,
    user_message: str,
) -> dict[str, Any]:
    """Send a user message through the LangGraph builder flow."""
    # Save user message
    next_order = session.messages.count()
    ConversationMessage.objects.create(
        session=session,
        role="user",
        content=user_message,
        message_order=next_order,
    )

    # Rebuild message history for LangGraph
    history = []
    for m in session.messages.filter(role__in=["user", "assistant"]).order_by("message_order"):
        if m.role == "user":
            history.append(HumanMessage(content=m.content))
        elif m.role == "assistant":
            history.append(AIMessage(content=m.content))

    # Run the graph
    graph = _get_builder_graph()
    initial_state: ConversationState = {
        "messages": history,
        "session_id": str(session.pk),
        "user_id": str(session.user_id),
        "scenario_created": False,
        "scenario_id": "",
    }

    result = graph.invoke(initial_state)

    # Extract the final assistant message
    assistant_text = ""
    structured_data = None
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage):
            assistant_text = msg.content if isinstance(msg.content, str) else str(msg.content)
            break

    scenario_created = result.get("scenario_created", False)
    scenario_id = result.get("scenario_id", "")

    # Save assistant response
    ConversationMessage.objects.create(
        session=session,
        role="assistant",
        content=assistant_text,
        structured_data=structured_data,
        message_order=next_order + 1,
        token_count=0,
    )

    # Mark completed if scenario was created
    if scenario_created:
        completed_parent = LookupValue.objects.get(parent__isnull=True, code="CONVERSATION_STATUS")
        completed_status = LookupValue.objects.get(parent=completed_parent, code="COMPLETED")
        session.status = completed_status
        session.save(update_fields=["status", "updated_at"])

    return {
        "assistant_message": assistant_text,
        "scenario_created": scenario_created,
        "scenario_id": scenario_id,
    }


def analyze_simulation(
    scenario: Scenario,
    user: Any,
    force_refresh: bool = False,
    optimize_for_player_id: str | None = None,
) -> str:
    """Run LLM analysis on simulation results. Returns analysis text.
    Caches general analysis on SimulationRun.analysis_report.
    Player-specific analyses are always generated fresh (not cached).
    """
    from apps.engine.models import SimulationRun

    latest_sim = SimulationRun.objects.filter(
        scenario=scenario,
    ).select_related("status").first()

    if not latest_sim:
        return "No simulation results available. Run a simulation first."

    # Return cached analysis if available (only for general, non-player-specific analysis)
    if latest_sim.analysis_report and not force_refresh and not optimize_for_player_id:
        return latest_sim.analysis_report

    # Build context about the scenario and results
    issues = list(scenario.issues.filter(is_active=True))
    players = list(scenario.players.filter(is_active=True).select_related("player_type"))

    # Gather position data
    position_data = []
    for player in players:
        for issue in issues:
            pp = PlayerPosition.objects.filter(
                player=player, issue=issue, is_active=True,
            ).select_related("risk_profile").first()
            if pp:
                position_data.append(
                    f"  {player.name} on '{issue.title}': "
                    f"position={pp.position}, capability={pp.capability}, "
                    f"salience={pp.salience}, flexibility={pp.flexibility}, "
                    f"risk={pp.risk_profile.label}"
                )

    # Gather simulation results
    outcomes = list(
        latest_sim.prediction_outcomes.all().select_related("issue", "outcome_stability")
    )
    outcome_text = []
    for o in outcomes:
        outcome_text.append(
            f"  Issue '{o.issue.title}': predicted={o.predicted_position}, "
            f"confidence={o.confidence_score}, median={o.weighted_median}, "
            f"mean={o.weighted_mean}, coalition_cap={o.winning_coalition_capability}%, "
            f"stability={o.outcome_stability.label}"
        )

    # Gather round-by-round summary
    rounds = list(
        latest_sim.round_results.all()
        .select_related("player", "issue")
        .order_by("round_number", "player__name")
    )
    round_summary = {}
    for r in rounds:
        key = f"Round {r.round_number}"
        if key not in round_summary:
            round_summary[key] = []
        round_summary[key].append(
            f"  {r.player.name}: {r.position_start} → {r.position_end} "
            f"(pressure={r.pressure_received}, challenges_in={r.challenges_received})"
        )

    round_text = ""
    for rnd, entries in round_summary.items():
        round_text += f"\n{rnd}:\n" + "\n".join(entries)

    context_message = f"""Analyze these BDM simulation results:

**Scenario**: {scenario.title}
**Description**: {scenario.description}

**Issues**:
{chr(10).join(f"  - {i.title}: {i.scale_min_label} (0) to {i.scale_max_label} (100), status quo={i.status_quo_position}" for i in issues)}

**Players & Positions**:
{chr(10).join(position_data)}

**Simulation Results**:
- Rounds executed: {latest_sim.total_rounds_executed}
- Converged: {latest_sim.converged}
- Deadlock: {latest_sim.deadlock_detected}
- Execution time: {latest_sim.execution_time_ms}ms

**Predicted Outcomes**:
{chr(10).join(outcome_text)}

**Round-by-Round Movement**:
{round_text}

"""

    # Add player-specific optimization instructions
    if optimize_for_player_id:
        opt_player = Player.objects.filter(pk=optimize_for_player_id, scenario=scenario).first()
        if opt_player:
            opt_positions = PlayerPosition.objects.filter(
                player=opt_player, is_active=True,
            ).select_related("issue", "risk_profile")
            opt_detail = "\n".join(
                f"  Issue '{pp.issue.title}': their ideal position={pp.position}, "
                f"capability={pp.capability}, salience={pp.salience}, "
                f"flexibility={pp.flexibility}, risk={pp.risk_profile.label}"
                for pp in opt_positions
            )
            context_message += f"""

**OPTIMIZE FOR: {opt_player.name}**
You are now acting as a strategic advisor specifically for **{opt_player.name}** ({opt_player.description}).

Their current parameters:
{opt_detail}

Please provide your analysis entirely from {opt_player.name}'s perspective:

1. **Gap Analysis**: How far is the predicted outcome from {opt_player.name}'s ideal position on each issue? Quantify the gap.

2. **Power Assessment**: How does {opt_player.name}'s capability × salience compare to other players? Where do they rank in effective influence? Are they punching above or below their weight?

3. **Coalition Map**: Which other players have positions closest to {opt_player.name}'s ideal? Who are natural allies? Who are the main opponents?

4. **5 Specific Strategic Moves**: For each recommendation:
   - What exactly should {opt_player.name} do? (target a specific player, build an alliance, increase leverage, etc.)
   - What parameter would this change? (e.g., "increase your capability from X to Y by doing Z")
   - Estimated impact: how much would the predicted outcome shift toward {opt_player.name}'s ideal?
   - Difficulty/feasibility rating (1-5)
   - Potential counter-moves from opponents

5. **What-If Scenarios**: Suggest 2-3 specific parameter changes {opt_player.name} could test using the What-If branch feature. Be precise: "Change your capability from X to Y and Player Z's salience from A to B."

6. **Risk Assessment**: What's the biggest risk to {opt_player.name}'s position? What could opponents do to undermine their strategy?

7. Use web_search if this involves real-world entities — look for current leverage opportunities, relationships, or events that {opt_player.name} could exploit."""
        else:
            context_message += """

Please provide:
1. A clear explanation of what the predicted outcome means in context
2. Analysis of the strategic dynamics — why players moved as they did
3. Identification of the key leverage points and swing players
4. 3-5 specific, actionable recommendations for engineering a better outcome
5. Use web_search if this involves real-world entities"""
    else:
        context_message += """

Please provide:
1. A clear explanation of what the predicted outcome means in context
2. Analysis of the strategic dynamics — why players moved as they did
3. Identification of the key leverage points and swing players
4. 3-5 specific, actionable recommendations for engineering a better outcome for the scenario owner
5. Use web_search if this involves real-world entities that you can research for current leverage opportunities"""

    # Run through analyst graph
    graph = _get_analyst_graph()
    initial_state: ConversationState = {
        "messages": [HumanMessage(content=context_message)],
        "session_id": "",
        "user_id": str(user.pk),
        "scenario_created": False,
        "scenario_id": str(scenario.pk),
    }

    result = graph.invoke(initial_state)

    # Extract analysis and save to SimulationRun
    analysis_text = "Analysis could not be generated."
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage):
            analysis_text = msg.content if isinstance(msg.content, str) else str(msg.content)
            break

    # Only cache general analysis, not player-specific ones
    if not optimize_for_player_id:
        latest_sim.analysis_report = analysis_text
        latest_sim.save(update_fields=["analysis_report", "updated_at"])

    return analysis_text


# ── Scenario Modifier ──

SCENARIO_MODIFIER_PROMPT = """You are an expert game theory analyst. You are helping the user modify an existing BDM scenario through conversation.

You have access to the current scenario data (provided below). The user can ask you to:
- Add, remove, or modify players
- Change player parameters (position, capability, salience, flexibility, risk profile)
- Add or modify issues
- Change issue scale labels or status quo
- Get explanations about what parameters mean
- Get suggestions for better parameter values

When the user asks for a change, use the modify_scenario tool to make it. Always confirm what you changed.

Use web_search when the user asks about real-world entities to help calibrate parameters.

Be conversational and helpful. When making changes, explain the strategic implications (e.g., "Increasing their capability from 40 to 60 means they now have significantly more influence — this will likely shift the predicted outcome toward their preferred position").

CRITICAL: When adding a new player, you MUST include their positions array with position, capability, salience, flexibility, and risk_profile values for every issue in the scenario. A player without positions is useless — they cannot participate in simulations. If you don't have values, use reasonable defaults and tell the user what you chose."""


@tool
def modify_scenario(
    modifications: list[dict],
) -> str:
    """Apply modifications to the current scenario. The scenario is already known — do NOT ask the user for a scenario ID.

    Args:
        modifications: List of modification objects. Each has a "type" field and relevant data:
            - {"type": "add_player", "name": str, "description": str, "player_type": str, "positions": [{"issue_title": str, "position": float, "capability": float, "salience": float, "flexibility": float, "risk_profile": str}]} — ALWAYS include positions when adding a player. If the scenario has one issue, you may omit issue_title.
            - {"type": "remove_player", "player_name": str}
            - {"type": "update_player_position", "player_name": str, "issue_title": str, "position": float, "capability": float, "salience": float, "flexibility": float, "risk_profile": str} — use this to change an existing player's parameters
            - {"type": "add_issue", "title": str, "description": str, "scale_min_label": str, "scale_max_label": str, "status_quo_position": int}
            - {"type": "update_issue", "issue_title": str, "scale_min_label": str, "scale_max_label": str, "status_quo_position": int}
            - {"type": "remove_issue", "issue_title": str}
            - {"type": "update_player_meta", "player_name": str, "name": str, "description": str, "player_type": str}

    IMPORTANT: When adding a player, ALWAYS include their positions array with values for each issue in the scenario. A player without positions cannot participate in simulations.
    """
    # Placeholder — actual execution in tool_handler which injects scenario_id from state
    return json.dumps({"modifications": modifications})


MODIFIER_TOOLS = [web_search, modify_scenario]


def _apply_modifications(scenario_id: str, modifications: list[dict], user: Any) -> str:
    """Apply a list of modifications to a scenario."""
    scenario = Scenario.objects.get(pk=scenario_id)
    player_type_parent = LookupValue.objects.get(parent__isnull=True, code="PLAYER_TYPE")
    risk_parent = LookupValue.objects.get(parent__isnull=True, code="RISK_PROFILE")
    results = []

    for mod in modifications:
        mod_type = mod.get("type", "")

        if mod_type == "add_player":
            pt_code = mod.get("player_type", "individual").upper()
            player_type_lv = LookupValue.objects.get(parent=player_type_parent, code=pt_code)
            player = Player.objects.create(
                scenario=scenario,
                name=mod["name"],
                description=mod.get("description", ""),
                player_type=player_type_lv,
            )
            # Auto-create positions if provided inline
            for pos_data in mod.get("positions", []):
                issue_title = pos_data.get("issue_title", "")
                issue = ScenarioIssue.objects.filter(
                    scenario=scenario, title__iexact=issue_title, is_active=True,
                ).first()
                if not issue:
                    # If only one issue, use it by default
                    issues = list(scenario.issues.filter(is_active=True))
                    issue = issues[0] if len(issues) == 1 else None
                if issue:
                    rp_code = pos_data.get("risk_profile", "risk_neutral").upper()
                    risk_lv = LookupValue.objects.get(parent=risk_parent, code=rp_code)
                    PlayerPosition.objects.create(
                        player=player,
                        issue=issue,
                        position=Decimal(str(pos_data.get("position", 50))),
                        capability=Decimal(str(pos_data.get("capability", 50))),
                        salience=Decimal(str(pos_data.get("salience", 50))),
                        flexibility=Decimal(str(pos_data.get("flexibility", 50))),
                        risk_profile=risk_lv,
                    )
            pos_count = PlayerPosition.objects.filter(player=player).count()
            results.append(f"Added player '{mod['name']}' with {pos_count} position(s)")

        elif mod_type == "remove_player":
            player = Player.objects.filter(
                scenario=scenario, name__iexact=mod["player_name"], is_active=True,
            ).first()
            if player:
                player.is_active = False
                player.save(update_fields=["is_active", "updated_at"])
                results.append(f"Removed player '{mod['player_name']}'")
            else:
                results.append(f"Player '{mod['player_name']}' not found")

        elif mod_type == "update_player_position":
            player = Player.objects.filter(
                scenario=scenario, name__iexact=mod["player_name"], is_active=True,
            ).first()
            issue = ScenarioIssue.objects.filter(
                scenario=scenario, title__iexact=mod["issue_title"], is_active=True,
            ).first()
            if player and issue:
                rp_code = mod.get("risk_profile", "risk_neutral").upper()
                risk_lv = LookupValue.objects.get(parent=risk_parent, code=rp_code)
                pp, created = PlayerPosition.objects.update_or_create(
                    player=player,
                    issue=issue,
                    defaults={
                        "position": Decimal(str(mod.get("position", 50))),
                        "capability": Decimal(str(mod.get("capability", 50))),
                        "salience": Decimal(str(mod.get("salience", 50))),
                        "flexibility": Decimal(str(mod.get("flexibility", 50))),
                        "risk_profile": risk_lv,
                    },
                )
                action = "Set" if created else "Updated"
                results.append(
                    f"{action} {player.name} on '{issue.title}': "
                    f"pos={mod.get('position')}, cap={mod.get('capability')}, "
                    f"sal={mod.get('salience')}, flex={mod.get('flexibility')}"
                )
            else:
                results.append(f"Player or issue not found for update")

        elif mod_type == "add_issue":
            from django.db.models import Max
            max_order = scenario.issues.aggregate(m=Max("sort_order"))["m"]
            next_order = (max_order + 1) if max_order is not None else 0
            issue = ScenarioIssue.objects.create(
                scenario=scenario,
                title=mod["title"],
                description=mod.get("description", ""),
                scale_min_label=mod["scale_min_label"],
                scale_max_label=mod["scale_max_label"],
                status_quo_position=mod.get("status_quo_position", 50),
                sort_order=next_order,
            )
            results.append(f"Added issue '{mod['title']}'")

        elif mod_type == "update_issue":
            issue = ScenarioIssue.objects.filter(
                scenario=scenario, title__iexact=mod["issue_title"], is_active=True,
            ).first()
            if issue:
                if "scale_min_label" in mod:
                    issue.scale_min_label = mod["scale_min_label"]
                if "scale_max_label" in mod:
                    issue.scale_max_label = mod["scale_max_label"]
                if "status_quo_position" in mod:
                    issue.status_quo_position = mod["status_quo_position"]
                issue.save()
                results.append(f"Updated issue '{mod['issue_title']}'")
            else:
                results.append(f"Issue '{mod['issue_title']}' not found")

        elif mod_type == "remove_issue":
            issue = ScenarioIssue.objects.filter(
                scenario=scenario, title__iexact=mod["issue_title"], is_active=True,
            ).first()
            if issue:
                issue.is_active = False
                issue.save(update_fields=["is_active", "updated_at"])
                results.append(f"Removed issue '{mod['issue_title']}'")
            else:
                results.append(f"Issue '{mod['issue_title']}' not found")

        elif mod_type == "update_player_meta":
            player = Player.objects.filter(
                scenario=scenario, name__iexact=mod["player_name"], is_active=True,
            ).first()
            if player:
                if "name" in mod and mod["name"]:
                    player.name = mod["name"]
                if "description" in mod:
                    player.description = mod["description"]
                if "player_type" in mod:
                    pt_code = mod["player_type"].upper()
                    player.player_type = LookupValue.objects.get(
                        parent=player_type_parent, code=pt_code,
                    )
                player.save()
                results.append(f"Updated player '{mod['player_name']}'")
            else:
                results.append(f"Player '{mod['player_name']}' not found")

    return "; ".join(results) if results else "No modifications applied."


def modifier_tool_handler_node(state: ConversationState) -> dict:
    """Handle tool calls for the scenario modifier graph."""
    messages = state["messages"]
    last = messages[-1]
    results = []

    if isinstance(last, AIMessage) and last.tool_calls:
        for tc in last.tool_calls:
            if tc["name"] == "web_search":
                result = web_search.invoke(tc["args"])
                results.append(ToolMessage(content=result, tool_call_id=tc["id"]))
            elif tc["name"] == "modify_scenario":
                try:
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    user = User.objects.get(pk=state["user_id"])
                    result = _apply_modifications(
                        state["scenario_id"],
                        tc["args"]["modifications"],
                        user,
                    )
                    results.append(ToolMessage(content=result, tool_call_id=tc["id"]))
                except Exception as e:
                    logger.exception("Failed to modify scenario")
                    results.append(ToolMessage(
                        content=f"Error: {e}",
                        tool_call_id=tc["id"],
                    ))

    return {"messages": results}


def _build_scenario_context(scenario_id: str) -> str:
    """Build a text summary of the current scenario state for the LLM."""
    try:
        scenario = Scenario.objects.get(pk=scenario_id)
    except Scenario.DoesNotExist:
        return "Scenario not found."

    issues = list(scenario.issues.filter(is_active=True).order_by("sort_order"))
    players = list(scenario.players.filter(is_active=True).select_related("player_type").order_by("name"))

    lines = [
        f"SCENARIO: {scenario.title}",
        f"DESCRIPTION: {scenario.description}",
        "",
        "ISSUES:",
    ]
    for issue in issues:
        lines.append(
            f"  - \"{issue.title}\": scale 0={issue.scale_min_label}, 100={issue.scale_max_label}, status_quo={issue.status_quo_position}"
        )

    lines.append("")
    lines.append("PLAYERS AND CURRENT POSITIONS:")
    for player in players:
        positions = PlayerPosition.objects.filter(
            player=player, is_active=True,
        ).select_related("issue", "risk_profile")
        if positions.exists():
            for pp in positions:
                lines.append(
                    f"  - \"{player.name}\" ({player.player_type.label}) on \"{pp.issue.title}\": "
                    f"position={pp.position}, capability={pp.capability}, salience={pp.salience}, "
                    f"flexibility={pp.flexibility}, risk_profile={pp.risk_profile.code.lower()}"
                )
        else:
            lines.append(
                f"  - \"{player.name}\" ({player.player_type.label}): NO POSITIONS SET"
            )

    return "\n".join(lines)


def scenario_modifier_node(state: ConversationState) -> dict:
    """Conversational node for scenario modification."""
    llm = _get_llm().bind_tools(MODIFIER_TOOLS)

    # Inject live scenario data into the system prompt
    scenario_context = _build_scenario_context(state["scenario_id"])
    prompt = (
        SCENARIO_MODIFIER_PROMPT
        + f"\n\nYou are working on scenario ID: {state['scenario_id']}. Do NOT ask the user for a scenario ID — it is already set."
        + f"\n\n--- CURRENT SCENARIO STATE ---\n{scenario_context}\n--- END SCENARIO STATE ---"
        + "\n\nIMPORTANT: When the user asks you to set or update values for players, you MUST call the modify_scenario tool with update_player_position entries for EVERY player that needs changes. Use the exact player names and issue titles shown above. The tool call is what saves the data — if you don't call it, nothing is saved."
    )
    system = SystemMessage(content=prompt)
    messages = [system] + state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}


def _build_modifier_graph():
    graph = StateGraph(ConversationState)
    graph.add_node("modifier", scenario_modifier_node)
    graph.add_node("tools", modifier_tool_handler_node)
    graph.add_edge(START, "modifier")
    graph.add_conditional_edges("modifier", _should_use_tools, {"tools": "tools", END: END})
    graph.add_edge("tools", "modifier")
    return graph.compile()


_modifier_graph = None


def _get_modifier_graph():
    global _modifier_graph
    if _modifier_graph is None:
        _modifier_graph = _build_modifier_graph()
    return _modifier_graph


def start_modifier_session(scenario: Scenario, user: Any) -> ConversationSession:
    """Start a chat session for modifying an existing scenario."""
    session_type_parent = LookupValue.objects.get(
        parent__isnull=True, code="CONVERSATION_SESSION_TYPE",
    )
    session_type = LookupValue.objects.get(parent=session_type_parent, code="GENERAL")
    status_parent = LookupValue.objects.get(parent__isnull=True, code="CONVERSATION_STATUS")
    active_status = LookupValue.objects.get(parent=status_parent, code="ACTIVE")

    session = ConversationSession.objects.create(
        user=user,
        scenario=scenario,
        session_type=session_type,
        status=active_status,
    )

    # Build scenario summary for context
    issues = scenario.issues.filter(is_active=True)
    players = scenario.players.filter(is_active=True).select_related("player_type")

    summary_parts = [f"**Scenario**: {scenario.title}", f"**Description**: {scenario.description}", "", "**Issues**:"]
    for issue in issues:
        summary_parts.append(f"- {issue.title}: {issue.scale_min_label} (0) to {issue.scale_max_label} (100), status quo={issue.status_quo_position}")

    summary_parts.append("\n**Players**:")
    for player in players:
        positions = PlayerPosition.objects.filter(player=player, is_active=True).select_related("issue", "risk_profile")
        for pp in positions:
            summary_parts.append(
                f"- **{player.name}** ({player.player_type.label}) on '{pp.issue.title}': "
                f"pos={pp.position}, cap={pp.capability}, sal={pp.salience}, "
                f"flex={pp.flexibility}, risk={pp.risk_profile.label}"
            )

    scenario_summary = "\n".join(summary_parts)

    greeting = (
        f"I'm ready to help you modify this scenario. Here's what we're working with:\n\n"
        f"{scenario_summary}\n\n"
        f"What would you like to change? You can ask me to:\n"
        f"- Add, remove, or rename players\n"
        f"- Adjust any player's parameters (position, capability, salience, flexibility, risk)\n"
        f"- Add or modify issues\n"
        f"- Get suggestions for better parameter values\n"
        f"- Research real-world information to calibrate the model"
    )

    ConversationMessage.objects.create(
        session=session,
        role="assistant",
        content=greeting,
        message_order=0,
        token_count=0,
    )

    return session


def send_modifier_message(
    session: ConversationSession,
    user_message: str,
) -> dict[str, Any]:
    """Send a message through the scenario modifier graph."""
    next_order = session.messages.count()
    ConversationMessage.objects.create(
        session=session,
        role="user",
        content=user_message,
        message_order=next_order,
    )

    # Build history
    history = []
    for m in session.messages.filter(role__in=["user", "assistant"]).order_by("message_order"):
        if m.role == "user":
            history.append(HumanMessage(content=m.content))
        elif m.role == "assistant":
            history.append(AIMessage(content=m.content))

    graph = _get_modifier_graph()
    initial_state: ConversationState = {
        "messages": history,
        "session_id": str(session.pk),
        "user_id": str(session.user_id),
        "scenario_created": False,
        "scenario_id": str(session.scenario_id) if session.scenario_id else "",
    }

    result = graph.invoke(initial_state)

    assistant_text = ""
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage):
            assistant_text = msg.content if isinstance(msg.content, str) else str(msg.content)
            break

    ConversationMessage.objects.create(
        session=session,
        role="assistant",
        content=assistant_text,
        message_order=next_order + 1,
        token_count=0,
    )

    return {"assistant_message": assistant_text}


def ai_research_players(scenario: Scenario, user: Any) -> str:
    """
    Use LLM + web search to research all players in a scenario
    and set their position, capability, salience, flexibility, and risk profile
    based on external data. Overwrites existing values.
    """
    scenario_context = _build_scenario_context(str(scenario.pk))

    prompt = f"""You are a game theory research analyst. Your task is to research the players in this scenario
and determine accurate values for their position, capability, salience, flexibility, and risk profile
on each issue.

{scenario_context}

INSTRUCTIONS:
1. Use web_search to research each player — look for their current stance, power/influence, priorities, and negotiation style.
2. Based on your research, determine values (0-100) for each player on each issue:
   - position: where they want the outcome to land on the 0-100 scale
   - capability: their relative power/influence compared to other players
   - salience: how much they care about this specific issue
   - flexibility: how willing they are to compromise
   - risk_profile: risk_averse, risk_neutral, or risk_acceptant
3. Call modify_scenario with update_player_position entries for EVERY player on EVERY issue.
4. Use the EXACT player names and issue titles shown above.
5. Set ALL values — do not leave any player without complete parameters.

Research thoroughly, then make all the modifications in a single tool call."""

    graph = _get_modifier_graph()
    initial_state: ConversationState = {
        "messages": [HumanMessage(content=prompt)],
        "session_id": "",
        "user_id": str(user.pk),
        "scenario_created": False,
        "scenario_id": str(scenario.pk),
    }

    result = graph.invoke(initial_state)

    # Count how many positions were updated
    updated = PlayerPosition.objects.filter(
        player__scenario=scenario,
        player__is_active=True,
        is_active=True,
    ).count()

    # Extract the LLM's explanation
    explanation = ""
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage):
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            if content:
                explanation = content
                break

    return f"AI research complete. {updated} player positions updated across all issues."
