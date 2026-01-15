# Grid Heist Rules (RAG Corpus)

## Objective
- Maximize score over the match length.

## Board
- 9x9 grid, fully visible.
- Tiles: empty, treasure_1, treasure_2, treasure_3, key, vault, scanner, trap.

## Actions (one per round)
- MOVE (N/E/S/W)
- COLLECT (treasure/key on current tile)
- OPEN_VAULT (if on vault and has a key, +8 points, consumes 1 key)
- SCAN (if on scanner tile; small reward)
- SET_TRAP (adjacent empty tile)
- STEAL (adjacent player)
- NOOP (do nothing)

## Collisions
- If multiple players attempt to move to the same destination, all those moves fail.

## Steal Rule
- If target has a key: steal 1 key.
- Else: steal 1 point (target score floored at 0).

## Traps
- Set by players via SET_TRAP.
- If a player steps on a trap, they become trapped_for=1 (lose next action).

## Scoring
- Treasure_1: +1
- Treasure_2: +2
- Treasure_3: +3
- Vault: +8 (requires a key)
