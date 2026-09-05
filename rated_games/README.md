# MilkyWay Rated Game Forensics Corpus

This directory contains forensic investigations, game logs, and counterfactual model replays for all AI Chessathon rated game losses.

## Purpose
Generic benchmark positions (WAC, STS, ECM) fail to capture the specific failure modes that arise in real tournament play:
- Clock pressure and time allocation collapse
- Model policy vs. tactical search interactions
- Queen-checking defensive evasion
- Repetition handling under losing evaluations

Every rated game loss is ingested here to establish causal attribution and build targeted regression suites.

## Corpus Structure
- `round_20_larpmaxx/`: Round 20 loss (MW-0.2, Sicilian Closed, move 19 blunder `g4??`).
- `round_25_neomatica/`: Round 25 loss (MW-R25-POLICY, Pirc Defence, 134 moves, early clock exhaustion, moves 15 `Rb1` and 18 `Ra1`).

## Protocol for Ingesting Rated Losses
1. Freeze exact build and model artifact in `build_manifest.json`.
2. Parse PGN and engine platform log into `positions.jsonl`.
3. Annotate all decisions with offline Stockfish MultiPV 5 (100k+ nodes).
4. Run counterfactual replays:
   - Frozen MW-0.2 stateful replay
   - Experimental code with policy disabled (`MILKYWAY_ROOT_POLICY=0`)
5. Trace root search depth progression and search ablations on critical positions.
6. Synthesize attribution report in `analysis.md`.
