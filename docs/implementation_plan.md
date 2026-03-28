# Implementation Plan — Game Theory Prediction Engine

## What Already Exists

The GSD framework provides a solid foundation:

- **Django 5 + PostgreSQL 16** — fully containerized with Docker Compose
- **BaseModel** — UUID PKs, timestamps, soft deletes (all models inherit from this)
- **User model** — email-based, OAuth2 (Google + Microsoft), JWT tokens, roles M2M
- **LookupValue model** — hierarchical parent-child reference data (currently seeded with generic GSD types)
- **RBAC system** — ControlPointGroups, ControlPoints, Roles
- **GraphQL API** — Strawberry at `/graphql/` with full CRUD for Users, Roles, ControlPoints, LookupValues
- **Admin UI** — Django template-based CRUD pages with filtering, sorting, pagination
- **Celery + Redis** — worker configured, task queue ready
- **Social Auth pipeline** — Google/Microsoft OAuth2 with JWT issuance
- **Frontend skeleton** — React 18 + Vite (exists but not primary; Django templates are the main UI)

## What Needs to Be Built

Everything below maps to the capabilities doc (P0–P3) and feature map (Features 1–16).

---

## Phase 1 — Foundation (MVP)

**Goal**: A user can create a scenario, define issues and players, run a BDM simulation, and see the predicted outcome on a stakeholder landscape map.

### Step 1.1: Extend LookupValue Seed Data
**Feature Map**: Feature 16
**Effort**: Small
**Files**: `apps/lookup/management/commands/seed_lookups.py`, new migration

- The existing LookupValue model structure works as-is (parent-child hierarchy)
- **However**, the feature map specifies a flat `category` + `code` structure with unique constraint on `(category, code)`. The existing model uses `parent` FK + `code` with unique on `(parent, code)`. **Decision: keep the existing parent-child model** — it's more flexible. Map "category" to the parent LookupValue, "code" to the child's code field.
- Add all required seed categories and values:
  - `SCENARIO_TYPE` → geopolitical, corporate, legislative, legal, market, negotiation, personal, custom
  - `SCENARIO_STATUS` → draft, ready, running, completed, archived
  - `PLAYER_TYPE` → individual, organization, government, coalition_bloc, institution, other
  - `RISK_PROFILE` → risk_averse, risk_neutral, risk_acceptant
  - `USER_ROLE` → admin, analyst, viewer (app-level, distinct from RBAC roles)
  - `SUBSCRIPTION_TIER` → free, pro, enterprise
  - `SIMULATION_STATUS` → queued, running, completed, failed
  - `OUTCOME_STABILITY` → stable, fragile, deadlocked
  - `COALITION_TYPE` → detected, user_defined, hypothetical
  - `RECOMMENDATION_TYPE` → position_shift, coalition_build, coalition_fracture, salience_increase, capability_reduction, alliance_formation
  - `CONVERSATION_SESSION_TYPE` → scenario_builder, analysis_review, strategy_advisor, general
  - `CONVERSATION_STATUS` → active, completed, abandoned
  - `SENSITIVITY_TYPE` → oat, monte_carlo
- Remove or keep the existing generic GSD seed data (CUSTOMER_TYPE, etc.) — these can stay for now but are not used by game theory features

### Step 1.2: Extend User Model
**Feature Map**: Feature 1
**Effort**: Small
**Files**: `apps/users/models.py`, migration

- Add fields to existing User model:
  - `display_name` (CharField, blank=True)
  - `organization` (CharField, blank=True)
  - `app_role` (FK to LookupValue, nullable — values from USER_ROLE category)
  - `subscription_tier` (FK to LookupValue, nullable — values from SUBSCRIPTION_TIER category)
- Update the social auth pipeline to set defaults on first login: `app_role=analyst`, `subscription_tier=free`
- Add `GET /api/users/me/` and `PATCH /api/users/me/` endpoints (REST)

### Step 1.3: Create New Django App — `apps/scenarios`
**Feature Map**: Features 2, 3, 4
**Effort**: Large
**Files**: New app `apps/scenarios/` with models, views, serializers, URLs, admin, forms, services

**Models to create:**

**Scenario** (Feature 2):
- `id` (UUID, from BaseModel)
- `title` (CharField, max 200)
- `description` (TextField, blank=True)
- `scenario_type` (FK to LookupValue — SCENARIO_TYPE)
- `status` (FK to LookupValue — SCENARIO_STATUS, default=draft)
- `owner` (FK to User)
- `is_public` (BooleanField, default=False)
- `parent_version` (nullable self-FK for branching)
- `version_number` (IntegerField, default=1)
- `version_label` (CharField, blank=True)
- `created_by`, `updated_by` (FK to User)
- Inherits: `is_active`, `created_at`, `updated_at` from BaseModel

**ScenarioIssue** (Feature 3):
- `scenario` (FK to Scenario)
- `title` (CharField)
- `description` (TextField)
- `scale_min_label` (CharField)
- `scale_max_label` (CharField)
- `scale_min_value` (IntegerField, default=0)
- `scale_max_value` (IntegerField, default=100)
- `status_quo_position` (IntegerField)
- `sort_order` (IntegerField)

**Player** (Feature 4):
- `scenario` (FK to Scenario)
- `name` (CharField)
- `description` (TextField, blank=True)
- `player_type` (FK to LookupValue — PLAYER_TYPE)

**PlayerPosition** (Feature 4):
- `player` (FK to Player)
- `issue` (FK to ScenarioIssue)
- `position` (DecimalField, 0–100)
- `capability` (DecimalField, 0–100)
- `salience` (DecimalField, 0–100)
- `flexibility` (DecimalField, 0–100)
- `risk_profile` (FK to LookupValue — RISK_PROFILE)
- Unique constraint: (`player`, `issue`)

**Endpoints (REST)**:
- Full CRUD for Scenarios, Issues, Players, PlayerPositions
- `POST /api/scenarios/{id}/duplicate/` — deep copy
- `POST /api/scenarios/{id}/branch/` — versioned branch
- `GET /api/scenarios/{id}/versions/` — version history
- `PUT /api/scenarios/{id}/positions/bulk/` — bulk position update

**Admin UI**:
- Scenario list page (using existing admin/list.html pattern)
- Scenario detail/edit form
- Player management table (inline with scenario)
- Bulk position editor (rows=players, cols=position/capability/salience per issue)

### Step 1.4: BDM Expected Utility Engine
**Feature Map**: Feature 5
**Effort**: Large
**Files**: `apps/engine/` (new app), `apps/engine/services.py`, `apps/engine/models.py`, `apps/engine/tasks.py`

**Models:**

**SimulationRun**:
- `scenario` (FK to Scenario)
- `total_rounds_executed` (IntegerField)
- `converged` (BooleanField)
- `deadlock_detected` (BooleanField)
- `predicted_outcome` (DecimalField)
- `confidence_score` (DecimalField, 0–1)
- `secondary_prediction` (DecimalField)
- `execution_time_ms` (IntegerField)
- `parameters` (JSONField)
- `status` (FK to LookupValue — SIMULATION_STATUS)
- `created_by` (FK to User)

**RoundResult**:
- `simulation_run` (FK to SimulationRun)
- `round_number` (IntegerField)
- `player` (FK to Player)
- `issue` (FK to ScenarioIssue)
- `position_start` (DecimalField)
- `position_end` (DecimalField)
- `pressure_received` (DecimalField)
- `challenges_made` (IntegerField)
- `challenges_received` (IntegerField)
- Unique constraint: (`simulation_run`, `round_number`, `player`, `issue`)

**PredictionOutcome**:
- `simulation_run` (FK to SimulationRun)
- `issue` (FK to ScenarioIssue)
- `predicted_position` (DecimalField)
- `confidence_score` (DecimalField, 0–1)
- `weighted_median` (DecimalField)
- `weighted_mean` (DecimalField)
- `winning_coalition_capability` (DecimalField)
- `outcome_stability` (FK to LookupValue — OUTCOME_STABILITY)
- `narrative_summary` (TextField, blank=True)

**Engine Service** (`apps/engine/services.py`):
1. **Pairwise EU Calculation** (Feature 5.1):
   - For each player pair (i, j) on each issue: `EU_i(challenge_j) = P(success) × U(win) + P(failure) × U(lose) - U(status_quo)`
   - P(success) based on ratio of supporting vs opposing capability
   - Risk adjustment: `2 - (4 × (0.5^(1-r)))` where r = risk parameter
2. **Round Resolution** (Feature 5.2):
   - Calculate EU for all pairs → identify challenges → aggregate pressure → shift positions
   - Position shift proportional to: net pressure × flexibility × inverse salience
3. **Convergence & Termination** (Feature 5.3):
   - Run N rounds (default 7, max 15)
   - Converge when all shifts < 0.5 units
   - Detect deadlock when balanced opposing blocs
4. **Outcome Prediction** (Feature 5.4):
   - Power-weighted median (primary)
   - Salience-weighted mean (secondary)
   - Confidence from convergence tightness + coalition dominance

**Celery Task** (`apps/engine/tasks.py`):
- `run_simulation(scenario_id, user_id, params)` — async task for engine execution
- Updates SimulationRun status as it progresses

**Endpoints**:
- `POST /api/scenarios/{id}/simulate/` — trigger simulation
- `GET /api/scenarios/{id}/simulations/` — list runs
- `GET /api/simulations/{run_id}/` — results with prediction outcomes
- `GET /api/simulations/{run_id}/rounds/` — round-by-round data

### Step 1.5: Stakeholder Landscape Map Visualization
**Feature Map**: Feature 11.1
**Effort**: Medium
**Files**: Templates + JavaScript (D3.js or Chart.js)

- Scatter plot: X = position, Y = capability, bubble size = salience
- Color by player type (pre-simulation) or coalition (post-simulation)
- Hover tooltips with all parameter values
- Animated round-by-round playback with play/pause/step controls
- Responsive and touch-friendly
- Rendered on the scenario detail page

### Step 1.6: Scenario Summary Dashboard
**Feature Map**: Feature 11.7
**Effort**: Medium
**Files**: Templates, views

- Single page combining: scenario metadata, data quality score, compact stakeholder map, predicted outcome with confidence, top recommendations (placeholder until Phase 2)
- This becomes the scenario detail page after simulation

### Step 1.7: Game Theory Dashboard (Home Page)
**Feature Map**: General UX
**Effort**: Small
**Files**: `templates/dashboard.html` (already created), views

- Update the existing dashboard.html to show:
  - User's scenarios list (recent, filterable by status)
  - Quick-create scenario button
  - Stats summary (total scenarios, completed simulations, etc.)
- Replace the placeholder "Coming Soon" cards with real navigation

### Step 1.8: Data Quality & Validation
**Feature Map**: Feature 10
**Effort**: Medium
**Files**: `apps/engine/validators.py`

- Pre-simulation validation: at least 1 issue, 3+ players, all positions defined
- Warnings: trivial scenarios (all same position), dominant player (>80% capability), few players (<5)
- Composite quality score (0–100): completeness (30%), diversity (25%), consistency (25%), granularity (20%)
- Display score before simulation with improvement suggestions

### Step 1.9: Mobile-Responsive Layout
**Feature Map**: Feature 15
**Effort**: Medium
**Files**: Templates, CSS

- Ensure all views work 320px–2560px
- Card-based mobile scenario dashboard
- Progressive disclosure on mobile (summary first, drill-down on tap)
- The existing Materialize CSS framework supports responsive grids — leverage it

---

## Phase 2 — Intelligence

**Goal**: Coalition analysis, sensitivity analysis, outcome engineering with LLM-generated recommendations, and richer visualizations.

### Step 2.1: Coalition Detection & Pivotal Player Analysis
**Feature Map**: Feature 6
**Effort**: Medium
**Files**: `apps/engine/models.py` (add Coalition, CoalitionMember), `apps/engine/services.py`

- Models: Coalition, CoalitionMember
- Detection algorithm: cluster players by final position (threshold=10 units), calculate combined capability, determine winning coalition, mark pivotal players
- Swing player analysis: marginal impact calculation (±10 unit shift)
- Endpoints for coalition data and pivotal player rankings

### Step 2.2: Sensitivity Analysis (OAT)
**Feature Map**: Feature 7.1
**Effort**: Medium
**Files**: `apps/engine/models.py` (add SensitivityResult), `apps/engine/services.py`, `apps/engine/tasks.py`

- One-at-a-Time: vary each parameter ±10%, ±25%, ±50%, re-run simulation, record outcome delta
- Rank by outcome sensitivity
- Celery task for batch re-runs
- SensitivityResult model with JSONField for results

### Step 2.3: Outcome Engineering & Strategic Recommendations
**Feature Map**: Feature 8
**Effort**: Large
**Files**: `apps/engine/models.py` (add StrategicRecommendation), `apps/engine/services.py`, LLM integration

- Leverage point identification from sensitivity data
- Rank interventions by effort-to-impact ratio
- StrategicRecommendation model with target players M2M, parameter changes, predicted deltas
- LLM generates 3–5 strategic recommendations in plain language using engine outputs
- What-if runner: apply recommendation as branched scenario, re-simulate, compare

### Step 2.4: Conversational AI Layer (Scenario Builder)
**Feature Map**: Feature 9
**Effort**: Large
**Files**: New app `apps/conversations/` with models, services, views, Anthropic SDK integration

- Models: ConversationSession, ConversationMessage
- Conversation flow: Issue Definition → Stakeholder Elicitation → Validation → Results Explanation → Strategy Advisor
- Structured output extraction: dual-output pattern with tool use / function calling
- Claude (Anthropic API) as primary LLM
- System prompts stored in DB as configurable templates
- Token tracking per session and per user
- Streaming responses via Django Channels / SSE
- Context windowing for long conversations

### Step 2.5: Negotiation Timeline Visualization
**Feature Map**: Feature 11.3
**Effort**: Medium
**Files**: Templates + D3.js

- X = round number, Y = position on issue scale
- One line per player, showing position trajectory
- Annotate major shifts and coalition formation events
- Interactive: click round to see full state

### Step 2.6: Sensitivity Tornado Diagram
**Feature Map**: Feature 11.4
**Effort**: Small
**Files**: Templates + D3.js/Chart.js

- Horizontal bar chart ranked by parameter sensitivity
- Each bar shows outcome range when parameter varies
- Clickable for full sensitivity curve

### Step 2.7: Data Quality Scoring (Enhanced)
**Feature Map**: Feature 10.2, 10.3
**Effort**: Small
**Files**: `apps/engine/validators.py`

- LLM-assisted consistency checking (flag contradictory parameters)
- Calibration assistance: contextual guidance for extreme values
- Relative calibration tool: side-by-side bar chart of all players' capabilities

---

## Phase 3 — Scale & Polish

### Step 3.1: Monte Carlo Sensitivity Analysis
**Feature Map**: Feature 7.2
**Effort**: Medium
- Define uncertainty ranges per parameter
- Run N simulations (500–5000) with random sampling
- Produce probability distribution of outcomes with percentile confidence intervals
- Celery task with progress tracking

### Step 3.2: Full Visualization Suite
**Feature Map**: Features 11.2, 11.5, 11.6
**Effort**: Large
- Outcome Probability Distribution (histogram/density)
- Influence Network Graph (D3 force-directed)
- Decision Comparison Matrix (side-by-side scenario branches)

### Step 3.3: Reporting & Export
**Feature Map**: Feature 12
**Effort**: Medium
- Executive Summary PDF (1–2 pages via WeasyPrint or ReportLab)
- Full Analysis Report PDF
- CSV/JSON data export
- Shareable read-only dashboard links

### Step 3.4: Scenario Templates & Case Studies
**Feature Map**: Feature 13
**Effort**: Medium
- ScenarioTemplate model with template_data JSONField
- 7 system templates pre-loaded (M&A, Legislative, Geopolitical, etc.)
- Case study library with BDM's published predictions
- Clone-to-workspace functionality

### Step 3.5: Prediction Tracking & Accuracy
**Feature Map**: Feature 14
**Effort**: Medium
- PredictionTracking model
- Record actual outcomes, calculate accuracy
- Brier score calibration
- User accuracy dashboard

### Step 3.6: What-If Scenario Branching Workflow
**Feature Map**: Feature 8.3
**Effort**: Medium
- Apply any recommendation as a branched scenario
- Pre-apply parameter changes, re-simulate
- Side-by-side outcome comparison
- Tight predict → recommend → test → refine loop

---

## Phase 4 — Growth

### Step 4.1: Collaboration Features
**Feature Map**: Feature 6.4
**Effort**: Large
- Share scenarios (view/comment/edit permissions)
- Collaborative stakeholder data entry
- Commenting and annotation system

### Step 4.2: API Access for Programmatic Use
**Feature Map**: Feature 8.4
**Effort**: Medium
- Public REST/GraphQL API with API key auth
- Webhook support for external triggers
- CSV/JSON import
- Rate limiting per subscription tier

### Step 4.3: Advanced Mobile Optimizations
**Feature Map**: Feature 15
**Effort**: Medium
- Full-screen mobile chat interface
- Touch-optimized visualizations (pinch-to-zoom)
- Bottom navigation bar
- Push notifications

### Step 4.4: Subscription Tier Enforcement
**Feature Map**: Feature 8.2
**Effort**: Medium
- Free tier limits (scenario count, basic predictions)
- Pro tier (unlimited, full engine, collaboration)
- Enterprise tier (API access, SSO, custom integrations)
- LLM token usage metering
- Stripe integration (keys already in .env)

### Step 4.5: RAG Layer
**Feature Map**: Feature 9.3
**Effort**: Large
- Index BDM's published work and game theory reference material
- RAG-enhanced LLM responses grounded in methodology
- User-uploadable reference documents

---

## Implementation Order (Recommended Build Sequence)

```
Phase 1 (MVP):
  1.1  Seed LookupValues ──────────────────────┐
  1.2  Extend User model ──────────────────────┤
  1.3  Scenario/Issue/Player models & CRUD ────┤── Foundation (parallel)
  1.8  Data quality validators ────────────────┘
  1.4  BDM Engine (core computation) ────────── Depends on 1.3
  1.5  Stakeholder Landscape Map ──────────────┐
  1.6  Scenario Summary Dashboard ─────────────┤── UI (parallel, after 1.4)
  1.7  Home Dashboard update ──────────────────┤
  1.9  Mobile responsive pass ─────────────────┘

Phase 2 (Intelligence):
  2.1  Coalition analysis ─────────────────────┐
  2.2  Sensitivity analysis (OAT) ─────────────┤── Engine extensions (parallel)
  2.7  Enhanced data quality ──────────────────┘
  2.3  Outcome engineering + recommendations ── Depends on 2.1, 2.2
  2.4  Conversational AI layer ──────────────── Can start parallel with 2.1
  2.5  Negotiation timeline viz ───────────────┐
  2.6  Tornado diagram viz ────────────────────┘── Viz (parallel, after 2.2)

Phase 3 (Scale & Polish):
  3.1  Monte Carlo sensitivity ────────────────┐
  3.4  Templates & case studies ───────────────┤── Parallel tracks
  3.5  Prediction tracking ────────────────────┘
  3.2  Full visualization suite ───────────────── After 3.1
  3.3  Reporting & export ─────────────────────── After 3.2
  3.6  What-if branching workflow ──────────────── After 3.3

Phase 4 (Growth):
  4.1  Collaboration ──────────────────────────┐
  4.2  Public API ─────────────────────────────┤── Parallel tracks
  4.4  Subscription enforcement ───────────────┘
  4.3  Mobile optimizations ───────────────────── After 4.1
  4.5  RAG layer ──────────────────────────────── After 4.2
```

---

## New Django Apps to Create

| App | Purpose | Phase |
|-----|---------|-------|
| `apps/scenarios` | Scenario, Issue, Player, PlayerPosition models + CRUD | 1 |
| `apps/engine` | SimulationRun, RoundResult, PredictionOutcome, Coalition, SensitivityResult, StrategicRecommendation + BDM engine | 1–2 |
| `apps/conversations` | ConversationSession, ConversationMessage + LLM integration | 2 |

---

## Key Technical Decisions

1. **BDM Engine**: Pure Python service module in `apps/engine/services.py`. Synchronous for small scenarios (<20 players), Celery task for larger ones and Monte Carlo.
2. **LLM**: Anthropic Python SDK with Claude. System prompts in DB. Streaming via SSE (Server-Sent Events) or Django Channels WebSocket.
3. **Visualizations**: D3.js for stakeholder map and network graph (need custom interactivity). Chart.js for simpler charts (tornado, histogram). Both are CDN-loadable, no build step needed.
4. **Real-time**: Django Channels with WebSocket for simulation progress updates and LLM streaming. Add `channels` and `daphne` to requirements.
5. **Frontend**: Stay with Django templates + Materialize CSS + vanilla JS/D3 for MVP. React frontend exists but is secondary — evaluate migration to React after Phase 2.
6. **PDF Generation**: WeasyPrint for HTML-to-PDF reports (cleaner than ReportLab for styled output).
