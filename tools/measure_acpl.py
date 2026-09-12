# ruff: noqa: E402, E501
"""Standardized 100-position ACPL benchmark suite for MilkyWay.

Measures Average Centipawn Loss (ACPL) against Stockfish 18 oracle across
four balanced phases (25 Openings, 25 Tactics, 25 Middlegames, 25 Endgames)
using this project's explicit evaluation cap (±1000 cp).
Target: Mean ACPL <= 40 cp.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import chess
import chess.engine

from baselines.stockfish.agent import find_stockfish_binary
from harness.sandbox import local


@dataclass(frozen=True)
class ACPLPosition:
    id: str
    category: str
    fen: str
    description: str


# 100 Standardized Positions: 25 Opening, 25 Tactical, 25 Middlegame, 25 Endgame
ACPL_TEST_SUITE: tuple[ACPLPosition, ...] = (
    # =========================================================================
    # 1-25: OPENINGS (Plies 6-14 from master theory)
    # =========================================================================
    ACPLPosition("open_01", "opening", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "Starting position"),
    ACPLPosition("open_02", "opening", "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3", "Ruy Lopez / Italian branching point"),
    ACPLPosition("open_03", "opening", "rnbqkb1r/pp2pppp/3p1n2/8/3NP3/8/PPP2PPP/RNBQKB1R w KQkq - 1 5", "Open Sicilian Najdorf"),
    ACPLPosition("open_04", "opening", "rnbqkb1r/ppp2ppp/4pn2/3p4/2PP4/2N5/PP2PPPP/R1BQKBNR w KQkq - 0 4", "Queen's Gambit Declined"),
    ACPLPosition("open_05", "opening", "r1bqkb1r/pp2pppp/2np1n2/8/3NP3/2N5/PPP2PPP/R1BQKB1R w KQkq - 1 6", "Classical Sicilian"),
    ACPLPosition("open_06", "opening", "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4", "Italian Game Two Knights"),
    ACPLPosition("open_07", "opening", "rnbqkb1r/pp1ppppp/5n2/2p5/2PP4/8/PP2PPPP/RNBQKBNR w KQkq c6 0 3", "Benoni / English Defense"),
    ACPLPosition("open_08", "opening", "rnbqk2r/ppp1bppp/4pn2/3p4/2PP4/5NP1/PP2PPBP/RNBQK2R b KQkq - 1 5", "Catalan Opening"),
    ACPLPosition("open_09", "opening", "r1bqk2r/pp2bppp/2n1pn2/2pp4/2PP4/2N1PN2/PP2BPPP/R1BQK2R w KQkq - 4 7", "Tarrasch Defense"),
    ACPLPosition("open_10", "opening", "rnbq1rk1/ppp1ppbp/3p1np1/8/2PPP3/2N2N2/PP2BPPP/R1BQK2R b KQ - 3 6", "King's Indian Classical"),
    ACPLPosition("open_11", "opening", "rnbqkb1r/pp3ppp/4pn2/2pp4/2PP4/2N1PN2/PP3PPP/R1BQKB1R w KQkq - 2 6", "Nimzo / Queen's Gambit tension"),
    ACPLPosition("open_12", "opening", "r1bq1rk1/pppnbppp/4p3/3n2B1/3P4/2N1PN2/PP3PPP/R2QKB1R w KQ - 0 8", "French Rubinstein variation"),
    ACPLPosition("open_13", "opening", "r1bqkb1r/pp3ppp/2np1n2/4p3/4P3/1NN5/PPP1BPPP/R1BQK2R b KQkq - 1 7", "Sicilian Scheveningen setup"),
    ACPLPosition("open_14", "opening", "r1bqkb1r/pp2nppp/2n1p3/2ppP3/3P4/N1P2N2/PP3PPP/R1BQKB1R b KQkq - 4 6", "French Advance pawn chain"),
    ACPLPosition("open_15", "opening", "rnbq1rk1/pppp1ppp/4pn2/8/1bPP4/4PN2/PP1N1PPP/R1BQKB1R b KQ - 0 5", "Bogo-Indian Defense"),
    ACPLPosition("open_16", "opening", "rnbqkb1r/ppp2ppp/5n2/3p2B1/3P4/2N5/PP2PPPP/R2QKBNR b KQkq - 1 5", "Queen's Gambit Orthodox"),
    ACPLPosition("open_17", "opening", "r1b1k2r/ppq1bppp/2nppn2/8/3NP3/2N1BP2/PPP1B1PP/R2QK2R w KQkq - 1 9", "Sicilian Richter-Rauzer"),
    ACPLPosition("open_18", "opening", "r1bq1rk1/pp1nbppp/2p1pn2/3p4/2PP4/2N1PN2/PP2BPPP/R1BQ1RK1 w - - 4 8", "Queen's Gambit Lasker Defense"),
    ACPLPosition("open_19", "opening", "r1bqkb1r/pp2pppp/2n5/1B1p4/3P4/5N2/PPP2PPP/R1BQK2R b KQkq - 1 7", "Caro-Kann Advance / Classical"),
    ACPLPosition("open_20", "opening", "rnbq1rk1/pp2bppp/4p3/2pn4/8/2N2NP1/PP1PPPBP/R1BQ1RK1 w - - 0 8", "English Opening Neo-Catalan"),
    ACPLPosition("open_21", "opening", "r1bq1rk1/ppp1bppp/2np1n2/4p3/4P3/2NP1N2/PPP1BPPP/R1BQ1RK1 w - - 0 7", "Four Knights Spanish variation"),
    ACPLPosition("open_22", "opening", "rnbqkb1r/pp2pppp/3p1n2/8/3NP3/2N5/PPP2PPP/R1BQKB1R b KQkq - 2 5", "Sicilian Classical Dragon transition"),
    ACPLPosition("open_23", "opening", "r1bqkb1r/1p3ppp/p1np1n2/4p3/4P3/1NN5/PPP1BPPP/R1BQ1RK1 b kq - 1 8", "Najdorf with Be2"),
    ACPLPosition("open_24", "opening", "rnb1k2r/pp2qppp/2p1pn2/3p4/2PP4/2N1PN2/PP3PPP/R2QKB1R w KQkq - 0 8", "Slav Defense quiet development"),
    ACPLPosition("open_25", "opening", "r1bq1rk1/ppp2ppp/2n1pn2/3p4/2PP4/2N2NP1/PP2PPBP/R1BQK2R w KQ - 0 7", "Grunfeld / Catalan central clash"),

    # =========================================================================
    # 26-50: TACTICAL (Combinations, sacrifices, forks, pins, attacks)
    # =========================================================================
    ACPLPosition("tact_01", "tactical", "r1b2rk1/pp3ppp/2n1p3/q7/2BP4/5N2/PP1Q1PPP/R3K2R w KQ - 3 13", "Pin and central pressure"),
    ACPLPosition("tact_02", "tactical", "r1bq1rk1/pp3ppp/2n5/3np3/8/2NB4/PPP2PPP/R1BQ1RK1 w - - 0 11", "Bxh7 Greek gift tactical tension"),
    ACPLPosition("tact_03", "tactical", "r2q1rk1/1b2bppp/p2p1n2/1p2p3/3NP3/P1NP3P/1P3PP1/R1BQR1K1 w - - 0 14", "Open e-file tactical opportunity"),
    ACPLPosition("tact_04", "tactical", "r1bqr1k1/ppp2ppp/2n5/8/2BP4/5N2/PP1Q1PPP/R4RK1 w - - 1 13", "Bishop pressure on f7 with knight jumps"),
    ACPLPosition("tact_05", "tactical", "r1b1k2r/ppppqppp/2n5/4n3/1bP5/2N2N2/PP1BPPPP/R2QKB1R w KQkq - 0 8", "Threat of Nd3# cramped pinning defense"),
    ACPLPosition("tact_06", "tactical", "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", "Kiwipete multi-piece tactical clash"),
    ACPLPosition("tact_07", "tactical", "r1bqk2r/pppp1ppp/2n5/4P3/2B5/5Q2/PPP2PPP/RN2K2R b KQkq - 0 8", "Defending Qf7# mating threat"),
    ACPLPosition("tact_08", "tactical", "4r1k1/5ppp/8/8/8/8/4RPPP/6K1 w - - 0 1", "Rook pin conversion"),
    ACPLPosition("tact_09", "tactical", "r1b1kb1r/pppp1ppp/8/4q3/4n3/2N5/PPP1BPPP/R1BQK2R w KQkq - 0 8", "Pinned piece on e-file tactical refutation"),
    ACPLPosition("tact_10", "tactical", "6k1/5ppp/8/8/8/8/1r3PPP/R5K1 w - - 0 1", "Back-rank mate escape requirement"),
    ACPLPosition("tact_11", "tactical", "r1b2rk1/2q1bppp/p2pp3/1p4P1/3BPP1Q/2N5/PPP4P/2KR3R w - - 0 17", "Opposite-side castling pawn storm"),
    ACPLPosition("tact_12", "tactical", "r2q1rk1/1pp2ppp/p1np4/4p3/2B1P1b1/2NPPN2/PPP1Q1PP/R4RK1 w - - 1 11", "Pin on knight and kingside counterplay"),
    ACPLPosition("tact_13", "tactical", "2r2rk1/1b1nbppp/pq1pp3/1p6/3NPP2/P1N5/1PP1QBPP/R4R1K w - - 1 17", "Discovered attack on queen with Ne6"),
    ACPLPosition("tact_14", "tactical", "r1bq1rk1/ppp2ppp/2n5/3p4/2PPn3/2PB1N2/P4PPP/R1BQK2R w KQ - 0 9", "Central sacrifice / knight tension"),
    ACPLPosition("tact_15", "tactical", "r2qkb1r/pp1n1ppp/2p1pn2/5b2/2BP4/2N1PN2/PP3PPP/R1BQ1RK1 w kq - 2 8", "Queenside bishop outpost and central break"),
    ACPLPosition("tact_16", "tactical", "r1b2rk1/pp1nqppp/2p1pn2/3p4/2PP4/2NBPN2/PP3PPP/R2Q1RK1 w - - 0 10", "Central e4 break tactical lever"),
    ACPLPosition("tact_17", "tactical", "r1bqr1k1/pp3ppp/2n5/3p4/3N4/2PB4/P1P2PPP/R2Q1RK1 w - - 1 13", "Isolated queen's pawn tactical assault"),
    ACPLPosition("tact_18", "tactical", "r4rk1/1pq1bppp/p1np1n2/4p3/2P1P3/1PN1BP2/P3B1PP/R2Q1RK1 w - - 1 13", "Knight outpost on d5 tactically dominant"),
    ACPLPosition("tact_19", "tactical", "r2qr1k1/1p3ppp/p1np4/3N4/4n3/1N1Q4/PPP2PPP/R3R1K1 b - - 1 15", "Rook fork and discovered attack defense"),
    ACPLPosition("tact_20", "tactical", "2rq1rk1/pb1n1pbp/1p1pp1p1/8/2PPn3/1PN2NP1/PB2QPBP/2RR2K1 b - - 1 13", "Knight trade on c3 opening tactics"),
    ACPLPosition("tact_21", "tactical", "r1b2rk1/pp2qppp/2n1pn2/2pp4/2PP4/2N1PN2/PP1QBPPP/R4RK1 w - - 0 10", "Pawn break cxd4 opening lines"),
    ACPLPosition("tact_22", "tactical", "r1bq1rk1/pp1nbp1p/4p1p1/3pP3/2pP4/2P1PN2/PPBN2PP/R2Q1RK1 w - - 0 13", "Kingside pawn lever f4-f5 preparation"),
    ACPLPosition("tact_23", "tactical", "r2q1rk1/1b2bppp/p1np4/1p1Np3/4P3/1B2BP2/PPP3PP/R2QK2R b KQ - 1 13", "Hanging knight on d5 dynamic tactical reply"),
    ACPLPosition("tact_24", "tactical", "r1bq1rk1/pp2ppbp/2np1np1/8/3NP3/2N1BP2/PPP3PP/R2QKB1R w KQ - 1 9", "Yugoslav attack preparation 9.Bc4"),
    ACPLPosition("tact_25", "tactical", "r2qk2r/pb1nbppp/1p1ppn2/2p5/2PP4/1PN1PN2/PB2BPPP/R2QK2R w KQkq - 2 9", "Double fianchetto central break d5"),

    # =========================================================================
    # 51-75: COMPLEX MIDDLEGAMES (Quiet, closed, high-branching, maneuvering)
    # =========================================================================
    ACPLPosition("mid_01", "middlegame", "r1b2rk1/1pq1bppp/p1nppn2/8/3NPP2/2N1B3/PPP1B1PP/R2Q1R1K w - - 0 11", "Scheveningen quiet maneuvering"),
    ACPLPosition("mid_02", "middlegame", "r2q1rk1/1p2bppp/p1np1n2/2p1p3/P1B1P1b1/2NP1N2/1PP2PPP/R1BQ1RK1 w - - 1 9", "Italian quiet pin maneuvering"),
    ACPLPosition("mid_03", "middlegame", "r1rq2k1/pb1nbppp/1p2pn2/2pp4/2PP4/1PN1PNP1/PB2QPBP/2RR2K1 b - - 1 13", "Catalan / QID solid pawn skeleton"),
    ACPLPosition("mid_04", "middlegame", "2rr2k1/1p2bppp/p1q1pn2/3p4/2PP4/1PN1PN2/PB3PPP/2RQR1K1 w - - 0 14", "Symmetrical pawn structure positional bind"),
    ACPLPosition("mid_05", "middlegame", "r1b1k2r/pp2bppp/2n1p3/2ppP3/3P4/2N2N2/PPP1BPPP/R2QK2R w KQkq - 0 9", "French Advance locked center maneuvering"),
    ACPLPosition("mid_06", "middlegame", "r2q1rk1/1ppnbppp/p2p1n2/4p3/3PP3/2N1BN2/PPP1QPPP/R4RK1 b - - 0 9", "KID closed pawn structure"),
    ACPLPosition("mid_07", "middlegame", "rnb1k2r/pp3ppp/4pn2/2pp4/1bPP4/2N1PN2/PP3PPP/R1BQKB1R w KQkq - 2 6", "Nimzo closed tension"),
    ACPLPosition("mid_08", "middlegame", "r2q1rk1/pp1b1ppp/2n1pn2/2pp4/2PP4/2NBPN2/PP3PPP/R1BQ1RK1 w - - 0 8", "Closed Tarrasch center"),
    ACPLPosition("mid_09", "middlegame", "r1bqk2r/pppp1ppp/2n5/4p3/1bB1n3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 0 6", "Open high-branching tactical center"),
    ACPLPosition("mid_10", "middlegame", "r1bqkb1r/pp3ppp/2n1pn2/2pp4/2PP4/2N1PN2/PP3PPP/R1BQKB1R w KQkq - 0 6", "Rich central pawn tension (38 moves)"),
    ACPLPosition("mid_11", "middlegame", "r2q1rk1/pb1nbppp/1p2pn2/2pp4/2PP4/1PN1PN2/PB2BPPP/R2Q1RK1 w - - 0 10", "Wide piece mobility positional branching"),
    ACPLPosition("mid_12", "middlegame", "r1b1k2r/pp3ppp/1qn1pn2/2bp4/2PP4/2N1BN2/PP3PPP/R2QKB1R w KQkq - 3 8", "Multiple hanging pieces and choices"),
    ACPLPosition("mid_13", "middlegame", "r3k2r/ppp2ppp/2n1b3/3np3/8/2NB4/PPP2PPP/R1B2RK1 w kq - 0 11", "Queens exchanged early active minors"),
    ACPLPosition("mid_14", "middlegame", "r4rk1/pp1n1ppp/2p1pn2/8/3P4/2N2B2/PPP2PPP/R4RK1 w - - 0 14", "Quiet queenless grind with IQP"),
    ACPLPosition("mid_15", "middlegame", "2r2rk1/pp1b1ppp/4pn2/8/3N4/1P2P3/P3BPPP/2RR2K1 w - - 1 17", "Open c/d files queenless endgame transition"),
    ACPLPosition("mid_16", "middlegame", "r1b2rk1/pp2ppbp/2np1np1/8/2PNP3/2N1B3/PP2BPPP/R4RK1 b - - 3 10", "Dragon structure queenless squeeze"),
    ACPLPosition("mid_17", "middlegame", "r1b4r/p3k3/1p2p3/B1p3pp/P1P4P/4P1P1/3K1P2/R1R5 b - - 0 24", "Unbalanced pawn structure minor pieces"),
    ACPLPosition("mid_18", "middlegame", "8/p6r/k7/3pQ1np/2NP3p/5P2/4KP2/n7 w - - 6 38", "Complex queen and piece active endgame"),
    ACPLPosition("mid_19", "middlegame", "1n6/4p3/3k1nr1/1B6/7p/3K1P1N/R7/4b2R b - - 3 39", "Materially unbalanced open middlegame"),
    ACPLPosition("mid_20", "middlegame", "r4rk1/1pp2ppp/p1np4/4p3/4P1b1/1BNPPN2/PPP3PP/R4RK1 b - - 0 12", "Italian structure knight maneuvering"),
    ACPLPosition("mid_21", "middlegame", "2r1r1k1/1p1q1ppp/p1nb1n2/3p4/1P1P4/P1N1BN1P/3Q1PP1/2R1R1K1 w - - 3 19", "Carlsen-style symmetrical positional squeeze"),
    ACPLPosition("mid_22", "middlegame", "r2q1rk1/4bppp/p1n1bn2/1pp1p3/4P3/1PPP1N2/P1B3PP/RNBQ1RK1 w - - 0 13", "Spanish Breyer locked pawn chain"),
    ACPLPosition("mid_23", "middlegame", "r1bq1rk1/pp3ppp/2n1pn2/2pp4/2PP4/2PBPN2/P4PPP/R1BQ1RK1 w - - 0 9", "Nimzo-Indian Rubenstein main line"),
    ACPLPosition("mid_24", "middlegame", "r1b2rk1/ppqnbppp/2p1pn2/3p4/2PP4/2N1PN2/PPQ1BPPP/R1B2RK1 w - - 4 10", "Semislav Meran quiet strategic battle"),
    ACPLPosition("mid_25", "middlegame", "r1b2rk1/1p2bppp/pqnp1n2/4p3/2PNPP2/2N1B3/PP2B1PP/R2Q1RK1 w - - 0 12", "Sicilian Najdorf central tension e5/f4"),

    # =========================================================================
    # 76-100: TECHNICAL ENDGAMES (Rooks, minor pieces, pawns, conversions)
    # =========================================================================
    ACPLPosition("end_01", "endgame", "8/8/4k3/8/8/3R4/4K3/7r w - - 0 1", "Basic R vs R positioning"),
    ACPLPosition("end_02", "endgame", "8/5pk1/4p1p1/7p/3R3P/4PKP1/1r3P2/8 b - - 1 34", "4 vs 3 rook endgame with kingside majority"),
    ACPLPosition("end_03", "endgame", "1r4k1/5ppp/8/8/8/8/5PPP/1R4K1 w - - 0 1", "Back rank rook tension"),
    ACPLPosition("end_04", "endgame", "8/8/1P1k4/8/8/1r6/2K5/8 b - - 0 1", "Passed pawn rook ending cutting off king"),
    ACPLPosition("end_05", "endgame", "8/4k3/4b3/8/8/4B3/4K3/8 w - - 0 1", "Opposite-colored bishop ending hold"),
    ACPLPosition("end_06", "endgame", "8/8/4k3/3n4/8/2N5/4K3/8 w - - 0 1", "Knight vs knight ending technique"),
    ACPLPosition("end_07", "endgame", "8/5k2/5p2/5P2/6K1/8/8/8 w - - 0 1", "Opposition and key squares pawn ending"),
    ACPLPosition("end_08", "endgame", "8/p7/8/1P6/8/8/8/k1K5 b - - 0 1", "Passed pawn flank race"),
    ACPLPosition("end_09", "endgame", "k7/8/PK6/8/8/8/8/8 b - - 0 1", "Stalemate avoidance king maneuver"),
    ACPLPosition("end_10", "endgame", "8/8/8/8/8/5k2/4p3/4K3 w - - 0 1", "King in front of passed pawn 1 legal move"),
    ACPLPosition("end_11", "endgame", "8/3K3k/8/2Pp3P/1p6/2P2r2/1B6/8 b - - 0 42", "Bishop vs rook active passed pawns"),
    ACPLPosition("end_12", "endgame", "8/8/4k3/8/4P3/8/4K3/8 w - - 0 1", "Lucena / Philidor pawn support"),
    ACPLPosition("end_13", "endgame", "8/8/2k5/8/8/2K5/2P5/8 w - - 0 1", "Distant opposition basic pawn ending"),
    ACPLPosition("end_14", "endgame", "8/8/8/3k4/8/3K4/3P4/8 w - - 0 1", "Pawn breakthrough opposition test"),
    ACPLPosition("end_15", "endgame", "8/8/p7/1p6/1P6/P7/8/k1K5 w - - 0 1", "Triangulation and zugzwang pawn ending"),
    ACPLPosition("end_16", "endgame", "8/8/8/4k3/3p4/8/3K4/8 w - - 0 1", "Defending against central passed pawn"),
    ACPLPosition("end_17", "endgame", "8/1r6/8/8/k7/8/1K6/1R6 w - - 0 1", "Rook check king triangulation"),
    ACPLPosition("end_18", "endgame", "8/8/8/4k3/4b3/8/4K3/4B3 w - - 0 1", "Same-colored bishops drawing technique"),
    ACPLPosition("end_19", "endgame", "8/8/4k3/8/4N3/8/4K3/3n4 w - - 0 1", "Knight vs knight outpost battle"),
    ACPLPosition("end_20", "endgame", "8/8/4k3/8/4B3/8/4K3/4n3 w - - 0 1", "Bishop vs trapped knight winning conversion"),
    ACPLPosition("end_21", "endgame", "8/8/5k2/R7/8/4K3/8/7r w - - 0 1", "Rook and pawn active defense"),
    ACPLPosition("end_22", "endgame", "8/8/1k6/8/1K6/P7/8/8 w - - 0 1", "Knight pawn ending with outside pawn"),
    ACPLPosition("end_23", "endgame", "8/8/k7/8/PK6/8/8/8 w - - 0 1", "Rook pawn drawing zone hold"),
    ACPLPosition("end_24", "endgame", "8/8/8/3k4/8/2K5/2P5/8 b - - 0 1", "Defending king finding drawing square"),
    ACPLPosition("end_25", "endgame", "8/8/8/8/3k4/8/2PK4/8 w - - 0 1", "Pawn advance timing in critical ending"),
)


def score_to_cp(score_obj: chess.engine.PovScore, turn: chess.Color, cap: float = 1000.0) -> float:
    """Convert chess.engine score to centipawns from the perspective of side to move."""
    s = score_obj.pov(turn).score(mate_score=10000)
    if s is None:
        return 0.0
    return float(max(-cap, min(cap, s)))


class PositionAgent:
    """A fresh official-runner process per independent benchmark position."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.last_elapsed_ms = 0.0

    def get_move(self, fen: str, time_left_ms: int) -> str:
        process = local(self.directory)
        try:
            process.start(90.0)
            started = time.perf_counter()
            move = process.move(fen, time_left_ms)
            self.last_elapsed_ms = (time.perf_counter() - started) * 1000
            return move
        finally:
            process.stop()


def measure_move_loss(
    oracle: chess.engine.SimpleEngine,
    board: chess.Board,
    move: chess.Move,
    eval_time_s: float = 0.1,
    cap: float = 1000.0,
) -> dict[str, Any]:
    """Compare unrestricted and forced-root searches from the same mover's POV."""
    if move not in board.legal_moves:
        raise ValueError(f"Illegal move: {move.uci()}")
    limit = chess.engine.Limit(time=eval_time_s)
    best = oracle.analyse(board, limit, game=object())
    best_move = best["pv"][0]
    best_cp = score_to_cp(best["score"], board.turn, cap)
    if move == best_move:
        played_cp = best_cp
    else:
        played = oracle.analyse(board, limit, root_moves=[move], game=object())
        played_cp = score_to_cp(played["score"], board.turn, cap)
    return {
        "best": best_move.uci(),
        "best_score_cp": best_cp,
        "played_score_cp": played_cp,
        "cpl": max(0.0, best_cp - played_cp),
    }


def evaluate_agent_acpl(
    agent_module: Any,
    positions: tuple[ACPLPosition, ...],
    eval_time_s: float = 0.1,
    cpl_cap: float = 1000.0,
    time_budget_ms: int = 5000,
    target: float = 40.0,
) -> dict[str, Any]:
    """Fail on invalid input or agent/oracle errors; never substitute moves."""
    if not positions or eval_time_s <= 0 or time_budget_ms <= 0 or target < 0:
        raise ValueError("Positions and budgets must be positive; target must be nonnegative")
    for pos in positions:
        board = chess.Board(pos.fen)
        if not board.is_valid() or board.is_game_over():
            raise ValueError(f"Invalid or terminal benchmark position: {pos.id}")
    sf_path = find_stockfish_binary()
    if sf_path is None:
        raise RuntimeError("Stockfish binary not found")
    details: list[dict[str, Any]] = []
    started = time.perf_counter()
    with chess.engine.SimpleEngine.popen_uci(sf_path) as oracle:
        oracle.configure({"Threads": 1, "Hash": 32, "Skill Level": 20, "UCI_LimitStrength": False})
        oracle_id = dict(oracle.id)
        for idx, pos in enumerate(positions):
            board = chess.Board(pos.fen)
            move_started = time.perf_counter()
            move_text = agent_module.get_move(pos.fen, time_budget_ms)
            elapsed_ms = (time.perf_counter() - move_started) * 1000
            elapsed_ms = getattr(agent_module, "last_elapsed_ms", elapsed_ms)
            if elapsed_ms > time_budget_ms:
                raise RuntimeError(f"Agent exceeded clock at {pos.id}")
            move = chess.Move.from_uci(move_text)
            detail = measure_move_loss(oracle, board, move, eval_time_s, cpl_cap)
            detail.update({
                "id": pos.id, "category": pos.category, "fen": pos.fen,
                "description": pos.description, "played": move.uci(),
                "agent_elapsed_ms": round(elapsed_ms, 2),
            })
            details.append(detail)
            if (idx + 1) % 10 == 0 or idx + 1 == len(positions):
                mean = sum(d["cpl"] for d in details) / len(details)
                print(f"[{idx + 1}/{len(positions)}] Mean ACPL: {mean:.2f}", flush=True)
    losses = [float(d["cpl"]) for d in details]
    mean = sum(losses) / len(losses)
    categories = sorted({p.category for p in positions})
    by_category = {
        cat: [float(d["cpl"]) for d in details if d["category"] == cat]
        for cat in categories
    }
    return {
        "mean_acpl": mean,
        "target_acpl": target,
        "passed_target": mean <= target,
        "oracle": oracle_id,
        "oracle_time_seconds": eval_time_s,
        "agent_time_left_ms": time_budget_ms,
        "score_cap_cp": cpl_cap,
        "method": "same-position unrestricted/forced-root; independent searches; mover POV",
        "bank_sha256": hashlib.sha256(
            json.dumps([(p.id, p.category, p.fen) for p in positions]).encode()
        ).hexdigest(),
        "category_acpl": {cat: sum(v) / len(v) for cat, v in by_category.items()},
        "category_counts": {cat: len(v) for cat, v in by_category.items()},
        "distribution": {
            "best_moves_count": sum(c == 0 for c in losses),
            "good_moves_count": sum(0 < c <= 50 for c in losses),
            "inaccuracies_count": sum(50 < c <= 100 for c in losses),
            "mistakes_count": sum(100 < c <= 200 for c in losses),
            "blunders_count": sum(c > 200 for c in losses),
            "blunder_rate_pct": 100 * sum(c > 200 for c in losses) / len(losses),
            "best_rate_pct": 100 * sum(c == 0 for c in losses) / len(losses),
        },
        "total_positions": len(details),
        "elapsed_seconds": time.perf_counter() - started,
        "positions": details,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-dir", type=Path, default=Path("."))
    parser.add_argument("--target", type=float, default=40.0, help="Target maximum ACPL")
    parser.add_argument("--positions", type=int, default=100)
    parser.add_argument("--eval-time", type=float, default=0.1, help="Oracle time per position (seconds)")
    parser.add_argument("--time-budget-ms", type=int, default=5000, help="Agent time_left_ms budget")
    parser.add_argument(
        "--out", type=Path, default=Path("scratch/stockfish_benchmark/acpl_report.json")
    )
    args = parser.parse_args()
    if not 1 <= args.positions <= len(ACPL_TEST_SUITE):
        parser.error(f"--positions must be between 1 and {len(ACPL_TEST_SUITE)}")

    # Load agent dynamically from agent-dir
    agent_file = args.agent_dir / "agent.py"
    if not agent_file.exists():
        raise SystemExit(f"agent.py not found in {args.agent_dir}")

    agent_mod = PositionAgent(args.agent_dir.resolve())

    report = evaluate_agent_acpl(
        agent_module=agent_mod,
        positions=ACPL_TEST_SUITE[:args.positions],
        eval_time_s=args.eval_time,
        time_budget_ms=args.time_budget_ms,
        target=args.target,
    )

    report["agent_state"] = "fresh official-runner process per position"
    report["agent_sha256"] = {
        str(p.relative_to(args.agent_dir)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted([*args.agent_dir.glob("*.py"), *args.agent_dir.glob("weights/*")])
        if p.is_file()
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n=======================================================")
    print("ACPL BENCHMARK RESULTS")
    print(f"Mean ACPL: {report['mean_acpl']} cp (Target: <= {args.target} cp)")
    print(f"Pass Target: {'YES [PASS]' if report['passed_target'] else 'NO [FAIL]'}")
    print("-------------------------------------------------------")
    print("Category Breakdown:")
    for cat, val in report["category_acpl"].items():
        print(f"  {cat.capitalize():12s}: {val:.1f} cp")
    print("-------------------------------------------------------")
    dist = report["distribution"]
    print(f"Best moves (0 cp)    : {dist['best_moves_count']}/{report['total_positions']} ({dist['best_rate_pct']}%)")
    print(f"Good moves (1-50 cp) : {dist['good_moves_count']}")
    print(f"Inaccuracies (50-100): {dist['inaccuracies_count']}")
    print(f"Mistakes (100-200)   : {dist['mistakes_count']}")
    print(f"Blunders (>200 cp)   : {dist['blunders_count']} ({dist['blunder_rate_pct']}%)")
    print(f"Report written to {args.out}")
    print("=======================================================")
    if not report["passed_target"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
