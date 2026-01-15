# AI Arena

Multi-agent competitive LLM reasoning using Backboard API.

## The Game: Grid Heist

AI Arena pits **4 different LLM agents** against each other in **Grid Heist**, a turn-based strategy game on a 9×9 grid. Each agent must navigate the board, collect treasures, open vaults, negotiate with opponents, and outmaneuver rivals to maximize their score.

### Game Mechanics

**Objective**: Collect the most points by the end of the match (default 15 rounds).

**The Board**:
- **9×9 grid** with various tile types
- **Fully visible** - no fog of war, all players can see everything
- **Deterministic** - same seed produces identical layouts for replayability

**Tile Types**:
- **Treasures** (+1, +2, or +3 points) - collect by standing on them
- **Keys** - needed to open vaults (collected like treasures)
- **Vaults** (+8 points) - high-value targets requiring a key to open
- **Scanners** - reveal information and grant small bonuses
- **Traps** - can be placed by players to block opponents

**Player Actions** (one per round):
- **MOVE** - navigate the grid in 4 directions
- **COLLECT** - pick up treasures or keys on your current tile
- **OPEN_VAULT** - spend a key for 8 points (if on a vault)
- **SCAN** - use scanner tiles for information
- **SET_TRAP** - place traps on adjacent tiles
- **STEAL** - take keys or points from adjacent players

**Strategic Elements**:
- **Negotiation Phase** - agents can propose deals, form alliances, or make threats
- **Memory** - each agent remembers past negotiations, betrayals, and opponent behavior
- **Multi-model routing** - different LLMs bring unique strategies and personalities
- **Tool usage** - agents can query game state, check legal actions, and propose deals

The game rewards both **strategic planning** (collecting keys for vaults) and **social dynamics** (negotiation, betrayal, cooperation). Watch as different LLM personalities emerge through their play styles!

## Quick Start

### Prerequisites

- Python 3.12+
- Backboard API key

### Installation

```bash
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root with your Backboard API key and settings:

```env
# Backboard API Configuration
# Get your API key from https://app.backboard.io
BACKBOARD_API_KEY=Enter Your API Key Here

# Backboard API settings (usually don't need to change)
BACKBOARD_BASE_URL=https://app.backboard.io/api
BACKBOARD_TIMEOUT=30

# Match Configuration
DEFAULT_MATCH_ROUNDS=15
DEFAULT_MATCH_SEED=demo_1

# UI Configuration
UI_FULLSCREEN=true
UI_DEFAULT_SPEED=1.0

# Backboard Model Routing (4 different models for demo)
P1_MODEL=gpt-4
P1_PROVIDER=openai
P2_MODEL=claude-3-5-sonnet
P2_PROVIDER=anthropic
P3_MODEL=gemini-1.5-pro
P3_PROVIDER=google
P4_MODEL=gpt-3.5-turbo
P4_PROVIDER=openai

# Web Search Configuration (set to true to enable)
ENABLE_WEB_SEARCH=false
SEARCH_BUDGET_PER_AGENT=1
SEARCH_COOLDOWN_ROUNDS=3

# Safety limits
MAX_LLM_CALLS_PER_MATCH=250
```

### Running a Match

Run a live 15-round match with 4 AI agents:

```bash
python -m ai_arena.cli run
```

Run a Backboard-powered match and log to SQLite:

```bash
python -m ai_arena.cli run_backboard --seed demo_1 --rounds 10
```

Run with custom seed and rounds:

```bash
python -m ai_arena.cli run --seed demo_1 --rounds 20
```

### Replaying a Match

Replay a previously recorded match:

```bash
python -m ai_arena.cli replay match_12345
```

Replay at faster speed:

```bash
python -m ai_arena.cli replay match_12345 --speed 2.0
```

### Demo Checklist

See `DEMO-CHECKLIST.md` for a full demo flow and UI controls.

## Project Structure

- `src/ai_arena/engine/` - Deterministic game logic (Grid Heist)
- `src/ai_arena/orchestrator/` - Multi-agent orchestration with Backboard
- `src/ai_arena/rag/` - Rules and strategy retrieval
- `src/ai_arena/storage/` - SQLite logging and replay
- `src/ai_arena/ui/` - Pygame visualization
