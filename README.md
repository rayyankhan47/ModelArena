# AI Arena

Multi-agent competitive LLM reasoning using Backboard API.

## Quick Start

### Prerequisites

- Python 3.12+
- Backboard API key

### Installation

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Backboard API key
```

### Running a Match

Run a live 15-round match with 4 AI agents:

```bash
python -m ai_arena.cli run
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

## Project Structure

- `src/ai_arena/engine/` - Deterministic game logic (Grid Heist)
- `src/ai_arena/orchestrator/` - Multi-agent orchestration with Backboard
- `src/ai_arena/rag/` - Rules and strategy retrieval
- `src/ai_arena/storage/` - SQLite logging and replay
- `src/ai_arena/ui/` - Pygame visualization
