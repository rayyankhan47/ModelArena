## Demo Checklist

### Pre-Demo Setup
- Confirm `.env` has `BACKBOARD_API_KEY`
- Verify dependencies: `pip install -r requirements.txt`
- Choose a seed for reproducibility (e.g., `demo_1`)
- Ensure internet access for Backboard API

### Live Demo (Backboard)
- Start a Backboard match: `python -m ai_arena.cli run_backboard --seed demo_1 --rounds 10`
- Confirm match logs are written to `ai_arena.db`

### Replay Demo (Pygame)
- Replay the logged match: `python -m ai_arena.cli replay <match_id>`
- Use controls:
  - Space: pause/resume
  - Right arrow: step
  - +/-: speed
  - T: toggle tool call list

### UI Features to Show
- Agent dock (clickable P1–P4)
- Inspector drawer (I to toggle)
- Tab switching (Tab)
- Pitch mode (P)
- Deal list in sidebar

### Troubleshooting
- If Backboard fails, use replay mode for the demo
- If match_id not found, run a short match to generate logs
