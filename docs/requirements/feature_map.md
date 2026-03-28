# Feature Map — Game Theory Prediction Engine

## Project Context

You are building a **Game Theory Prediction Engine** — an AI-powered web application (with mobile-responsive views) that uses Bruce Bueno de Mesquita's (BDM) expected utility model to predict outcomes of strategic scenarios and recommend interventions to engineer preferred results. A conversational LLM layer gathers scenario data from users, the game theory engine computes predicted outcomes across iterative negotiation rounds, and the platform delivers actionable strategic intelligence.

The application is built on **Django with PostgreSQL**. The Django project is already stood up and operational.

---

## Technical Conventions

Follow these conventions across all implementation work:

- **Primary Keys**: All models use `UUIDField` as the primary key (`id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)`)
- **Foreign Keys**: All foreign key references use UUID fields
- **Lookup Table**: Use a unified `LookupValue` model for all enumerated/reference data (scenario types, player types, risk profiles, status codes, etc.) rather than scattered choice fields or individual lookup tables
- **Authentication**: Google and Microsoft OAuth2 only — no password storage, no local auth
- **Timestamps**: All models include `created_at`, `updated_at` (auto-managed), and `created_by`, `updated_by` (FK to User)
- **Soft Deletes**: All primary models use `is_active` boolean rather than hard deletes
- **API Layer**: Django REST Framework for all API endpoints; JSON responses
- **Frontend**: Django templates with a modern CSS framework for responsive/mobile support
- **Docker**: All services containerized
- **Environment Config**: Settings split by environment (DEV/UAT/PROD) using environment variables

---

## Domain Model Overview

The core domain is organized around these entity relationships:

```
User
 └── Scenario (a prediction project)
      ├── ScenarioIssue (what is being decided — supports multi-issue scenarios)
      │    └── IssueScale (defines the 0–100 outcome scale with labeled endpoints)
      ├── Player (a stakeholder in the scenario)
      │    ├── PlayerPosition (player's preferred outcome on each issue, 0–100)
      │    ├── PlayerCapability (player's relative power/influence, 0–100)
      │    └── PlayerSalience (how much the player cares about each issue, 0–100)
      ├── SimulationRun (an execution of the BDM engine)
      │    ├── RoundResult (per-round state for each player across N rounds)
      │    └── PredictionOutcome (final predicted outcome with confidence)
      ├── Coalition (detected or user-defined player groupings)
      │    └── CoalitionMember (player membership in coalition)
      ├── StrategicRecommendation (engine-generated intervention advice)
      ├── ConversationSession (LLM chat thread tied to scenario)
      │    └── ConversationMessage (individual messages in the thread)
      └── ScenarioVersion (version history / branching)
```

---

## Feature Specifications

### FEATURE 1: User Authentication & Profile

**Purpose**: Secure access with zero password management burden.

**Requirements**:
- Google OAuth2 login/registration flow
- Microsoft OAuth2 login/registration flow
- No local username/password authentication — OAuth2 only
- User profile model extending Django's AbstractUser:
  - `id` (UUID primary key)
  - `email` (unique, from OAuth provider)
  - `display_name`
  - `avatar_url` (from OAuth provider)
  - `organization` (optional, free text)
  - `role` (FK to LookupValue — values: `admin`, `analyst`, `viewer`)
  - `subscription_tier` (FK to LookupValue — values: `free`, `pro`, `enterprise`)
  - `is_active`, `created_at`, `updated_at`
- On first OAuth login, auto-create user profile with `free` tier and `analyst` role
- Session management with configurable timeout
- JWT token support for API access

**Endpoints**:
- `GET /auth/google/` — initiate Google OAuth flow
- `GET /auth/google/callback/` — handle Google OAuth callback
- `GET /auth/microsoft/` — initiate Microsoft OAuth flow
- `GET /auth/microsoft/callback/` — handle Microsoft OAuth callback
- `POST /auth/logout/`
- `GET /api/users/me/` — current user profile
- `PATCH /api/users/me/` — update profile

---

### FEATURE 2: Scenario Management (CRUD & Versioning)

**Purpose**: Create, organize, version, and manage prediction scenarios.

**Requirements**:

**Scenario Model**:
- `id` (UUID)
- `title` (CharField, max 200)
- `description` (TextField)
- `scenario_type` (FK to LookupValue — values: `geopolitical`, `corporate`, `legislative`, `legal`, `market`, `negotiation`, `personal`, `custom`)
- `status` (FK to LookupValue — values: `draft`, `ready`, `running`, `completed`, `archived`)
- `owner` (FK to User)
- `is_public` (BooleanField, default False)
- `parent_version` (nullable self-FK for branching)
- `version_number` (IntegerField, default 1)
- `version_label` (CharField, optional — e.g., "What if China retaliates")
- `is_active`, `created_at`, `updated_at`, `created_by`, `updated_by`

**Scenario Operations**:
- Full CRUD on scenarios
- **Duplicate**: Deep copy a scenario with all players, positions, and issues into a new scenario
- **Branch**: Create a new version linked to the parent via `parent_version`; all data copied; user modifies the branch independently
- **Version History**: List all versions of a scenario (linked by `parent_version` chain); allow revert by duplicating any prior version as the new head
- **Archive**: Set `status` to `archived` (soft removal from active lists)
- **Scenario Dashboard**: List view showing all user scenarios with status, last modified, prediction summary (if completed), and quick actions (open, duplicate, branch, archive)

**Endpoints**:
- `GET /api/scenarios/` — list user's scenarios (filterable by status, type; sortable by date, title)
- `POST /api/scenarios/` — create scenario
- `GET /api/scenarios/{id}/` — retrieve scenario with full nested data
- `PATCH /api/scenarios/{id}/` — update scenario
- `DELETE /api/scenarios/{id}/` — soft delete (set `is_active=False`)
- `POST /api/scenarios/{id}/duplicate/` — deep copy
- `POST /api/scenarios/{id}/branch/` — create versioned branch
- `GET /api/scenarios/{id}/versions/` — list version history

---

### FEATURE 3: Scenario Issues & Outcome Scale

**Purpose**: Define what decision(s) are at stake and the range of possible outcomes.

**Requirements**:

**ScenarioIssue Model**:
- `id` (UUID)
- `scenario` (FK to Scenario)
- `title` (CharField — e.g., "Trade tariff rate")
- `description` (TextField — detailed description of the issue)
- `scale_min_label` (CharField — e.g., "Full free trade")
- `scale_max_label` (CharField — e.g., "Complete embargo")
- `scale_min_value` (IntegerField, default 0)
- `scale_max_value` (IntegerField, default 100)
- `status_quo_position` (IntegerField — where things stand today on the scale)
- `sort_order` (IntegerField — ordering for multi-issue scenarios)
- `is_active`, `created_at`, `updated_at`

**Behavior**:
- Every scenario must have at least one issue before simulation can run
- Multi-issue scenarios link the same set of players across multiple issues; each player has separate position/salience per issue
- The outcome scale is always numeric (0–100 default) with user-defined semantic labels at the endpoints and optionally at midpoints
- The status quo position is required — it anchors the model and represents what happens if no players act
- Validation: `status_quo_position` must be between `scale_min_value` and `scale_max_value`

**Endpoints**:
- `GET /api/scenarios/{id}/issues/` — list issues for a scenario
- `POST /api/scenarios/{id}/issues/` — create issue
- `PATCH /api/scenarios/{id}/issues/{issue_id}/` — update issue
- `DELETE /api/scenarios/{id}/issues/{issue_id}/` — remove issue

---

### FEATURE 4: Player / Stakeholder Management

**Purpose**: Define all actors who have influence over the scenario outcome, along with their strategic parameters.

**Requirements**:

**Player Model**:
- `id` (UUID)
- `scenario` (FK to Scenario)
- `name` (CharField — e.g., "United States", "CEO of AcmeCorp", "Labor Union")
- `description` (TextField — background, motivations, context)
- `player_type` (FK to LookupValue — values: `individual`, `organization`, `government`, `coalition_bloc`, `institution`, `other`)
- `is_active`, `created_at`, `updated_at`

**PlayerPosition Model** (per player, per issue):
- `id` (UUID)
- `player` (FK to Player)
- `issue` (FK to ScenarioIssue)
- `position` (DecimalField, 0–100 — where this player wants the outcome to land)
- `capability` (DecimalField, 0–100 — this player's relative power/influence on this issue)
- `salience` (DecimalField, 0–100 — how much this player cares about this issue)
- `flexibility` (DecimalField, 0–100 — willingness to compromise; higher = more willing to shift)
- `risk_profile` (FK to LookupValue — values: `risk_averse`, `risk_neutral`, `risk_acceptant`)
- Unique constraint on (`player`, `issue`)

**Behavior**:
- When a new issue is added to a scenario, prompt the user to define positions for all existing players on that issue
- When a new player is added, prompt the user to define positions on all existing issues
- Capability values are relative — they represent comparative influence, not absolute power; the engine normalizes them
- The LLM conversation layer should assist users in estimating these values (see Feature 9)
- Provide a bulk-edit table view: rows = players, columns = position/capability/salience per issue — allows rapid data entry and comparison
- Validation: all numeric fields must be between 0 and 100

**Endpoints**:
- `GET /api/scenarios/{id}/players/` — list all players with their positions
- `POST /api/scenarios/{id}/players/` — create player (with initial positions)
- `PATCH /api/scenarios/{id}/players/{player_id}/` — update player metadata
- `DELETE /api/scenarios/{id}/players/{player_id}/` — remove player
- `GET /api/scenarios/{id}/players/{player_id}/positions/` — get all positions for a player
- `PUT /api/scenarios/{id}/players/{player_id}/positions/` — bulk update positions for a player
- `PUT /api/scenarios/{id}/positions/bulk/` — bulk update all player positions (for table view saves)

---

### FEATURE 5: BDM Expected Utility Computation Engine

**Purpose**: The core analytical engine that implements Bruce Bueno de Mesquita's expected utility model to predict outcomes through iterative negotiation simulation.

**Requirements**:

**5.1 — Pairwise Expected Utility Calculation**

For every pair of players (i, j) on every issue, calculate whether player i would challenge player j's position. The expected utility for player i of challenging player j is:

```
EU_i(challenge_j) = P(success) × U(win) + P(failure) × U(lose) - U(status_quo)
```

Where:
- `P(success)` is the probability that player i prevails, based on the ratio of supporting capability (players who prefer i's position to j's) vs. opposing capability
- `U(win)` is the utility gain if i's preferred position is adopted (distance between j's position and i's position, weighted by i's salience)
- `U(lose)` is the utility loss if j's position is reinforced (cost of failed challenge, weighted by salience)
- `U(status_quo)` is the utility of doing nothing

The calculation must account for **risk profile**:
- Risk-averse players weight potential losses more heavily (concave utility function)
- Risk-neutral players weight gains and losses equally (linear utility function)
- Risk-acceptant players weight potential gains more heavily (convex utility function)

Implement risk transformation using the formula:
```
Risk-adjusted utility = 2 - (4 × (0.5^(1-r)))   where r = risk parameter
```
- r < 1: risk-averse
- r = 1: risk-neutral
- r > 1: risk-acceptant

**5.2 — Negotiation Round Resolution**

Each round proceeds as follows:
1. Calculate EU for all player pairs
2. Identify all **challenges** (where EU > 0 for the challenger)
3. For each challenged player, aggregate incoming pressure (weighted by challenger capability × salience)
4. Players receiving net pressure exceeding their resistance threshold **shift position** toward the weighted mean of challenger positions
5. Position shift magnitude is proportional to:
   - Net pressure received
   - The challenged player's flexibility
   - Inverse of the challenged player's salience (high-salience players resist more)
6. Players who are not challenged hold their positions
7. Record the updated positions as the starting state for the next round

**5.3 — Convergence & Termination**

The simulation runs for N rounds (configurable, default 7) or until convergence:
- **Convergence**: All player positions have shifted less than a threshold (default: 0.5 units) in the current round
- **Deadlock detection**: If two or more blocs with roughly equal combined capability hold opposing positions and neither is shifting, flag as deadlock
- Maximum rounds cap (default: 15) to prevent infinite loops

**5.4 — Outcome Prediction Calculation**

After simulation completes:
- **Predicted outcome** = the power-weighted median position across all players at the final round
  - Weight = `capability × salience` for each player
  - The median is the position where 50% of weighted capability lies on each side
- **Secondary prediction** = salience-weighted mean as a cross-check
- **Confidence level** = function of:
  - Position convergence (tight cluster = high confidence)
  - Winning coalition dominance (how much capability supports the predicted range)
  - Input data quality score (from Feature 10)

**SimulationRun Model**:
- `id` (UUID)
- `scenario` (FK to Scenario)
- `total_rounds_executed` (IntegerField)
- `converged` (BooleanField)
- `deadlock_detected` (BooleanField)
- `predicted_outcome` (DecimalField — the predicted position on the issue scale)
- `confidence_score` (DecimalField, 0–1)
- `secondary_prediction` (DecimalField — weighted mean)
- `execution_time_ms` (IntegerField)
- `parameters` (JSONField — snapshot of all engine config used for this run)
- `status` (FK to LookupValue — values: `queued`, `running`, `completed`, `failed`)
- `created_at`, `created_by`

**RoundResult Model** (captures state at each round for visualization):
- `id` (UUID)
- `simulation_run` (FK to SimulationRun)
- `round_number` (IntegerField)
- `player` (FK to Player)
- `issue` (FK to ScenarioIssue)
- `position_start` (DecimalField — position entering this round)
- `position_end` (DecimalField — position exiting this round)
- `pressure_received` (DecimalField — net pressure on this player this round)
- `challenges_made` (IntegerField — how many other players this player challenged)
- `challenges_received` (IntegerField — how many challenges this player received)
- Unique constraint on (`simulation_run`, `round_number`, `player`, `issue`)

**PredictionOutcome Model**:
- `id` (UUID)
- `simulation_run` (FK to SimulationRun)
- `issue` (FK to ScenarioIssue)
- `predicted_position` (DecimalField)
- `confidence_score` (DecimalField, 0–1)
- `weighted_median` (DecimalField)
- `weighted_mean` (DecimalField)
- `winning_coalition_capability` (DecimalField — % of total capability supporting the outcome)
- `outcome_stability` (FK to LookupValue — values: `stable`, `fragile`, `deadlocked`)
- `narrative_summary` (TextField — LLM-generated plain language explanation)
- `created_at`

**Endpoints**:
- `POST /api/scenarios/{id}/simulate/` — trigger a new simulation run
- `GET /api/scenarios/{id}/simulations/` — list all simulation runs for a scenario
- `GET /api/simulations/{run_id}/` — get simulation results with prediction outcomes
- `GET /api/simulations/{run_id}/rounds/` — get round-by-round results for visualization
- `GET /api/simulations/{run_id}/rounds/{round_number}/` — get specific round state

**Engine Configuration Parameters** (stored in SimulationRun.parameters JSONField):
```json
{
  "max_rounds": 7,
  "convergence_threshold": 0.5,
  "deadlock_detection_enabled": true,
  "deadlock_capability_balance_threshold": 0.1,
  "risk_model": "bdm_standard",
  "position_shift_dampening": 0.8,
  "flexibility_weight": 1.0,
  "salience_resistance_weight": 1.0
}
```

---

### FEATURE 6: Coalition & Alliance Analysis

**Purpose**: Detect natural player groupings, model coalition dynamics, and identify pivotal actors.

**Requirements**:

**Coalition Model**:
- `id` (UUID)
- `simulation_run` (FK to SimulationRun)
- `issue` (FK to ScenarioIssue)
- `name` (CharField — auto-generated or user-labeled, e.g., "Pro-Trade Bloc")
- `coalition_type` (FK to LookupValue — values: `detected`, `user_defined`, `hypothetical`)
- `combined_capability` (DecimalField — sum of member capabilities)
- `combined_weighted_power` (DecimalField — sum of member capability × salience)
- `mean_position` (DecimalField — average position of coalition members)
- `is_winning` (BooleanField — does this coalition have majority weighted power?)
- `created_at`

**CoalitionMember Model**:
- `id` (UUID)
- `coalition` (FK to Coalition)
- `player` (FK to Player)
- `is_pivotal` (BooleanField — would removing this player cause the coalition to lose winning status?)

**Coalition Detection Algorithm**:
1. After simulation completes, cluster players by final position using a configurable proximity threshold (default: 10 units on the 0–100 scale)
2. For each cluster, calculate combined capability and weighted power
3. Determine if any cluster constitutes a winning coalition (>50% weighted power)
4. Mark the largest winning cluster as the **winning coalition**
5. For each member of the winning coalition, test whether removing them drops the coalition below 50% — if so, mark as **pivotal**

**Pivotal Player Analysis**:
- Identify **swing players**: players whose current position is near the boundary between two coalitions and whose shift would change the outcome
- Calculate each player's **marginal impact**: how much the predicted outcome moves if this player's position shifts by ±10 units
- Rank players by marginal impact — the top-ranked are the highest-leverage targets for intervention

**Endpoints**:
- `GET /api/simulations/{run_id}/coalitions/` — list detected coalitions
- `GET /api/simulations/{run_id}/coalitions/{coalition_id}/` — coalition detail with members
- `GET /api/simulations/{run_id}/pivotal-players/` — ranked list of pivotal and swing players
- `POST /api/simulations/{run_id}/coalitions/` — create user-defined coalition for what-if analysis

---

### FEATURE 7: Sensitivity Analysis

**Purpose**: Identify which input parameters most influence the predicted outcome and quantify model robustness.

**Requirements**:

**7.1 — One-at-a-Time (OAT) Sensitivity**:
- For each player on each issue, independently vary position, capability, and salience by ±10%, ±25%, ±50% from the base value
- Re-run the simulation for each variation
- Record the resulting change in predicted outcome
- Rank parameters by **outcome sensitivity** (largest outcome change per unit input change)

**7.2 — Monte Carlo Sensitivity** (Pro/Enterprise tier):
- Define uncertainty ranges for each input parameter (e.g., Player A's capability is 60 ± 15)
- Run N simulations (default 500, configurable up to 5000) sampling from uniform or normal distributions within those ranges
- Produce a **probability distribution** of predicted outcomes
- Calculate percentile-based confidence intervals (10th, 25th, 50th, 75th, 90th)

**SensitivityResult Model**:
- `id` (UUID)
- `simulation_run` (FK to SimulationRun)
- `analysis_type` (FK to LookupValue — values: `oat`, `monte_carlo`)
- `parameters_tested` (JSONField — list of parameters and their variation ranges)
- `results` (JSONField — structured results including parameter rankings and outcome distributions)
- `created_at`

**Endpoints**:
- `POST /api/simulations/{run_id}/sensitivity/oat/` — trigger OAT sensitivity analysis
- `POST /api/simulations/{run_id}/sensitivity/monte-carlo/` — trigger Monte Carlo analysis
- `GET /api/simulations/{run_id}/sensitivity/` — get sensitivity results

---

### FEATURE 8: Outcome Engineering & Strategic Recommendations

**Purpose**: Not just predict what will happen, but advise the user on how to change the outcome in their favor.

**Requirements**:

**8.1 — Leverage Point Identification**:
- Using sensitivity analysis results, identify the **top 5 highest-leverage interventions** — specific changes to specific players' parameters that would most shift the outcome
- Rank by effort-to-impact ratio: a 5-point shift in a low-salience player's position is easier than a 5-point shift in a high-salience player's position
- For each leverage point, calculate the **required shift** to move the outcome to the user's preferred position

**8.2 — Strategic Move Generation (LLM)**:
- Pass the engine outputs (leverage points, coalition data, player profiles) to the LLM
- LLM generates **3–5 specific strategic recommendations** in plain language
- Each recommendation includes:
  - The target player(s) to influence
  - The suggested approach (increase their salience, shift their position, reduce their capability, fracture their coalition, etc.)
  - The expected impact on the predicted outcome
  - Potential second-order effects and counter-moves
  - A difficulty/feasibility rating (1–5)
- Recommendations are grounded in game theory logic, not generic advice

**StrategicRecommendation Model**:
- `id` (UUID)
- `simulation_run` (FK to SimulationRun)
- `recommendation_type` (FK to LookupValue — values: `position_shift`, `coalition_build`, `coalition_fracture`, `salience_increase`, `capability_reduction`, `alliance_formation`)
- `target_players` (M2M to Player)
- `description` (TextField — LLM-generated recommendation narrative)
- `target_parameter` (CharField — e.g., "position", "salience", "capability")
- `current_value` (DecimalField)
- `recommended_value` (DecimalField)
- `predicted_outcome_if_applied` (DecimalField)
- `outcome_delta` (DecimalField — how much the prediction changes)
- `feasibility_score` (IntegerField, 1–5)
- `sort_order` (IntegerField — ranked by impact)
- `created_at`

**8.3 — What-If Scenario Runner**:
- User can take any recommendation and apply it as a scenario modification
- System creates a **branched scenario** with the recommended parameter changes pre-applied
- Run the simulation on the branch and compare outcomes side by side
- This creates a tight loop: predict → recommend → test → refine

**Endpoints**:
- `GET /api/simulations/{run_id}/recommendations/` — get strategic recommendations
- `POST /api/simulations/{run_id}/recommendations/{rec_id}/apply/` — apply recommendation as a branched scenario and run simulation

---

### FEATURE 9: Conversational AI Layer (LLM Integration)

**Purpose**: The LLM serves as an expert analyst that guides users through scenario construction, validates inputs, explains outputs, and generates strategic narratives.

**Requirements**:

**9.1 — Conversation Session Management**:

**ConversationSession Model**:
- `id` (UUID)
- `scenario` (FK to Scenario)
- `user` (FK to User)
- `session_type` (FK to LookupValue — values: `scenario_builder`, `analysis_review`, `strategy_advisor`, `general`)
- `status` (FK to LookupValue — values: `active`, `completed`, `abandoned`)
- `created_at`, `updated_at`

**ConversationMessage Model**:
- `id` (UUID)
- `session` (FK to ConversationSession)
- `role` (CharField — values: `user`, `assistant`, `system`)
- `content` (TextField)
- `structured_data` (JSONField, nullable — parsed parameters extracted from the message, e.g., player positions identified)
- `message_order` (IntegerField)
- `token_count` (IntegerField)
- `created_at`

**9.2 — Scenario Builder Conversation Flow**:

The LLM guides the user through a structured intake process. The system prompt should instruct the LLM to:

1. **Issue Definition Phase**: Ask the user to describe the situation. Extract and confirm:
   - The core issue/decision at stake
   - The range of possible outcomes (map to 0–100 scale with labeled endpoints)
   - The current status quo
   - Whether there are multiple linked issues

2. **Stakeholder Elicitation Phase**: Guide the user through identifying players:
   - Ask "Who are the key players who can influence this outcome?"
   - For each player, conversationally extract position, capability, salience, and flexibility
   - Use anchoring questions: "On a scale where 0 means [min_label] and 100 means [max_label], where does [player] want the outcome to land?"
   - Challenge vague answers: "You said they're 'very powerful' — compared to the other players, would you put them in the top third? What percentage of total influence do they hold?"
   - Suggest missing stakeholders: "In scenarios like this, regulatory bodies often play a role. Is there a regulator or oversight body we should include?"

3. **Validation Phase**: Before simulation, the LLM reviews all inputs:
   - Flag inconsistencies: "You rated Player A as high power but low salience — that means they likely won't engage actively. Is that accurate?"
   - Check completeness: "We have 6 players defined. Are there any other actors who could influence this outcome?"
   - Confirm the full parameter set in a summary table format

4. **Results Explanation Phase**: After simulation, the LLM:
   - Generates a narrative explaining the predicted outcome in plain language
   - Explains the strategic logic: why players moved, who formed coalitions, what drove convergence
   - Highlights key decision points and critical assumptions

5. **Strategy Advisor Phase**: When reviewing recommendations:
   - Explains each recommendation with strategic reasoning
   - Answers follow-up questions about specific players, coalitions, or moves
   - Helps the user think through second-order effects

**9.3 — Structured Output Extraction**:

The LLM conversation must produce structured data that can populate the domain models. Implement a **dual-output pattern**:
- The LLM responds conversationally to the user
- Simultaneously, the system extracts structured parameters from the LLM response using tool use / function calling
- Extracted parameters are stored in `ConversationMessage.structured_data` and used to pre-populate scenario models
- The user confirms or adjusts the extracted values before they are committed

Define the following extraction schemas:
```json
{
  "issue_extracted": {
    "title": "string",
    "description": "string",
    "scale_min_label": "string",
    "scale_max_label": "string",
    "status_quo_position": "integer"
  },
  "player_extracted": {
    "name": "string",
    "description": "string",
    "player_type": "string",
    "position": "number",
    "capability": "number",
    "salience": "number",
    "flexibility": "number",
    "risk_profile": "string"
  }
}
```

**9.4 — LLM Configuration**:
- Use Claude (Anthropic API) as the primary LLM
- System prompts are stored as configurable templates in the database, not hardcoded
- Include BDM methodology context in the system prompt so the LLM understands the model
- Token usage tracking per conversation session and per user
- Implement conversation context windowing — summarize older messages when context approaches token limits
- Streaming responses for real-time conversational feel

**Endpoints**:
- `POST /api/scenarios/{id}/conversations/` — start a new conversation session
- `GET /api/scenarios/{id}/conversations/` — list conversation sessions
- `POST /api/conversations/{session_id}/messages/` — send a message (triggers LLM response)
- `GET /api/conversations/{session_id}/messages/` — get conversation history
- `GET /api/conversations/{session_id}/extracted-data/` — get all structured data extracted from conversation

---

### FEATURE 10: Data Quality & Input Validation

**Purpose**: Ensure the prediction engine produces meaningful results by validating and scoring input data quality.

**Requirements**:

**10.1 — Input Completeness Checks**:
- Every scenario must have at least 1 issue, at least 3 players, and positions defined for all player-issue combinations before simulation can run
- Flag scenarios where all players have the same position (trivial — no conflict to resolve)
- Flag scenarios where one player has >80% of total capability (dominant player — outcome is predetermined)
- Warning if fewer than 5 players (model works best with more actors)

**10.2 — Data Quality Score**:
- Calculate a composite quality score (0–100) based on:
  - Completeness: all fields populated (weight: 30%)
  - Diversity: reasonable spread of positions and capabilities (weight: 25%)
  - Consistency: no contradictory parameter combinations flagged by LLM (weight: 25%)
  - Granularity: players use a range of values, not all round numbers like 50, 75, 100 (weight: 20%)
- Display the quality score prominently before simulation with suggestions for improvement
- Store quality score on the SimulationRun

**10.3 — Parameter Calibration Assistance**:
- When users enter extreme or unusual values, provide contextual guidance
- Example: "You set this player's capability at 95/100 — that puts them as the single most powerful actor by far. For context, in BDM's models, even the United States in global scenarios typically rates 70–85. Are you sure?"
- Relative calibration tool: show a bar chart of all players' capabilities side by side so users can visually assess relative power

---

### FEATURE 11: Visualization & Dashboards

**Purpose**: Render scenario data, simulation results, and strategic insights in clear, interactive visualizations.

**Requirements**:

**11.1 — Stakeholder Landscape Map** (P0 — required for MVP):
- Scatter plot: X-axis = player position (0–100), Y-axis = player capability
- Bubble size = player salience
- Color coding by coalition membership (after simulation) or player type (before simulation)
- Hover tooltip shows player name, all parameter values
- Animated version: show position movement across simulation rounds (play/pause/step controls)
- This is the signature visualization — it must be polished, responsive, and interactive

**11.2 — Outcome Probability Distribution**:
- Histogram or density curve showing predicted outcome range on the issue scale
- Vertical line for the primary prediction, shaded confidence interval
- When Monte Carlo sensitivity has been run, display the full distribution
- Overlay multiple simulation runs for comparison

**11.3 — Negotiation Timeline**:
- X-axis = simulation round number, Y-axis = position on issue scale
- One line per player (or per coalition), showing position trajectory across rounds
- Annotate key events: when a player made a major shift, when a coalition formed or fractured
- Interactive: click on a round to see the full state at that point

**11.4 — Sensitivity Tornado Diagram**:
- Horizontal bar chart ranking parameters by outcome sensitivity
- Each bar shows the outcome range when that parameter is varied
- Top bar = most sensitive parameter
- Clickable: click a bar to see the full sensitivity curve for that parameter

**11.5 — Influence Network Graph**:
- Network diagram showing players as nodes, challenge relationships as edges
- Edge weight/thickness = strength of challenge (EU magnitude)
- Arrow direction = who is challenging whom
- Node size = capability, node color = coalition
- Layout: force-directed or circular, player clusters visible

**11.6 — Decision Comparison Matrix**:
- Side-by-side comparison of 2–4 scenario branches or intervention strategies
- Columns: scenario variant, rows: key metrics (predicted outcome, confidence, winning coalition, top recommendation)
- Highlight differences in green/red

**11.7 — Scenario Summary Dashboard**:
- Single-page view combining:
  - Scenario metadata and status
  - Data quality score
  - Stakeholder landscape map (compact)
  - Predicted outcome with confidence
  - Top 3 strategic recommendations
  - Link to full analysis views

---

### FEATURE 12: Reporting & Export

**Purpose**: Generate downloadable reports and shareable summaries of predictions and analysis.

**Requirements**:
- **Executive Summary PDF**: 1–2 page PDF with scenario description, key players, predicted outcome, confidence level, and top recommendations
- **Full Analysis Report PDF**: Comprehensive report with all visualizations, detailed methodology explanation, round-by-round data, sensitivity analysis, and coalition analysis
- **Data Export**: CSV/JSON export of all scenario data (players, positions, simulation results, round data)
- **Shareable Dashboard Link**: Generate a read-only URL for a scenario's results dashboard (respects `is_public` flag)

**Endpoints**:
- `GET /api/scenarios/{id}/export/summary-pdf/`
- `GET /api/scenarios/{id}/export/full-report-pdf/`
- `GET /api/scenarios/{id}/export/data/` (format param: csv or json)
- `POST /api/scenarios/{id}/share/` — generate shareable link

---

### FEATURE 13: Scenario Templates & Case Studies

**Purpose**: Accelerate onboarding and build user intuition by providing pre-built scenario structures and historical examples.

**Requirements**:

**ScenarioTemplate Model**:
- `id` (UUID)
- `title` (CharField)
- `description` (TextField)
- `scenario_type` (FK to LookupValue)
- `template_data` (JSONField — contains pre-defined issues, player archetypes with suggested parameter ranges, and guidance notes)
- `is_system` (BooleanField — system-provided vs. user-created)
- `usage_count` (IntegerField)
- `is_active`, `created_at`

**System Templates** (pre-loaded):
- Corporate M&A Negotiation
- Legislative Vote / Policy Decision
- Geopolitical Conflict
- Market Entry Strategy
- Contract / Legal Negotiation
- Organizational Change Initiative
- Competitive Pricing Decision

**Case Study Library**:
- Curated scenarios based on BDM's published predictions (with proper citation)
- Each case study includes: historical context, player data, the model's prediction, and the actual outcome
- Users can clone a case study into their workspace and modify it
- Serve as both educational content and model validation

**Endpoints**:
- `GET /api/templates/` — list available templates
- `POST /api/templates/{id}/use/` — create a new scenario from a template
- `GET /api/case-studies/` — list case studies
- `GET /api/case-studies/{id}/` — view case study detail
- `POST /api/case-studies/{id}/clone/` — clone into user workspace

---

### FEATURE 14: Prediction Tracking & Accuracy

**Purpose**: Build trust by tracking prediction accuracy over time as real-world outcomes materialize.

**Requirements**:

**PredictionTracking Model**:
- `id` (UUID)
- `prediction_outcome` (FK to PredictionOutcome)
- `actual_outcome_position` (DecimalField, nullable — filled in when real outcome is known)
- `actual_outcome_description` (TextField)
- `accuracy_score` (DecimalField, nullable — calculated distance between predicted and actual)
- `outcome_date` (DateField — when the real outcome occurred)
- `recorded_by` (FK to User)
- `created_at`

**Accuracy Metrics**:
- **Prediction error**: absolute distance between predicted and actual position
- **Brier-style score**: normalized accuracy across all tracked predictions
- **Calibration analysis**: for predictions with confidence levels, how well-calibrated are they? (e.g., of predictions with 80% confidence, did roughly 80% fall within the predicted range?)
- User accuracy dashboard showing their track record over time

**Endpoints**:
- `POST /api/predictions/{outcome_id}/track/` — record actual outcome
- `GET /api/users/me/accuracy/` — user's accuracy dashboard data
- `GET /api/predictions/tracked/` — list all tracked predictions with accuracy scores

---

### FEATURE 15: Mobile-Responsive Experience

**Purpose**: Ensure full usability on mobile devices with optimized layouts and touch interactions.

**Requirements**:
- All views must be fully responsive from 320px to 2560px viewport width
- **Mobile-optimized conversational interface**: the LLM chat is the primary mobile interaction — full-screen chat view with minimal chrome
- **Mobile scenario dashboard**: card-based layout, swipeable, with quick-action buttons (view, run simulation, share)
- **Mobile-optimized visualizations**: stakeholder map and timeline must be touch-friendly with pinch-to-zoom and tap-for-detail
- **Progressive disclosure on mobile**: show summary views first, drill down on tap rather than showing all detail at once
- **Offline indicator**: clearly show when the user is offline and what functionality is limited
- Bottom navigation bar on mobile: Home (dashboard), New (create scenario), Chat (active conversation), Profile

---

### FEATURE 16: LookupValue Reference Data

**Purpose**: Centralized enumeration management for all typed fields across the application.

**Requirements**:

**LookupValue Model**:
- `id` (UUID)
- `category` (CharField — groups related values, e.g., `scenario_type`, `player_type`, `risk_profile`)
- `code` (CharField — machine-readable key, e.g., `risk_averse`)
- `display_name` (CharField — human-readable label, e.g., "Risk Averse")
- `description` (TextField, optional)
- `sort_order` (IntegerField)
- `is_active` (BooleanField)
- `created_at`, `updated_at`
- Unique constraint on (`category`, `code`)

**Required Categories and Initial Values**:

| Category | Values |
|---|---|
| `scenario_type` | geopolitical, corporate, legislative, legal, market, negotiation, personal, custom |
| `scenario_status` | draft, ready, running, completed, archived |
| `player_type` | individual, organization, government, coalition_bloc, institution, other |
| `risk_profile` | risk_averse, risk_neutral, risk_acceptant |
| `user_role` | admin, analyst, viewer |
| `subscription_tier` | free, pro, enterprise |
| `simulation_status` | queued, running, completed, failed |
| `outcome_stability` | stable, fragile, deadlocked |
| `coalition_type` | detected, user_defined, hypothetical |
| `recommendation_type` | position_shift, coalition_build, coalition_fracture, salience_increase, capability_reduction, alliance_formation |
| `conversation_session_type` | scenario_builder, analysis_review, strategy_advisor, general |
| `conversation_status` | active, completed, abandoned |
| `sensitivity_type` | oat, monte_carlo |

**Endpoints**:
- `GET /api/lookups/` — list all lookup categories
- `GET /api/lookups/{category}/` — list values for a category
- Admin-only CRUD for managing lookup values

---

## Implementation Phases

### Phase 1 — Foundation (MVP)
1. LookupValue model and seed data migration
2. User model with Google/Microsoft OAuth2
3. Scenario CRUD with versioning
4. ScenarioIssue and Player/PlayerPosition models
5. BDM Expected Utility Engine (Features 5.1–5.4)
6. Multi-round simulation with convergence detection
7. Basic conversational scenario builder (Feature 9.2, phases 1–3)
8. Stakeholder Landscape Map visualization
9. Scenario Summary Dashboard
10. Mobile-responsive layout

### Phase 2 — Intelligence
1. Coalition detection and pivotal player analysis
2. Sensitivity analysis (OAT)
3. Outcome engineering and strategic recommendations
4. LLM results explanation and strategy advisor
5. Negotiation timeline visualization
6. Sensitivity tornado diagram
7. Data quality scoring

### Phase 3 — Scale & Polish
1. Monte Carlo sensitivity analysis
2. Full visualization suite (influence network, decision comparison)
3. Reporting and PDF export
4. Scenario templates and case study library
5. Prediction tracking and accuracy dashboard
6. What-if scenario branching workflow
7. Shareable dashboard links

### Phase 4 — Growth
1. Collaboration features (shared scenarios, team roles)
2. API access for programmatic use
3. Advanced mobile optimizations
4. Subscription tier enforcement and usage metering
5. LLM prompt optimization and cost management

---

## Key Technical Decisions to Make During Implementation

1. **Computation engine location**: Implement the BDM engine as a Django service module (synchronous for small scenarios) with Celery task support for Monte Carlo and large simulations
2. **LLM integration**: Use the Anthropic Python SDK (`anthropic` package) with streaming for the conversational layer; store system prompts as database-managed templates
3. **Visualization library**: Evaluate D3.js, Plotly.js, or Chart.js for interactive visualizations; D3 preferred for the stakeholder map and network graph
4. **Real-time updates**: Django Channels with WebSocket for simulation progress and LLM streaming responses
5. **Caching**: Redis for caching simulation results and frequently-accessed scenario data
6. **Background tasks**: Celery with Redis broker for simulation runs, sensitivity analysis, report generation

---

## Data Seed Requirements

On initial deployment, the system must be seeded with:
1. All LookupValue records for every category listed above
2. System scenario templates (7 templates listed in Feature 13)
3. At least 2 case studies with full player data and known outcomes for demonstration
4. Default engine configuration parameters
5. Default LLM system prompt templates for each conversation session type
