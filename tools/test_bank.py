"""Stable development bank of 200 legal near-balanced positions for A/B testing.

Version: 1.0.0
Used for paired engine-vs-engine A/B testing: each position played once as White,
once as Black (200 FENs x 2 = 400 games). Opening luck is eliminated.
"""

from __future__ import annotations

from dataclasses import dataclass

BANK_VERSION = "1.0.0"


@dataclass(frozen=True)
class BankPosition:
    id: str
    category: str
    fen: str
    eval_cp: int


PAIRED_TEST_BANK: tuple[BankPosition, ...] = (
    BankPosition(
        "bank_001", "middlegame",
        "r1b4r/p3k3/1p2p3/B1p3pp/P1P4P/4P1P1/3K1P2/R1R5 b - - 0 24", 3,
    ),
    BankPosition(
        "bank_002", "endgame",
        "8/3K3k/8/2Pp3P/1p6/2P2r2/1B6/8 b - - 0 42", 43,
    ),
    BankPosition(
        "bank_003", "opening",
        "rnbqkbnr/p1pp1pp1/4p3/1p5p/1P1P2P1/8/P1P1PP1P/RNBQKBNR w KQkq - 0 6", 1,
    ),
    BankPosition(
        "bank_004", "middlegame",
        "8/p6r/k7/3pQ1np/2NP3p/5P2/4KP2/n7 w - - 6 38", -21,
    ),
    BankPosition(
        "bank_005", "opening",
        "r1bq1knr/pppp3p/2B3p1/4p3/4p3/N2P1N2/PPP1Qb1P/R1B2K1R w - - 0 11", -10,
    ),
    BankPosition(
        "bank_006", "opening",
        "r2q1rk1/1p1bnppp/5n2/p1N5/1PP5/4pN2/PB3PPP/RQ3RK1 b - - 1 14", -27,
    ),
    BankPosition(
        "bank_007", "opening",
        "r1bqkbr1/pp1pp2p/6p1/3Q4/P5P1/4K3/1P1P1P1P/RNB4R b - - 0 15", -1,
    ),
    BankPosition(
        "bank_008", "opening",
        "rq3nk1/pb2n3/1p1bp1pp/1N6/P5PP/1P2P3/3NB3/BR1Q1K2 b - - 2 21", -18,
    ),
    BankPosition(
        "bank_009", "middlegame",
        "1n6/4p3/3k1nr1/1B6/7p/3K1P1N/R7/4b2R b - - 3 39", 33,
    ),
    BankPosition(
        "bank_010", "middlegame",
        "r1b5/1ppk4/2p5/PN3p2/6p1/2P1P1P1/P2P1KR1/R1r5 w - - 2 22", 30,
    ),
    BankPosition(
        "bank_011", "endgame",
        "8/4k3/5p2/5P2/8/6K1/8/8 b - - 17 9", 11,
    ),
    BankPosition(
        "bank_012", "middlegame",
        "2b3nr/r1bp1k1p/5p2/6p1/1nP1P3/1N3K2/PPB5/R1B3NR b - - 2 20", 32,
    ),
    BankPosition(
        "bank_013", "endgame",
        "8/6p1/5kP1/1K6/8/8/8/8 w - - 2 55", -4,
    ),
    BankPosition(
        "bank_014", "endgame",
        "8/8/5k1P/7P/8/7K/5p2/8 b - - 2 16", 17,
    ),
    BankPosition(
        "bank_015", "endgame",
        "1k6/8/8/6K1/7P/6p1/8/8 b - - 33 72", -34,
    ),
    BankPosition(
        "bank_016", "opening",
        "1rb2knr/pp3ppp/Bq2pb1B/3P4/8/1nN2N2/PP3PPP/1R1QK2R w K - 6 15", -6,
    ),
    BankPosition(
        "bank_017", "middlegame",
        "rnb2b1Q/pp2pp1R/2k3p1/3q2B1/8/1p3PP1/P3P1P1/R3K1N1 w Q - 0 19", 2,
    ),
    BankPosition(
        "bank_018", "endgame",
        "8/8/6pk/5p2/5P1P/7P/8/3K4 b - - 1 16", 1,
    ),
    BankPosition(
        "bank_019", "opening",
        "rnbqkb1r/p2pppp1/5n1p/2p5/1p2P3/3K3P/PPPP1PP1/RNBQNB1R b kq - 1 6", -43,
    ),
    BankPosition(
        "bank_020", "middlegame",
        "r5r1/p2n1n1p/3b4/3Np1k1/2p1P3/7P/PPPP1P2/R1B1K2R w Q - 2 20", 28,
    ),
    BankPosition(
        "bank_021", "opening",
        "rnbqkb1r/ppp2ppp/3Qpn2/8/2pP4/2N2N2/PP2PPPP/R1B1KB1R b KQ - 5 7", 33,
    ),
    BankPosition(
        "bank_022", "endgame",
        "8/8/5p2/5P2/8/8/k3K3/8 b - - 41 21", 28,
    ),
    BankPosition(
        "bank_023", "endgame",
        "5k2/7p/5p2/6pP/6P1/5P2/7K/8 b - - 0 13", 25,
    ),
    BankPosition(
        "bank_024", "middlegame",
        "6n1/1p2kp1p/4b3/r7/p1P2P2/P6P/4N3/2R1KB2 w - - 1 23", -36,
    ),
    BankPosition(
        "bank_025", "middlegame",
        "3r1k2/pp1r3p/2p3p1/3n1p2/1P1P2B1/2P5/P4PPK/4RR2 w - - 0 26", 10,
    ),
    BankPosition(
        "bank_026", "middlegame",
        "r1rk4/1p3pp1/n1p5/p1b1P3/5BNp/PP1P4/2P4P/1R3R1K b - - 5 23", 39,
    ),
    BankPosition(
        "bank_027", "endgame",
        "8/8/2k4p/5RP1/1r6/8/6P1/7K w - - 2 38", 9,
    ),
    BankPosition(
        "bank_028", "middlegame",
        "1rb1k2r/4p2p/1pn4b/1B1p2p1/3N3P/6R1/PPP3P1/RN5K w k - 0 21", -31,
    ),
    BankPosition(
        "bank_029", "middlegame",
        "r4k2/pprB2p1/8/7p/7P/6N1/PP3PP1/n2K3R b - - 1 23", -28,
    ),
    BankPosition(
        "bank_030", "opening",
        "rnb1kbnr/ppppqpp1/8/4p2p/2P5/4PQ2/PP1P1PPP/RNB1KBNR w KQkq - 5 5", 6,
    ),
    BankPosition(
        "bank_031", "opening",
        "r2q1rk1/1p2bppp/p1np1n2/2p1p3/P1B1P1b1/2NP1N2/1PP2PPP/R1BQ1RK1 w - - 1 9", 13,
    ),
    BankPosition(
        "bank_032", "opening",
        "rnbqkb1r/3pp2p/1pp2p2/P5p1/P3n1Q1/3B4/1BPP1PPP/RN2K1NR b KQkq - 0 8", -43,
    ),
    BankPosition(
        "bank_033", "middlegame",
        "4kbr1/p2ppp2/4r2p/Pp4pP/5P2/6K1/R3P1P1/5BNR b - - 0 23", 23,
    ),
    BankPosition(
        "bank_034", "middlegame",
        "rnb5/pp3p2/1k1r1n1p/3p2P1/1P1Np1P1/N7/P3PPB1/R3K2R b KQ - 0 22", 29,
    ),
    BankPosition(
        "bank_035", "middlegame",
        "r1r3k1/4bpp1/p2pp2p/1p6/1P3P2/8/P1B1QBPP/6K1 w - - 0 23", -6,
    ),
    BankPosition(
        "bank_036", "middlegame",
        "rnb4r/1p3ppp/p1pp3n/2P1k3/7P/P2K4/P1Q1Pp2/3R1BNR w - - 0 17", 45,
    ),
    BankPosition(
        "bank_037", "middlegame",
        "r2q1b2/3P2k1/pp4pp/3P4/7P/5pP1/P1P1NP2/2R3RK b - - 0 24", 16,
    ),
    BankPosition(
        "bank_038", "middlegame",
        "6r1/2r2pk1/4p3/1P3p2/6PR/3p4/P4P1K/4R3 b - - 2 38", 7,
    ),
    BankPosition(
        "bank_039", "endgame",
        "8/8/1k3p2/5P2/1K6/8/8/8 w - - 42 22", 10,
    ),
    BankPosition(
        "bank_040", "middlegame",
        "2bqk1nr/2p2pp1/2n5/p2N3p/8/6P1/P3PP1P/R1B1KBNR b KQk - 0 11", -26,
    ),
    BankPosition(
        "bank_041", "endgame",
        "r2k4/5B2/p4p2/2p4p/8/P1n2KPP/8/7R b - - 1 42", -37,
    ),
    BankPosition(
        "bank_042", "middlegame",
        "r3k2r/pppR1ppB/2n5/4p3/n7/8/1PP2PPP/R1B3K1 b kq - 0 14", 23,
    ),
    BankPosition(
        "bank_043", "endgame",
        "7n/6k1/8/5P2/5P2/1P1P3P/8/4b2K b - - 0 46", -5,
    ),
    BankPosition(
        "bank_044", "endgame",
        "8/8/5p2/5P2/8/7k/8/1K6 w - - 88 45", -3,
    ),
    BankPosition(
        "bank_045", "middlegame",
        "rnb1kb1r/ppp2ppp/4p3/8/P1p5/4P3/1P3KPP/R1BN1BNR b kq - 0 9", -34,
    ),
    BankPosition(
        "bank_046", "endgame",
        "8/8/6k1/7p/5p1P/5P2/7K/8 b - - 30 31", -34,
    ),
    BankPosition(
        "bank_047", "middlegame",
        "rnb1kr2/3p4/p1p3p1/B2n1p1p/1P3P2/1K2PR2/2P4P/4QB2 b - - 0 23", 44,
    ),
    BankPosition(
        "bank_048", "middlegame",
        "rnb2bn1/pp1ppk2/8/r5p1/4PN2/6PP/P1PP1P2/RNB1K2R b KQ - 1 11", -23,
    ),
    BankPosition(
        "bank_049", "middlegame",
        "7r/p3nppp/5k2/8/8/b6P/PPPr1P1P/R1B1K1NR b - - 3 16", 0,
    ),
    BankPosition(
        "bank_050", "opening",
        "rnbk2nr/pppp2pp/8/4p1q1/4pPP1/B7/2PPB1NP/RN1QK2R b KQ f3 0 10", 3,
    ),
    BankPosition(
        "bank_051", "middlegame",
        "2b2k1r/p1pR1p2/8/4p1P1/n1r3P1/8/P2PP3/R1BK2N1 b - - 0 26", 21,
    ),
    BankPosition(
        "bank_052", "opening",
        "rn5r/p1k2ppp/1p6/3QN1qn/2P1PpP1/b7/PP3P1P/RB2K2R b KQ - 5 17", -25,
    ),
    BankPosition(
        "bank_053", "middlegame",
        "r1br4/pp1pnkpp/n1p5/7N/2Pbp3/P1N5/1P1BPPPP/1R2KB1R w K - 0 15", 1,
    ),
    BankPosition(
        "bank_054", "middlegame",
        "2k3r1/p5b1/2n3n1/1B1r4/P2p2bP/1P6/2P2KP1/RNB4R w - - 0 21", 16,
    ),
    BankPosition(
        "bank_055", "middlegame",
        "r7/6rp/2n4k/p3P3/2p5/P6P/1PPR1K1n/R1B5 w - - 1 32", -43,
    ),
    BankPosition(
        "bank_056", "middlegame",
        "rnb2rk1/pp1n1ppp/4p3/8/2BP3P/2p1P1P1/PP3P2/RNB1K2R w KQ - 0 13", 20,
    ),
    BankPosition(
        "bank_057", "opening",
        "r1b3k1/p1Bpqr1p/2n3p1/1B3p2/8/1P1P1K1Q/P4RPP/R7 b - - 4 21", 44,
    ),
    BankPosition(
        "bank_058", "endgame",
        "8/1p6/1p6/2p4p/PP3kp1/7R/8/5K2 w - - 2 45", 12,
    ),
    BankPosition(
        "bank_059", "endgame",
        "5nB1/k7/8/7K/1p6/8/7P/8 w - - 1 36", -36,
    ),
    BankPosition(
        "bank_060", "middlegame",
        "r3kBr1/pppb1p2/4p3/2N4p/1npn4/P7/4PPPP/R3KBNR b KQq - 2 13", 4,
    ),
    BankPosition(
        "bank_061", "middlegame",
        "rn1k2r1/1p1b1p2/p7/2p3p1/2P1P3/1P3P2/P2P4/bNBQ1K1B w - - 0 21", -43,
    ),
    BankPosition(
        "bank_062", "opening",
        "r1bqk1nr/ppppnppp/8/8/2BpP3/P7/2PP1PPP/RNBQK2R b KQkq - 2 6", -38,
    ),
    BankPosition(
        "bank_063", "opening",
        "2b1kb1r/3q1ppp/r1Bp4/p1p1P3/P5P1/2P1P3/7P/QNB2KNR b - - 2 17", -3,
    ),
    BankPosition(
        "bank_064", "opening",
        "rq3r1k/3nbBpp/1p1p4/2p1p2b/p2NP3/2PP4/1P3PPP/1RBQ1RK1 w - - 0 16", 37,
    ),
    BankPosition(
        "bank_065", "middlegame",
        "5k2/p2p1n2/1p2p3/2r1N1q1/8/7N/P5BP/1R2K2R b - - 5 21", 3,
    ),
    BankPosition(
        "bank_066", "opening",
        "rnb1kb1r/ppp2p1p/3p4/4p1q1/4P3/P1N2N2/1PP2PPP/R2QKB1R b KQkq - 1 7", 43,
    ),
    BankPosition(
        "bank_067", "opening",
        "rnb4r/pp2k1pp/2pbPn2/2q1P3/8/8/RPPPQ1PP/1NBK2NR b - - 6 11", -28,
    ),
    BankPosition(
        "bank_068", "middlegame",
        "r2r2k1/Bp2ppbp/p2p1np1/8/2P1PPB1/5nP1/PP3K1P/RN3R2 b - - 1 16", -36,
    ),
    BankPosition(
        "bank_069", "endgame",
        "5k2/8/8/7P/8/6p1/2K5/8 w - - 1 56", -21,
    ),
    BankPosition(
        "bank_070", "middlegame",
        "r2r2k1/8/5p2/p1pP2nK/8/P7/3N2PP/R4B2 b - - 2 31", -24,
    ),
    BankPosition(
        "bank_071", "middlegame",
        "rnbk1bnr/1p1pp2p/8/p1p4p/7P/P2PN2R/1P3PP1/1RB1KBN1 b - - 2 13", 22,
    ),
    BankPosition(
        "bank_072", "middlegame",
        "r3k1r1/1pp1qppp/p2Q4/8/N1P2P2/4b3/PP2B1P1/1RB2K2 b q - 0 17", 38,
    ),
    BankPosition(
        "bank_073", "middlegame",
        "6nr/1bb2k1p/5p2/3p3K/1nP1P3/1N6/rPBB4/R5NR w - - 2 24", 5,
    ),
    BankPosition(
        "bank_074", "opening",
        "r1bqkbnr/pp1p2p1/n4p2/2p1p2p/2P1P1B1/8/PPQP1PPP/RNB1K1NR w KQkq - 0 6", 40,
    ),
    BankPosition(
        "bank_075", "middlegame",
        "5r1b/8/r2P1pkp/3N2p1/8/5P2/PP4PP/R5K1 w - - 1 24", -2,
    ),
    BankPosition(
        "bank_076", "opening",
        "rnbk2nr/pp2pp2/8/2pPq3/1P6/P7/R1PQBPP1/1NB1K1N1 b - - 2 12", -35,
    ),
    BankPosition(
        "bank_077", "endgame",
        "4r3/7k/7p/3P4/5P2/8/4B3/4K3 b - - 2 41", -28,
    ),
    BankPosition(
        "bank_078", "middlegame",
        "r1b1k3/pp1p3r/5B2/1p4Rp/P2P4/1K6/6PP/3R4 w q - 1 27", 8,
    ),
    BankPosition(
        "bank_079", "opening",
        "r1q1kbr1/p3pppp/1Nn1b3/7n/P3p3/3Q2P1/1PPK1P1P/RNB2B1R b q - 0 13", -6,
    ),
    BankPosition(
        "bank_080", "middlegame",
        "1r3r2/1p1n1ppk/2p1pn2/p2N3p/3P3P/5B2/PPP2PP1/R4RK1 w - - 0 18", 38,
    ),
    BankPosition(
        "bank_081", "middlegame",
        "3R1rk1/5p1p/6p1/8/p1p4P/8/Pr2RNPK/8 b - - 0 28", 41,
    ),
    BankPosition(
        "bank_082", "middlegame",
        "5b2/P3n1pr/5k2/7P/PB3Pn1/5PR1/8/R2K1b2 w - - 0 30", -6,
    ),
    BankPosition(
        "bank_083", "middlegame",
        "2rr3k/6p1/p4p2/4p2p/1Q2P3/3R1K1P/8/b3N3 w - - 0 37", -5,
    ),
    BankPosition(
        "bank_084", "opening",
        "rnbqkbr1/pppp2pp/7n/4p3/P1P2p2/1P5P/2QPPPP1/RNB1KBNR w KQq - 0 6", -39,
    ),
    BankPosition(
        "bank_085", "endgame",
        "1N3k1b/p6p/8/8/P1r5/6R1/2P2K2/8 b - - 3 43", 5,
    ),
    BankPosition(
        "bank_086", "endgame",
        "5b2/4p3/1k4p1/8/5P2/K7/4P3/6N1 w - - 0 45", -7,
    ),
    BankPosition(
        "bank_087", "middlegame",
        "r1b1k2r/2pp1ppp/7n/8/N2pP3/R2P4/1P2KPP1/1Q6 b kq - 0 20", -23,
    ),
    BankPosition(
        "bank_088", "endgame",
        "8/6k1/8/8/4p3/6P1/5K2/8 w - - 4 57", -8,
    ),
    BankPosition(
        "bank_089", "middlegame",
        "r4k1r/pp1bb1pp/5p2/2Pp4/2P1N1n1/5P2/PP2B1PP/R3K1NR w KQ - 0 15", 2,
    ),
    BankPosition(
        "bank_090", "endgame",
        "8/8/7k/3K3p/8/4P3/8/8 b - - 3 56", 29,
    ),
    BankPosition(
        "bank_091", "endgame",
        "1r2k3/p1p4p/1p2p1p1/8/2PPp2P/4P3/PP3K2/1R6 b - - 0 29", -23,
    ),
    BankPosition(
        "bank_092", "opening",
        "r1b2knr/ppp2p1p/n2bP3/7q/Q2P1P2/8/PP2PNPP/RN2KB1R w KQ - 3 12", 27,
    ),
    BankPosition(
        "bank_093", "endgame",
        "6k1/8/5p2/5P2/8/8/8/5K2 b - - 13 7", 8,
    ),
    BankPosition(
        "bank_094", "middlegame",
        "r1b5/2kp4/3pp2r/8/2P1B3/8/5PPP/1N2K1R1 w - - 2 23", -43,
    ),
    BankPosition(
        "bank_095", "middlegame",
        "rn5r/N1pb1kpp/8/4pp2/8/3B3P/PPP2P1P/2R1RK2 w - - 1 18", 21,
    ),
    BankPosition(
        "bank_096", "opening",
        "rnbqk2r/pp1p3p/3pp1pn/5P2/8/1P6/2PP1PPP/RN1QKBNR w KQkq - 0 7", 30,
    ),
    BankPosition(
        "bank_097", "middlegame",
        "r1b2k2/7p/1p1N4/2b4P/P5P1/2p5/P1P2n2/2R1R1K1 w - - 1 28", -3,
    ),
    BankPosition(
        "bank_098", "middlegame",
        "3r1k1r/3n3B/7p/2p2p2/K1P5/3P1P1P/6P1/bR3R2 b - - 2 34", -16,
    ),
    BankPosition(
        "bank_099", "middlegame",
        "rnb2b1r/1p2pkp1/3p3p/8/1pP1P1P1/1P6/3PNP1P/1NB1KB1R b K - 0 13", -9,
    ),
    BankPosition(
        "bank_100", "middlegame",
        "4r1n1/p4p2/np2pkpP/8/2p1bKP1/2P1P3/P4P1R/R1B5 w - - 2 23", -29,
    ),
    BankPosition(
        "bank_101", "endgame",
        "7k/5pp1/8/R6p/7P/6P1/2r2P2/7K w - - 1 7", -29,
    ),
    BankPosition(
        "bank_102", "middlegame",
        "4k1n1/1r3pp1/p1p4B/4P3/4n2P/7P/P1K2P2/6NR w - - 2 23", 10,
    ),
    BankPosition(
        "bank_103", "middlegame",
        "rB6/pb4pp/2p3k1/8/6n1/P2p3P/R3N3/4K2R b K - 2 23", -42,
    ),
    BankPosition(
        "bank_104", "endgame",
        "8/2p3k1/1R6/5b2/3K4/6P1/5nP1/8 w - - 12 49", -7,
    ),
    BankPosition(
        "bank_105", "middlegame",
        "r3kb1r/1ppR1ppp/8/6B1/1p6/P1n5/2P1BPPP/4K2R w Kkq - 0 15", -37,
    ),
    BankPosition(
        "bank_106", "middlegame",
        "r3k3/p4R1r/P2bp1p1/7p/2p1K3/N3P2P/5PP1/6R1 b - - 5 27", 22,
    ),
    BankPosition(
        "bank_107", "opening",
        "rn1qk1nr/p1p2pp1/1p1pb3/7p/1b3B2/4QN2/PPP1PPPP/RN1K1B1R w kq - 2 10", 12,
    ),
    BankPosition(
        "bank_108", "middlegame",
        "8/1p3p2/k4npb/p1p5/B1N2P2/2PK2P1/PP6/2R4r b - - 2 30", 22,
    ),
    BankPosition(
        "bank_109", "opening",
        "r3qrk1/1p2bppp/4pn2/1p6/2pP4/1P2PN2/PB3PPP/2RQR1K1 w - - 2 19", 32,
    ),
    BankPosition(
        "bank_110", "endgame",
        "8/8/1k3p2/5P2/8/8/6K1/8 w - - 30 16", -22,
    ),
    BankPosition(
        "bank_111", "middlegame",
        "rnb5/1p1p2p1/p1p5/3BPk2/8/2PR4/P3K1P1/RNb5 b - - 2 21", -1,
    ),
    BankPosition(
        "bank_112", "middlegame",
        "r1b2b1r/p1k1pppp/p1p2n2/8/4PP2/6P1/PPPN3P/R1B1K1NR b KQ - 0 8", 19,
    ),
    BankPosition(
        "bank_113", "opening",
        "r1bq1bnr/pppk3p/3p2p1/4pp1P/2B1P1P1/3n1N2/PPPPKP2/RNBQ3R b - - 0 9", -1,
    ),
    BankPosition(
        "bank_114", "opening",
        "rr1q2k1/p4ppp/1p2pb2/2pb1Q2/P1PP4/1P2P3/1B3PBP/2R2RK1 b - - 2 21", -23,
    ),
    BankPosition(
        "bank_115", "middlegame",
        "r4n2/5ppk/p1p4p/4R3/1P6/2P2PP1/P3K3/R2N3r b - - 2 31", 18,
    ),
    BankPosition(
        "bank_116", "middlegame",
        "rn3bn1/1p2pkp1/p4p2/2p5/8/1PP1KP2/P4R1N/R1B5 w - - 1 21", -3,
    ),
    BankPosition(
        "bank_117", "endgame",
        "7k/8/5p1P/3Bp3/pr3P1P/8/1P4K1/8 w - - 2 44", 28,
    ),
    BankPosition(
        "bank_118", "middlegame",
        "7k/5pp1/ppr5/4pP1p/7P/P3P2K/R2r4/3N3R b - - 0 45", -44,
    ),
    BankPosition(
        "bank_119", "middlegame",
        "2b1k1n1/2p2p1r/n2pp2B/6N1/2PP3P/8/Pq2PP1P/R3KB1R b KQ - 1 15", 37,
    ),
    BankPosition(
        "bank_120", "middlegame",
        "rr6/2pk3p/p4pp1/3p4/2p4P/B1P3P1/P3PP2/2K2BR1 w - - 0 23", 11,
    ),
    BankPosition(
        "bank_121", "middlegame",
        "1n3knr/6p1/7p/2p2P2/P3pP1b/3pK3/1P5P/1R3BNR b - - 0 26", -9,
    ),
    BankPosition(
        "bank_122", "endgame",
        "8/prpk2p1/n5p1/3p4/7P/P7/5P2/RNB1K3 b Q - 1 25", 26,
    ),
    BankPosition(
        "bank_123", "opening",
        "1nb1k1nr/rp2b2p/p2qp1p1/8/3P2Q1/2N5/PPP2PPP/2KR1BNR b k - 1 10", 39,
    ),
    BankPosition(
        "bank_124", "opening",
        "rnbk3r/pp5p/R4p2/2Pp1p2/6P1/2Nq1N2/1P3P1P/2Q1K2R b K - 1 20", 0,
    ),
    BankPosition(
        "bank_125", "opening",
        "rnbqk2r/2ppbppp/8/pp6/N1N1P1n1/1P3P2/P1PPK2P/R1BQ1B1R w kq - 0 11", -31,
    ),
    BankPosition(
        "bank_126", "endgame",
        "8/8/5p2/2k2P2/8/8/2K5/8 w - - 68 35", -33,
    ),
    BankPosition(
        "bank_127", "middlegame",
        "1n3Rnr/6k1/2b1p3/2p4p/7P/3B4/5PP1/5K1R b - - 0 25", 0,
    ),
    BankPosition(
        "bank_128", "middlegame",
        "8/p6r/4Q2n/k2p3p/3P3p/5P2/3NKP2/n7 w - - 0 35", 22,
    ),
    BankPosition(
        "bank_129", "middlegame",
        "1n3b1r/4pkp1/1p6/2p2P2/1p4p1/1P5N/3P1PBP/rNBK1R2 b - - 3 21", 16,
    ),
    BankPosition(
        "bank_130", "opening",
        "rnb1kbnr/1p1p1p1p/p1p1q1p1/4p3/1P6/B4NP1/P1PPPP1P/RN1QKB1R w KQkq - 3 8", 16,
    ),
    BankPosition(
        "bank_131", "endgame",
        "2k5/8/8/6P1/8/4K2p/8/8 b - - 16 35", 23,
    ),
    BankPosition(
        "bank_132", "middlegame",
        "1nb3nr/1p1k3p/2p5/5p2/8/r7/1PPNKPPP/2B2BNR w - - 0 16", 10,
    ),
    BankPosition(
        "bank_133", "middlegame",
        "rnb3Br/1p1p2p1/p1p4p/7k/1b2P3/7N/P1P1K1P1/RNB4R w - - 0 14", 17,
    ),
    BankPosition(
        "bank_134", "opening",
        "rnb1kbn1/pp1p1ppr/2p4p/2P4P/4pqP1/1Q5R/PP1PPP2/RNB1KBN1 b Qq - 4 7", -21,
    ),
    BankPosition(
        "bank_135", "middlegame",
        "1rb3k1/pp2n3/n5pp/2ppp3/4P3/P1P1K3/R2P2PP/1NB3R1 w - - 0 18", 11,
    ),
    BankPosition(
        "bank_136", "middlegame",
        "rnb5/3p1p2/1p2qk1P/P3p3/4P3/3P1N1P/P3BP2/R3K2R w KQ - 3 22", 45,
    ),
    BankPosition(
        "bank_137", "middlegame",
        "r1bqkb2/pp1pppp1/3B4/4n2p/3N4/6P1/P1PPK1P1/RN1Q1B2 b q - 0 13", -29,
    ),
    BankPosition(
        "bank_138", "endgame",
        "8/8/6pp/8/6PP/8/7K/4k3 b - - 4 14", 0,
    ),
    BankPosition(
        "bank_139", "opening",
        "1nb1kb1r/1pqpppp1/r6n/2P4p/1pP3P1/2N4P/P3PP1R/R1BQKBN1 w Qk - 0 9", 9,
    ),
    BankPosition(
        "bank_140", "middlegame",
        "1n3b1r/1B2p1p1/5k2/1pp2P2/1p4p1/BP5N/3P1P1P/rN1K1R2 b - - 1 23", -8,
    ),
    BankPosition(
        "bank_141", "middlegame",
        "2b5/3p4/2p4n/1p1k2p1/3P3R/4r3/P3B1P1/3RK3 w - - 0 29", 44,
    ),
    BankPosition(
        "bank_142", "opening",
        "rnbqk1nr/p1pp1p1p/1p1bp3/6p1/3P4/1P2P1PN/P1P2P1P/RNBQKB1R b KQkq - 0 5", 18,
    ),
    BankPosition(
        "bank_143", "middlegame",
        "7r/1k6/pp5b/5p1p/5R2/1P3p2/PBP2Pb1/3RK3 b - - 0 35", 36,
    ),
    BankPosition(
        "bank_144", "middlegame",
        "1n5r/5k2/3bp1pR/1p6/3P1P2/3P2P1/1PKBB3/r5N1 w - - 1 27", 16,
    ),
    BankPosition(
        "bank_145", "endgame",
        "8/7k/8/P6p/2p2P2/8/8/3K4 b - - 0 51", -9,
    ),
    BankPosition(
        "bank_146", "middlegame",
        "3q1r2/1ppn1pk1/3p4/r5b1/Q7/2N5/PPP2PPP/R2R1K2 b - - 0 18", -38,
    ),
    BankPosition(
        "bank_147", "opening",
        "r1b1kb1r/p3q1pp/2ppp2n/8/2BPp3/4P1PP/P1Q2P1R/1RB1K1N1 b kq - 1 13", -34,
    ),
    BankPosition(
        "bank_148", "middlegame",
        "2r4k/1p4pn/p3R1p1/2q5/5P2/1PN3P1/P6K/R1B5 b - - 0 28", 41,
    ),
    BankPosition(
        "bank_149", "middlegame",
        "2b3n1/3p3p/n2k4/6p1/5P2/rP4PP/3PP3/1N2KB1R b K - 0 18", -6,
    ),
    BankPosition(
        "bank_150", "opening",
        "r1bqk2r/ppppn1pp/8/n3Q3/4p2N/b2B4/PPPP1PPP/RNB1K2R w KQkq - 1 9", 5,
    ),
    BankPosition(
        "bank_151", "middlegame",
        "2bk4/1p3B2/5p2/r1b4p/7P/P3nP2/1P3K2/R5R1 b - - 0 27", -34,
    ),
    BankPosition(
        "bank_152", "endgame",
        "8/4k3/5p2/5P2/8/8/5K2/8 b - - 11 6", 9,
    ),
    BankPosition(
        "bank_153", "endgame",
        "8/8/4k3/8/3B4/1b2K3/8/8 w - - 24 13", 17,
    ),
    BankPosition(
        "bank_154", "middlegame",
        "1rb1k1r1/1p4p1/5p1p/1p2p3/1P6/7P/3B1P2/RN1R1K2 b - - 1 31", -1,
    ),
    BankPosition(
        "bank_155", "endgame",
        "8/1K6/1P6/8/4k3/p7/8/8 w - - 12 24", -42,
    ),
    BankPosition(
        "bank_156", "middlegame",
        "1n3b2/1B4p1/5k2/1pp1pP1r/1p1P2p1/1P5N/1B3P1P/rN1K1R2 b - - 0 25", 3,
    ),
    BankPosition(
        "bank_157", "middlegame",
        "r1n3k1/R7/1p1r2p1/5p2/3PN2P/6P1/bP3P2/4K2R w K - 7 29", 2,
    ),
    BankPosition(
        "bank_158", "middlegame",
        "8/P5k1/8/4p2p/4P3/5p2/1K6/1R2R1q1 b - - 0 39", 26,
    ),
    BankPosition(
        "bank_159", "endgame",
        "8/3k4/4p1p1/4Kp1p/7P/4P1P1/5P2/8 b - - 1 40", 39,
    ),
    BankPosition(
        "bank_160", "opening",
        "r1bq1knr/pppp1ppp/B7/2b5/3pP3/1PNP2P1/2P2P1P/R1BQK2R b KQ - 0 10", -26,
    ),
    BankPosition(
        "bank_161", "opening",
        "r2q2k1/p1rnbp1p/1p2pnp1/2pb4/3P4/1PN1PNP1/PB1R1PBP/2R1Q1K1 w - - 0 17", 32,
    ),
    BankPosition(
        "bank_162", "endgame",
        "8/8/6k1/5p1p/5P1P/8/8/5K2 w - - 47 77", -30,
    ),
    BankPosition(
        "bank_163", "endgame",
        "8/2k5/8/8/8/7b/8/B3K3 w - - 18 10", -39,
    ),
    BankPosition(
        "bank_164", "opening",
        "rnb1qbnr/ppp1p1p1/7p/3k1p2/1P1P3P/5N2/P1PQPPP1/R1BK1B1R w - - 0 10", -38,
    ),
    BankPosition(
        "bank_165", "opening",
        "r1bqkbr1/ppp1n1pp/3p1p2/4p3/4P3/1P1P1N2/P1P1KPPP/RNBQ3R b q - 1 7", -44,
    ),
    BankPosition(
        "bank_166", "opening",
        "rnbk1b1r/1pqpppp1/7n/2P4p/1pP3P1/1QN4P/P3PPBR/R1B1K1N1 w Q - 4 11", 39,
    ),
    BankPosition(
        "bank_167", "endgame",
        "8/8/2k2p2/5P1K/8/8/8/8 w - - 42 22", -41,
    ),
    BankPosition(
        "bank_168", "middlegame",
        "r1N1r1kb/1p3p1p/4pBp1/p7/P1P3P1/8/1P2nPKP/3R1R2 b - - 0 19", 9,
    ),
    BankPosition(
        "bank_169", "middlegame",
        "rnbqkb2/3pp3/5p2/p2PB1p1/6P1/NP5N/P3P3/R3KB1R b KQ - 1 16", -10,
    ),
    BankPosition(
        "bank_170", "endgame",
        "1K6/8/5p1k/5P2/8/8/8/8 w - - 36 19", 1,
    ),
    BankPosition(
        "bank_171", "middlegame",
        "r7/pk2p3/4P2n/1P3P2/5P2/6r1/1BP5/1N2K1N1 b - - 4 32", 0,
    ),
    BankPosition(
        "bank_172", "opening",
        "r1bqkb1r/p1pppppp/8/1p1n2N1/2NP1n2/2P1P3/PP3PPP/R1BQKB1R w KQkq - 2 8", 33,
    ),
    BankPosition(
        "bank_173", "middlegame",
        "r1b2k2/pp3p1p/6pb/P2Pp3/3N4/2N5/1P3PP1/1R4K1 b - - 0 19", -37,
    ),
    BankPosition(
        "bank_174", "middlegame",
        "rn6/5kpp/4p2P/B4p2/5P2/5rP1/1P1K1R2/1R6 b - - 0 32", 35,
    ),
    BankPosition(
        "bank_175", "middlegame",
        "1nb1kbr1/r2ppppp/2p5/8/1P1P4/8/P1PNPn1P/R1B1KBNR w KQ - 0 10", 33,
    ),
    BankPosition(
        "bank_176", "middlegame",
        "5rk1/2p2p2/3p1np1/1p3P1p/3PP3/qP4B1/P1P2K1P/R1RN4 b - - 0 21", 13,
    ),
    BankPosition(
        "bank_177", "middlegame",
        "2n3qk/pr3rp1/5p2/3N4/3N4/1b6/PRB2PPP/2B2RK1 b - - 1 22", 13,
    ),
    BankPosition(
        "bank_178", "middlegame",
        "2k1rb2/R1p4r/3p4/5p1p/1P1p1P2/8/3P1K2/1NB3R1 w - - 0 26", 9,
    ),
    BankPosition(
        "bank_179", "opening",
        "3rq1rk/Q3bp2/4pp2/7p/2Pp4/5nP1/PB3PKP/1R1B1R2 b - - 1 23", -42,
    ),
    BankPosition(
        "bank_180", "endgame",
        "8/3R4/4p3/8/2p1k2p/1P5P/5Kp1/8 w - - 4 39", 43,
    ),
    BankPosition(
        "bank_181", "endgame",
        "6k1/8/4p2P/7p/8/8/6K1/8 w - - 7 51", -26,
    ),
    BankPosition(
        "bank_182", "endgame",
        "8/8/5p2/k4P2/8/8/6K1/8 w - - 72 37", -2,
    ),
    BankPosition(
        "bank_183", "opening",
        "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3", -1,
    ),
    BankPosition(
        "bank_184", "middlegame",
        "rnb4r/p1pp2pp/2p3kn/4p3/4P3/2NP4/P4PPP/R1B1K1NR w KQ - 0 11", -1,
    ),
    BankPosition(
        "bank_185", "endgame",
        "8/3k4/5p2/5P2/8/5K2/8/8 w - - 44 23", 45,
    ),
    BankPosition(
        "bank_186", "middlegame",
        "4k2r/2p2p2/8/4p3/8/2K3P1/rB3P2/R5N1 w - - 4 26", 2,
    ),
    BankPosition(
        "bank_187", "opening",
        "2b1k1nr/rp1p2pp/p2Bp3/5p2/PQP5/8/4PP1q/1R2KBNR w K - 0 17", 32,
    ),
    BankPosition(
        "bank_188", "endgame",
        "4k3/8/8/7p/7P/8/8/1K6 b - - 60 49", 0,
    ),
    BankPosition(
        "bank_189", "opening",
        "r1bk1b1r/pp1ppp1p/n1p2Q2/q5B1/1P1Pn3/8/P1P1BPPP/RN2K1NR w KQ - 1 8", 25,
    ),
    BankPosition(
        "bank_190", "middlegame",
        "6k1/5p2/4r2p/6B1/rP6/8/8/1R2N2K b - - 0 50", 4,
    ),
    BankPosition(
        "bank_191", "middlegame",
        "r4k2/2p3pp/8/pN6/1p4PP/1P3r2/P3K3/R1B5 w - - 2 29", 8,
    ),
    BankPosition(
        "bank_192", "middlegame",
        "3rr3/pp1n1kpp/5n2/8/3P4/P7/1PP2PPP/R2N1RK1 b - - 1 19", -2,
    ),
    BankPosition(
        "bank_193", "endgame",
        "3k4/8/8/5p1p/5P1P/8/8/6K1 w - - 32 62", 3,
    ),
    BankPosition(
        "bank_194", "middlegame",
        "4k2r/1b1p1npp/p7/4pp2/P1P1P3/8/5P1B/3K1BNR w - - 0 22", 28,
    ),
    BankPosition(
        "bank_195", "opening",
        "r1rq2k1/pb1nbppp/1p2pn2/2pp4/2PP4/1PN1PNP1/PB2QPBP/2RR2K1 b - - 1 13", 15,
    ),
    BankPosition(
        "bank_196", "opening",
        "r1b1k1r1/1p3ppp/p1nqPn2/1N6/7N/2P5/P3QPPP/1R2KB1R b Kq - 0 15", 35,
    ),
    BankPosition(
        "bank_197", "middlegame",
        "2b3r1/3n4/n3Pppp/1P6/6k1/5N2/PP2PPPb/R3KB2 w - - 0 20", -39,
    ),
    BankPosition(
        "bank_198", "endgame",
        "8/6k1/5p2/5P2/8/8/8/3K4 b - - 51 26", 8,
    ),
    BankPosition(
        "bank_199", "endgame",
        "rk6/pp6/2p1B3/6p1/8/2K5/P7/R7 w - - 0 30", -16,
    ),
    BankPosition(
        "bank_200", "endgame",
        "8/2k5/5p2/5P2/8/5K2/8/8 w - - 66 34", 43,
    ),
)

def get_bank_positions() -> tuple[BankPosition, ...]:
    return PAIRED_TEST_BANK
