BACKBOARD API — ENGINEERING NOTES (READ BEFORE EDITING)

Backboard is a STATEFUL AI ORCHESTRATION API, not a stateless inference API.

Key concepts:
----------------
1. Assistants
   - Long-lived AI identities (system prompt + tools + RAG config).
   - Created once, reused across many sessions.
   - In this project: one assistant per agent (P1..P4) + optional shared assistant.

2. Threads
   - Stateful sessions attached to an assistant.
   - Preserve conversational context AND memory relevance.
   - Switching models does NOT reset thread context.
   - In this project: one thread per agent per match.

3. Messages (primary interaction)
   - Each message can independently specify:
     - model provider + model name
     - memory mode (Auto / Readonly / off)
     - tool availability
     - web search usage
   - This enables planner → actor routing per round.

Memory:
--------
- Memory is NOT just chat history.
- Backboard stores long-term, relevance-based memory automatically.

Memory modes:
- "Auto"     → read + write memory (use for planning & reflections)
- "Readonly" → read memory only (use for strict action commits)
- "off"      → ignore memory entirely (use for replay / debugging)

IMPORTANT:
- Private vs shared memory is achieved via DIFFERENT assistants or threads,
  NOT via flags.

Multi-model routing:
--------------------
- Models can be switched PER MESSAGE.
- Context and memory persist because they live in the thread.
- This enables:
    Planner (strong model) → Actor (cheap/fast model)
- If strict JSON fails, reroute once to planner.

Tools:
------
- Tools are FIRST-CLASS and schema-enforced.
- Each tool has:
    - name
    - JSON schema
    - real handler in Python
- Model may request tool calls; code executes them and returns results.
- Typical tools here:
    - get_public_state
    - get_player_state
    - list_legal_actions
    - propose_deal / accept / reject

RAG (Retrieval-Augmented Generation):
------------------------------------
- Documents are uploaded and indexed by Backboard.
- Retrieval happens automatically based on relevance.
- Used to ground agents in:
    - rules.md
    - strategy.md
- Prevents hallucinated rules.

Web Search:
-----------
- Optional per message.
- Enabled explicitly (e.g., web_search="Auto").
- Returns short snippets, not full pages.
- Must be rate-limited at the application level.

Error handling:
---------------
- API calls may fail (timeouts, rate limits, validation errors).
- All calls MUST:
    - have timeouts
    - be retry-safe
    - degrade gracefully (fallback action or replay mode)

Architectural invariants for AI Arena:
--------------------------------------
- Game engine must be deterministic and testable without Backboard.
- Backboard is used ONLY for agent cognition, memory, and tools.
- All Backboard interactions are logged to SQLite for replay.
- UI must visibly surface:
    - model routing
    - memory usage
    - tool calls
    - RAG/search usage

DO NOT:
-------
- Assume model switching resets context (it does not).
- Encode rules in prompts only (use RAG).
- Trust free-form outputs (always enforce schemas).

This file exists to isolate Backboard-specific logic behind a stable interface.