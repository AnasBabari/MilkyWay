"""Curated benchmark suite of 40 representative legal positions.

Covers:
- Opening positions
- Quiet middlegames
- Closed middlegames
- Open tactical middlegames
- High-branching positions
- Low-branching / cramped positions
- In-check / capture-heavy positions
- Queenless middlegames
- Rook endings
- Minor-piece endings
- Pawn endings
- Winning conversions
- Defensive holds
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BenchmarkPosition:
    id: str
    category: str
    fen: str
    description: str


BENCHMARK_SUITE: tuple[BenchmarkPosition, ...] = (
    # 1-4: Openings
    BenchmarkPosition(
        "open_01", "opening",
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "Standard starting position",
    ),
    BenchmarkPosition(
        "open_02", "opening",
        "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
        "Ruy Lopez / Italian opening branching point",
    ),
    BenchmarkPosition(
        "open_03", "opening",
        "rnbqkb1r/pp2pppp/3p1n2/8/3NP3/8/PPP2PPP/RNBQKB1R w KQkq - 1 5",
        "Open Sicilian (Najdorf/Dragon setup)",
    ),
    BenchmarkPosition(
        "open_04", "opening",
        "rnbqkb1r/ppp2ppp/4pn2/3p4/2PP4/2N5/PP2PPPP/R1BQKBNR w KQkq - 0 4",
        "Queen's Gambit Declined",
    ),

    # 5-8: Quiet middlegames
    BenchmarkPosition(
        "quiet_01", "quiet_middlegame",
        "r1b2rk1/1pq1bppp/p1nppn2/8/3NPP2/2N1B3/PPP1B1PP/R2Q1R1K w - - 0 11",
        "Sicilian Scheveningen quiet middlegame",
    ),
    BenchmarkPosition(
        "quiet_02", "quiet_middlegame",
        "r2q1rk1/1p2bppp/p1np1n2/2p1p3/P1B1P1b1/2NP1N2/1PP2PPP/R1BQ1RK1 w - - 1 9",
        "Italian quiet manoeuvring position",
    ),
    BenchmarkPosition(
        "quiet_03", "quiet_middlegame",
        "r1rq2k1/pb1nbppp/1p2pn2/2pp4/2PP4/1PN1PNP1/PB2QPBP/2RR2K1 b - - 1 13",
        "Catalan / Queen's Indian quiet structure",
    ),
    BenchmarkPosition(
        "quiet_04", "quiet_middlegame",
        "2rr2k1/1p2bppp/p1q1pn2/3p4/2PP4/1PN1PN2/PB3PPP/2RQR1K1 w - - 0 14",
        "Symmetrical pawn structure maneuvering",
    ),

    # 9-12: Closed middlegames
    BenchmarkPosition(
        "closed_01", "closed_middlegame",
        "r1b1k2r/pp2bppp/2n1p3/2ppP3/3P4/2N2N2/PPP1BPPP/R2QK2R w KQkq - 0 9",
        "French Defense Advance variation locked center",
    ),
    BenchmarkPosition(
        "closed_02", "closed_middlegame",
        "r2q1rk1/1ppnbppp/p2p1n2/4p3/3PP3/2N1BN2/PPP1QPPP/R4RK1 b - - 0 9",
        "King's Indian / Philidor closed structure",
    ),
    BenchmarkPosition(
        "closed_03", "closed_middlegame",
        "rnb1k2r/pp3ppp/4pn2/2pp4/1bPP4/2N1PN2/PP3PPP/R1BQKB1R w KQkq - 2 6",
        "Nimzo-Indian closed tension",
    ),
    BenchmarkPosition(
        "closed_04", "closed_middlegame",
        "r2q1rk1/pp1b1ppp/2n1pn2/2pp4/2PP4/2NBPN2/PP3PPP/R1BQ1RK1 w - - 0 8",
        "Closed Tarrasch center",
    ),

    # 13-16: Open tactical middlegames
    BenchmarkPosition(
        "tactical_01", "tactical_middlegame",
        "r1b2rk1/pp3ppp/2n1p3/q7/2BP4/5N2/PP1Q1PPP/R3K2R w KQ - 3 13",
        "Tension on queen and d4 pawn with kingside development",
    ),
    BenchmarkPosition(
        "tactical_02", "tactical_middlegame",
        "r1bq1rk1/pp3ppp/2n5/3np3/8/2NB4/PPP2PPP/R1BQ1RK1 w - - 0 11",
        "Greek gift / Bxh7 sacrifice potential",
    ),
    BenchmarkPosition(
        "tactical_03", "tactical_middlegame",
        "r2q1rk1/1b2bppp/p2p1n2/1p2p3/3NP3/P1NP3P/1P3PP1/R1BQR1K1 w - - 0 14",
        "Open e-file and d-file dynamic tactics",
    ),
    BenchmarkPosition(
        "tactical_04", "tactical_middlegame",
        "r1bqr1k1/ppp2ppp/2n5/8/2BP4/5N2/PP1Q1PPP/R4RK1 w - - 1 13",
        "Open central files with bishop eyeing f7",
    ),

    # 17-20: High branching (many legal moves)
    BenchmarkPosition(
        "branch_hi_01", "high_branching",
        "r1bqk2r/pppp1ppp/2n5/4p3/1bB1n3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 0 6",
        "Open position with 35+ legal moves",
    ),
    BenchmarkPosition(
        "branch_hi_02", "high_branching",
        "r1bqkb1r/pp3ppp/2n1pn2/2pp4/2PP4/2N1PN2/PP3PPP/R1BQKB1R w KQkq - 0 6",
        "Rich central pawn tension with 38 legal moves",
    ),
    BenchmarkPosition(
        "branch_hi_03", "high_branching",
        "r2q1rk1/pb1nbppp/1p2pn2/2pp4/2PP4/1PN1PN2/PB2BPPP/R2Q1RK1 w - - 0 10",
        "Wide piece mobility with 40+ legal moves",
    ),
    BenchmarkPosition(
        "branch_hi_04", "high_branching",
        "r1b1k2r/pp3ppp/1qn1pn2/2bp4/2PP4/2N1BN2/PP3PPP/R2QKB1R w KQkq - 3 8",
        "Tension with multiple hanging pieces and choices",
    ),

    # 21-24: Low branching / cramped
    BenchmarkPosition(
        "branch_lo_01", "low_branching",
        "k7/8/PK6/8/8/8/8/8 b - - 0 1",
        "Extreme cramped endgame, single legal king move",
    ),
    BenchmarkPosition(
        "branch_lo_02", "low_branching",
        "r1b1k2r/ppppqppp/2n5/4n3/1bP5/2N2N2/PP1BPPPP/R2QKB1R w KQkq - 0 8",
        "Threat of Nd3# cramped pinning position",
    ),
    BenchmarkPosition(
        "branch_lo_03", "low_branching",
        "8/8/8/8/8/5k2/4p3/4K3 w - - 0 1",
        "King in front of pawn, 1 legal move",
    ),
    BenchmarkPosition(
        "branch_lo_04", "low_branching",
        "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
        "Complex Kiwipete position with tactical threats",
    ),

    # 25-28: Queenless middlegames
    BenchmarkPosition(
        "qless_01", "queenless_middlegame",
        "r3k2r/ppp2ppp/2n1b3/3np3/8/2NB4/PPP2PPP/R1B2RK1 w kq - 0 11",
        "Queens exchanged early, active minor pieces and rooks",
    ),
    BenchmarkPosition(
        "qless_02", "queenless_middlegame",
        "r4rk1/pp1n1ppp/2p1pn2/8/3P4/2N2B2/PPP2PPP/R4RK1 w - - 0 14",
        "Quiet queenless grind with isolated pawn structure",
    ),
    BenchmarkPosition(
        "qless_03", "queenless_middlegame",
        "2r2rk1/pp1b1ppp/4pn2/8/3N4/1P2P3/P3BPPP/2RR2K1 w - - 1 17",
        "Open c-file and d-file queenless endgame transition",
    ),
    BenchmarkPosition(
        "qless_04", "queenless_middlegame",
        "r1b2rk1/pp2ppbp/2np1np1/8/2PNP3/2N1B3/PP2BPPP/R4RK1 b - - 3 10",
        "Dragon structure after queen swap",
    ),

    # 29-32: Rook endings
    BenchmarkPosition(
        "rook_01", "rook_ending",
        "8/8/4k3/8/8/3R4/4K3/7r w - - 0 1",
        "Basic R vs R positioning",
    ),
    BenchmarkPosition(
        "rook_02", "rook_ending",
        "8/5pk1/4p1p1/7p/3R3P/4PKP1/1r3P2/8 b - - 1 34",
        "4 vs 3 rook endgame with kingside pawn majority",
    ),
    BenchmarkPosition(
        "rook_03", "rook_ending",
        "1r4k1/5ppp/8/8/8/8/5PPP/1R4K1 w - - 0 1",
        "Back rank rook tension with single pair of rooks",
    ),
    BenchmarkPosition(
        "rook_04", "rook_ending",
        "8/8/1P1k4/8/8/1r6/2K5/8 b - - 0 1",
        "Passed pawn rook ending with cutting off king",
    ),

    # 33-36: Minor piece & pawn endings
    BenchmarkPosition(
        "minor_01", "minor_ending",
        "8/4k3/4b3/8/8/4B3/4K3/8 w - - 0 1",
        "Opposite-colored bishop endgame",
    ),
    BenchmarkPosition(
        "minor_02", "minor_ending",
        "8/8/4k3/3n4/8/2N5/4K3/8 w - - 0 1",
        "Knight vs knight endgame",
    ),
    BenchmarkPosition(
        "pawn_01", "pawn_ending",
        "8/5k2/5p2/5P2/6K1/8/8/8 w - - 0 1",
        "Opposition and key squares pawn ending",
    ),
    BenchmarkPosition(
        "pawn_02", "pawn_ending",
        "8/p7/8/1P6/8/8/8/k1K5 b - - 0 1",
        "Passed pawn race on the flank",
    ),

    # 37-40: Winning conversions & defensive positions
    BenchmarkPosition(
        "convert_01", "winning_conversion",
        "r1bqk2r/pppp1ppp/2n5/4P3/2B5/5Q2/PPP2PPP/RN2K2R b KQkq - 0 8",
        "White has big lead in development and mating threat on f7",
    ),
    BenchmarkPosition(
        "convert_02", "winning_conversion",
        "4r1k1/5ppp/8/8/8/8/4RPPP/6K1 w - - 0 1",
        "White is converting open file rook pin",
    ),
    BenchmarkPosition(
        "defend_01", "defensive",
        "r1b1kb1r/pppp1ppp/8/4q3/4n3/2N5/PPP1BPPP/R1BQK2R w KQkq - 0 8",
        "White defending pinned piece on e-file",
    ),
    BenchmarkPosition(
        "defend_02", "defensive",
        "6k1/5ppp/8/8/8/8/1r3PPP/R5K1 w - - 0 1",
        "White facing back-rank mate threat, must play g3/h3 or Ra8",
    ),
)


def validate_suite() -> bool:
    """Verify all positions are syntactically valid and legal chess boards."""
    import chess

    for pos in BENCHMARK_SUITE:
        board = chess.Board(pos.fen)
        if not board.is_valid():
            raise ValueError(f"Invalid position {pos.id}: {pos.fen}")
    return True


if __name__ == "__main__":
    validate_suite()
    print(f"Validated {len(BENCHMARK_SUITE)} benchmark positions.")
