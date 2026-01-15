# Grid Heist Rules (RAG Corpus)

## Objective
- [R1] Maximize score over the match length.

## Board
- [R2] 9x9 grid, fully visible.
- [R3] Tiles: empty, treasure_1, treasure_2, treasure_3, key, vault, scanner, trap.

## Actions (one per round)
- [R4] MOVE (N/E/S/W)
- [R5] COLLECT (treasure/key on current tile)
- [R6] OPEN_VAULT (if on vault and has a key, +8 points, consumes 1 key)
- [R7] SCAN (if on scanner tile; small reward)
- [R8] SET_TRAP (adjacent empty tile)
- [R9] STEAL (adjacent player)
- [R10] NOOP (do nothing)

## Collisions
- [R11] If multiple players attempt to move to the same destination, all those moves fail.

## Steal Rule
- [R12] If target has a key: steal 1 key.
- [R13] Else: steal 1 point (target score floored at 0).

## Traps
- [R14] Set by players via SET_TRAP.
- [R15] If a player steps on a trap, they become trapped_for=1 (lose next action).

## Scoring
- [R16] Treasure_1: +1
- [R17] Treasure_2: +2
- [R18] Treasure_3: +3
- [R19] Vault: +8 (requires a key)
