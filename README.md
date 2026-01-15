# AI Arena

Multi-agent competitive LLM reasoning using Backboard API.

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
