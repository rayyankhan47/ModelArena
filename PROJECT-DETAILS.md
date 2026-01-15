### Project: AI Arena (Grid Heist)

This document is the **full specification** for the project: what we are building, how it works, and what “meaningful Backboard usage” looks like end-to-end. It’s intended to be stable and referenceable; we’ll only change it when the spec changes.

---

### Goals and judging alignment

- **Primary goal (most weight)**: demonstrate **Backboard-native multi-agent orchestration** clearly and unambiguously:
  - multi-model routing
  - persistent memory (private per agent + shared match memory)
  - tool execution (real tools, not “pretend”)
  - RAG (rulebook/strategy retrieval)
  - web search (rate-limited, purposeful)
- **Secondary goal**: originality via a competitive multi-agent arena with negotiation and evolving strategies.
- **Tertiary goal**: usefulness framed as a reusable template for multi-agent competitive simulations and research.
- **Reliability goal**: the project must demo smoothly even if an API call fails (timeouts, fallbacks, replay mode).

---

### Core framing (what the project “is”)

**AI Arena** is a live, observable multi-agent competition where **4 different LLM agents** play a deterministic strategy game (**Grid Heist**) over multiple rounds. The game is the vehicle; the point is showcasing how Backboard enables:

- **multi-agent statefulness** (private and shared memory),
- **model routing** (planner vs actor models, with optional escalation),
- **tool-based interaction** with an environment,
- **retrieval** (RAG) of rules/strategies,
- and **web search** (controlled) to augment planning.

We surface all of these in a clean UI so judges can literally see them happening.

---

### Stack (MVP)

- **Language**: Python 3.12+
- **Rendering**: `pygame` (full-screen)
- **Validation**: `pydantic` (strict schemas for actions and logs)
- **Persistence**: SQLite (via stdlib `sqlite3`)
- **Concurrency**: `asyncio` (parallel planning/commit phases)
- **Backboard**: via a thin `BackboardClient` wrapper in `src/ai_arena/orchestrator/backboard_client.py`

---

### Repo structure (target)

```text
backboard-challenge/
  README.md
  PROJECT-DETAILS.md
  PROJECT-PLAN.md
  requirements.txt
  .env.example

  src/
    ai_arena/
      config.py
      cli.py

      engine/
        types.py
        generate.py
        rules.py
        reducer.py

      orchestrator/
        prompts.py
        routing.py
        tools.py
        backboard_client.py
        runner.py

      rag/
        corpus/
          rules.md
          strategy.md
        index.py
        retrieve.py

      storage/
        schema.py
        db.py
        logger.py
        replay.py

      ui/
        pygame_app.py
        render.py
        assets/
```

---

### Game specification: Grid Heist (fully visible board)

#### Board

- **Size**: 9×9 grid
- **Visibility**: fully visible (no fog-of-war)
- **Match seed**: deterministic seed determines initial layout for repeatable demos/replays

#### Tile types

- **Empty**
- **Treasure**: +1 / +2 / +3 points (collected by standing on tile and using `COLLECT`)
- **Key**: increases `keys` inventory by 1 (collected with `COLLECT`)
- **Vault**: redeemable by `OPEN_VAULT` if player has at least 1 key; awards **+8 points** and consumes 1 key
- **Scanner**: `SCAN` yields an event (and optionally a small +1 point bonus to make it worth it even without fog-of-war)
- **Trap**: placed by `SET_TRAP`, triggered when stepped on; effect: `trapped_for = 1` (lose next action) or equivalent simple penalty (we will pick one and keep it consistent)

#### Players (4)

Each player has:

- `player_id`
- `pos` (x,y)
- `score` (int)
- `keys` (int)
- `trapped_for` (int, turns remaining unable to act)

Spawn points: fixed corners (or fixed spread positions) to keep it simple and reproducible.

#### Actions (strict JSON)

One action per round per player (except when trapped; trapped players are forced to `NOOP`).

- `MOVE` (N/E/S/W)
- `COLLECT` (treasure/key on current tile)
- `OPEN_VAULT` (if on vault and has key)
- `SCAN` (if on scanner)
- `SET_TRAP` (place trap on adjacent tile)
- `STEAL` (if adjacent to a target player)
- `NOOP` (fallback / illegal action / trapped)

Negotiation is represented separately as a message/deal operations during the negotiation phase, not as a board action.

#### Collision rule (simplest)

If multiple players attempt to enter the same destination tile in the same round:

- **All involved moves fail** (players remain in place)
- Engine emits `COLLISION_BLOCKED` event

This is deterministic, easy to implement, and easy to explain.

#### Steal rule (simple + strategic)

If `STEAL(target)` is legal (target adjacent):

- If target has `keys > 0`: transfer **1 key** from target to thief
- Else: transfer **1 point** from target to thief (target score floored at 0)

Engine emits `STEAL_SUCCESS` or `STEAL_FAIL` events.

#### Illegal action handling

- Engine validates each action.
- Illegal actions become `NOOP` and emit `ILLEGAL_ACTION` event.
- Optional: small penalty (e.g., reward -1) to discourage nonsense; we’ll decide in implementation and keep consistent.

---

### Match flow (phases)

Each round is executed with a consistent script (good for demos and logs):

#### Phase A — Snapshot

- Freeze `public_state` (board, positions, scores, tiles, active deals).
- Prepare per-agent `private_state` (inventory/status, plus any private artifacts if we add them later).

#### Phase B — Planning (private, parallel)

Per agent:

- Provide state + private memory summary + shared match memory summary.
- Optionally include RAG snippets and web search snippets (controlled).
- Agent outputs a structured **Plan artifact** (not the final action).

#### Phase C — Negotiation (public, sequential)

Each agent may emit at most **one short message** publicly and optionally propose/accept/reject deals.

- Deals are **not enforced** by the engine in MVP.
- Deals are **logged** and written to shared match memory.

#### Phase D — Commit actions (private, parallel)

Each agent outputs a strict JSON `Action`.

#### Phase E — Resolve (engine)

Engine applies simultaneous resolution, emits events, computes rewards.

#### Phase F — Memory writeback

For each agent:

- Append private “round recap + learned notes” to private memory.
- Append a canonical round recap to shared match memory.

---

### Backboard feature usage (what is “meaningful”)

#### Multi-model routing

Per agent per round:

- **Planner call**: stronger model (strategy / negotiation stance)
- **Actor call**: faster/cheaper model (must output strict action JSON)

Optional escalation:

- If actor fails strict JSON or violates schema twice, reroute once to planner model.

UI must show per call:

- model identifier
- phase (PLAN/NEGOTIATE/COMMIT)
- latency (ms)
- whether rerouting happened

#### Persistent memory

We maintain:

- **Private memory per agent**: strategy, opponent models, betrayal history, heuristics, “what worked.”
- **Shared match memory**: negotiation transcript + round recaps + active deals summary.

UI must show:

- “Memory summary used this round” for the selected agent
- last 2–3 private memory entries for that agent
- last shared match recap (or a short shared summary)

#### Tools

We support real tool calls with schemas and real handler execution. Minimal tool set:

- `get_public_state()`
- `get_player_state(player_id)` (private state)
- `list_legal_actions(player_id)`
- `propose_deal(to_player_id, terms)`
- `accept_deal(deal_id)` / `reject_deal(deal_id)`

UI must show:

- tool call list for the selected agent (name + concise result)
- expand a tool call to see args/result JSON

#### RAG

We index and retrieve from:

- `src/ai_arena/rag/corpus/rules.md`
- `src/ai_arena/rag/corpus/strategy.md`

Usage:

- Planning phase retrieves relevant snippets given the current state (“I am near a vault but no key” etc.).
- The goal is to prevent hallucinated rules and to drive consistent tactical reasoning.

UI must show:

- top retrieved snippets used in planning (top 1–3, truncated)

#### Web search (controlled)

Search is allowed only in planning and is rate-limited:

- max 1 search per agent every N rounds (N chosen in implementation, likely 3)
- max 3 results

UI must show:

- query and short result snippets (top 1–2)

---

### Prompting strategy (high-level)

We will keep prompts stable and enforce strict outputs:

- **System**: identity (Player P1..P4), objective, strictness rules, tool policy.
- **Rules capsule**: brief rules, scoring, action schema constraints.
- **State capsule**: JSON snapshot of board/players/tiles plus recent events.
- **Memory capsule**: private and shared summaries (short).
- **RAG/Search capsule**: retrieved/search snippets with clear provenance.

Critical constraints:

- Action commit output must be **strict JSON** matching the `Action` schema.
- Negotiation output must be short and separated from action commit.

---

### Logging, persistence, and replay

We log everything necessary to:

- debug agent behavior,
- replay matches without Backboard,
- generate pitch screenshots and “proof” of Backboard usage.

SQLite tables (conceptually):

- matches (config, seed)
- rounds (state snapshot, committed actions, rewards)
- events (engine outputs)
- agent_calls (requests/responses per phase, model, latency)
- tool_calls (name, args, result)
- memory_summaries (per agent + shared)

Replay mode:

- `replay` uses stored round states/events to drive the UI with no external calls.

---

### UI specification (Pygame, full-screen, clean)

Principle: **always show the game**, show Backboard details **on demand** via a single inspector drawer.

#### Always-visible areas

- **Center**: 9×9 board + tokens + tile icons
- **Top bar (small)**: Round, Phase, and a tiny “activity strip” showing if any agent used Tools/RAG/Search this round
- **Right panel (compact)**: scoreboard + active deals (truncated)
- **Bottom ticker (compact)**: last ~6 events

#### Agent icons (dock)

- 4 colored icons (or logos) in a dock (top-left).
- Clicking an icon opens the inspector for that agent.

#### Inspector drawer (single, not duplicated per agent)

One drawer that shows details for the selected agent. It has tabs:

- Summary (default)
- Memory
- Routing
- Tools
- RAG/Search
- Negotiation

Only one tab is visible at a time to avoid clutter.

#### Controls

- `Space`: pause/resume
- `Right Arrow`: step to next phase/round
- `+/-`: adjust speed
- `Esc`: close drawer
- `1..4`: quick-select agent in drawer
- `P`: “Pitch Mode” toggle

#### Pacing (so simultaneous commit is readable)

Even with parallel commit, the UI will stage reveals:

- show “commits received” briefly per agent
- then show resolution/events
- default speed targets human-readable (not ultra fast), adjustable by hotkeys

#### Pitch Mode

Pitch Mode reduces on-screen text. It keeps:

- board
- scoreboard
- a single-line “feature callout” banner when Tools/RAG/Search/Memory writeback happens

The inspector remains available on click.

---

### MVP definition of done

The MVP is done when:

- A full-screen Pygame window runs a 15-round match with 4 agents.
- Each round executes the full phase script (plan → negotiate → commit → resolve → memory).
- Agents are routed across at least two models (planner vs actor), visible in UI.
- Tool calls work end-to-end and are visible in UI.
- RAG retrieval works and is visible in UI.
- Web search works (rate-limited) and is visible in UI.
- SQLite logs allow replay without any Backboard calls.

---

### Non-goals (for MVP)

- Deal enforcement/penalties (we only log and surface in memory/UI).
- Fog-of-war.
- Large-scale training / reinforcement learning loops.
- A web dashboard (Pygame window is the primary visualization).

