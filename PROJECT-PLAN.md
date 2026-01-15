### Project plan: AI Arena (Grid Heist)

This document is the **implementation plan and progress tracker**. We will update it continuously as we complete milestones (check off boxes, add notes, record decisions).

If `PROJECT-DETAILS.md` is “what we’re building,” this is “how we’re building it.”

---

### Operating principles (to keep MVP on track)

- **Deterministic engine**: all game logic must be deterministic and testable without Backboard.
- **Strict schemas**: agent outputs must be strict JSON; illegal actions must not crash the sim.
- **Observable Backboard usage**: memory/routing/tools/RAG/search must be visible in UI and logged in SQLite.
- **Demo reliability**: timeouts, fallbacks, and replay mode are mandatory.
- **UI clarity**: always prioritize readability; details are on-demand via the inspector drawer.

---

### Current decisions (locked for MVP)

- Board visibility: fully visible (no fog-of-war).
- Turn structure: simultaneous commit, paced for readability.
- Deals: negotiation + logging only (no enforcement).
- Collision rule: destination collisions block movement (all involved stay put).
- Steal rule: steal 1 key if available else steal 1 point (floored at 0).

---

### MVP milestones (checklist)

#### Milestone A — Repo scaffolding

- [x] Add `requirements.txt` (pydantic, pygame, etc.)
- [x] Add `.env.example` (Backboard config) - Note: .env files blocked by globalignore, will handle in setup
- [x] Create `src/ai_arena/` package skeleton
- [x] Update `README.md` with run/replay commands (no emojis)

Acceptance criteria:
- `python -m ai_arena.cli --help` works (even if stubbed).

#### Milestone B — Deterministic game engine (no AI)

- [x] Implement `engine/types.py` (pydantic models, enums, action schema)
- [x] Implement `engine/generate.py` (seeded board generation + spawns)
- [x] Implement `engine/rules.py` (legal action computation)
- [x] Implement `engine/reducer.py` (simultaneous resolution + events + rewards)
- [x] Add minimal unit tests (determinism, collisions, steal, vault open)

Acceptance criteria:
- A seed produces identical initial states across runs.
- A single “random bot” can play 15 rounds without exceptions.

#### Milestone C — Pygame UI v1 (engine-driven)

- [x] Implement full-screen window + scaling layout (board center, panels)
- [x] Draw board tiles + players + highlights
- [x] Scoreboard + event ticker
- [x] Basic pacing controls (pause, step, speed)

Acceptance criteria:
- You can watch a complete match (with dummy bots) at normal speed.

#### Milestone D — SQLite logging + replay

- [x] Implement `storage/schema.py` and `storage/db.py`
- [x] Log match config, per-round state snapshots, events, committed actions, rewards
- [x] Implement `storage/replay.py` to replay a completed match without Backboard

Acceptance criteria:
- A recorded match can be replayed deterministically in the UI.

#### Milestone E — Backboard client wrapper (integration point)

- [x] Implement `orchestrator/backboard_client.py` with:
  - model chat calls
  - tool calling support (as required by Backboard)
  - RAG retrieval calls
  - web search calls
- [x] Add timeouts/retries/backoff

Acceptance criteria:
- A single “ping” prompt roundtrip works and is logged.

#### Milestone F — Orchestrator v1 (plan → negotiate → commit → resolve → memory)

- [x] Implement `orchestrator/prompts.py` (stable templates + strict output rules)
- [x] Implement `orchestrator/routing.py` (planner vs actor model mapping)
- [x] Implement `orchestrator/runner.py` (full round loop)
- [x] Implement strict JSON parsing + fallback to `NOOP` on failures
- [x] Log all agent calls (phase, model, latency, request/response)

Acceptance criteria:
- 4 agents can play a full match end-to-end with stable pacing and logs.

#### Milestone G — Tools (real tool execution + UI)

- [ ] Implement `orchestrator/tools.py` tool registry + handlers:
  - get public state
  - get player state
  - list legal actions
  - propose/accept/reject deal
- [ ] Tool call loop: agent can call tools and then continue
- [ ] UI inspector shows tool calls per agent per round

Acceptance criteria:
- At least one tool call occurs during a match and is visible in UI and logs.

#### Milestone H — Negotiation + deals (logging only)

- [ ] Add negotiation phase messaging (1 message per agent per round)
- [ ] Implement deal objects (propose/accept/reject/expire)
- [ ] Show active deals in the UI (compact)
- [ ] Write negotiation transcript + deal snapshots to shared match memory

Acceptance criteria:
- Deals show up on screen and in memory summaries; no enforcement needed.

#### Milestone I — RAG

- [ ] Write `rag/corpus/rules.md` and `rag/corpus/strategy.md`
- [ ] Implement `rag/index.py` and `rag/retrieve.py`
- [ ] Integrate retrieval into planning calls (top-k snippets)
- [ ] Display retrieved snippets in inspector
- [ ] Log retrieval queries/results

Acceptance criteria:
- Agents consistently cite rules/tactics from retrieved snippets (or at least the snippets are clearly used in context).

#### Milestone J — Web search (rate-limited)

- [ ] Add per-agent search budget (e.g., 1 search every 3 rounds)
- [ ] Integrate into planning only
- [ ] Display search query + top snippets in inspector
- [ ] Log searches

Acceptance criteria:
- Search visibly triggers occasionally without slowing the demo excessively.

#### Milestone K — UI inspector drawer + pitch mode (polish that sells Backboard)

- [ ] Agent icon dock (click/select)
- [ ] Inspector drawer with tabs:
  - Summary, Memory, Routing, Tools, RAG/Search, Negotiation
- [ ] Scrollable + collapsible entries to avoid clutter
- [ ] Pitch Mode toggle that reduces text and shows feature callouts

Acceptance criteria:
- A judge can understand memory/routing/tools/RAG/search with 1–2 clicks and no clutter.

---

### Implementation order (recommended)

We will build in this order to keep feedback tight and avoid integration dead-ends:

1. Milestone A (scaffold)
2. Milestone B (engine)
3. Milestone C (UI v1 with dummy bots)
4. Milestone D (logging + replay)
5. Milestone E (Backboard client)
6. Milestone F (orchestrator basic)
7. Milestone G (tools)
8. Milestone H (negotiation/deals)
9. Milestone I (RAG)
10. Milestone J (search)
11. Milestone K (inspector + pitch mode polish)

---

### Risks and mitigations

- **Model output instability**: enforce strict JSON schema; fallback actions; escalation routing.
- **Latency variability**: pacing is UI-driven; allow speed adjustments; add timeouts.
- **API flakiness**: retries + replay mode ensures demo viability.
- **UI clutter**: single inspector drawer with tabs + collapsible sections.
- **Scope creep**: no deal enforcement, no fog-of-war, no web dashboard in MVP.

---

### Progress log (we update this as we go)

#### 2026-01-15

- [x] Created `PROJECT-DETAILS.md` (full spec)
- [x] Created `PROJECT-PLAN.md` (this plan + tracker)

#### 2026-01-15 (continued)

- [x] Completed Milestone A: repo scaffolding
  - Added requirements.txt with all dependencies
  - Created config.py with pydantic-settings
  - Created CLI stub with typer
  - Set up complete package structure under src/ai_arena/
  - Updated README.md with installation and usage instructions
- [x] Committed to GitHub

#### 2026-01-15 (later)

- [x] Completed Milestone B: deterministic game engine core
  - Added engine types and enums
  - Implemented seeded board generation and spawn layout
  - Implemented legal action computation
  - Implemented round resolution and events
  - Added engine unit tests

#### 2026-01-15 (even later)

- [x] Completed Milestone C: Pygame UI v1
  - Added a live demo loop with simple random agents
  - Implemented full-screen layout and basic rendering
  - Added scoreboard and event ticker
  - Added pacing controls (pause, step, speed)

Next up:
- [ ] Milestone G: Tools (real tool execution + UI)

