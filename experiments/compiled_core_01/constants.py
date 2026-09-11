"""Shared numeric constants for the MilkyWay engine.

All evaluation scores are centipawns. Mate scores live far outside the
positional range so they can never collide with a normal evaluation.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

# Score domains.
MATE_SCORE: int = 100000
INF: int = 1000000
DRAW_SCORE: int = 0

# Material values in centipawns (middlegame baseline).
PAWN_VALUE: int = 100
KNIGHT_VALUE: int = 320
BISHOP_VALUE: int = 330
ROOK_VALUE: int = 500
QUEEN_VALUE: int = 900
KING_VALUE: int = 0

# Game-phase weights (N=1, B=1, R=2, Q=4 per side, max 24).
PHASE_WEIGHT_PAWN: int = 0
PHASE_WEIGHT_KNIGHT: int = 1
PHASE_WEIGHT_BISHOP: int = 1
PHASE_WEIGHT_ROOK: int = 2
PHASE_WEIGHT_QUEEN: int = 4
MAX_PHASE: int = 24

# Search limits.
MAX_PLY: int = 64
MAX_QPLY: int = 12

# Transposition-table bounds.
EXACT: int = 0
LOWER: int = 1
UPPER: int = 2

# --- Piece-square tables (a8..h1 order, white perspective) -------------------
# Simplified Evaluation Function (Tomasz Michniewski, public domain style
# values widely used by open-source engines) with a separate endgame king
# and pawn table. These are our own numbers-in-code, tuned later in M16.

PAWN_MG: tuple[int, ...] = (
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    50,
    50,
    50,
    50,
    50,
    50,
    50,
    50,
    10,
    10,
    20,
    30,
    30,
    20,
    10,
    10,
    5,
    5,
    10,
    25,
    25,
    10,
    5,
    5,
    0,
    0,
    0,
    20,
    20,
    0,
    0,
    0,
    5,
    -5,
    -10,
    0,
    0,
    -10,
    -5,
    5,
    5,
    10,
    10,
    -20,
    -20,
    10,
    10,
    5,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
)

PAWN_EG: tuple[int, ...] = (
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    50,
    50,
    50,
    50,
    50,
    50,
    50,
    50,
    30,
    30,
    30,
    30,
    30,
    30,
    30,
    30,
    20,
    20,
    20,
    20,
    20,
    20,
    20,
    20,
    15,
    15,
    15,
    15,
    15,
    15,
    15,
    15,
    10,
    10,
    10,
    10,
    10,
    10,
    10,
    10,
    5,
    5,
    5,
    5,
    5,
    5,
    5,
    5,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
)

KNIGHT_PST: tuple[int, ...] = (
    -50,
    -40,
    -30,
    -30,
    -30,
    -30,
    -40,
    -50,
    -40,
    -20,
    0,
    0,
    0,
    0,
    -20,
    -40,
    -30,
    0,
    10,
    15,
    15,
    10,
    0,
    -30,
    -30,
    5,
    15,
    20,
    20,
    15,
    5,
    -30,
    -30,
    0,
    15,
    20,
    20,
    15,
    0,
    -30,
    -30,
    5,
    10,
    15,
    15,
    10,
    5,
    -30,
    -40,
    -20,
    0,
    5,
    5,
    0,
    -20,
    -40,
    -50,
    -40,
    -30,
    -30,
    -30,
    -30,
    -40,
    -50,
)

BISHOP_PST: tuple[int, ...] = (
    -20,
    -10,
    -10,
    -10,
    -10,
    -10,
    -10,
    -20,
    -10,
    0,
    0,
    0,
    0,
    0,
    0,
    -10,
    -10,
    0,
    5,
    10,
    10,
    5,
    0,
    -10,
    -10,
    5,
    5,
    10,
    10,
    5,
    5,
    -10,
    -10,
    0,
    10,
    10,
    10,
    10,
    0,
    -10,
    -10,
    10,
    10,
    10,
    10,
    10,
    10,
    -10,
    -10,
    5,
    0,
    0,
    0,
    0,
    5,
    -10,
    -20,
    -10,
    -10,
    -10,
    -10,
    -10,
    -10,
    -20,
)

ROOK_PST: tuple[int, ...] = (
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    5,
    10,
    10,
    10,
    10,
    10,
    10,
    5,
    -5,
    0,
    0,
    0,
    0,
    0,
    0,
    -5,
    -5,
    0,
    0,
    0,
    0,
    0,
    0,
    -5,
    -5,
    0,
    0,
    0,
    0,
    0,
    0,
    -5,
    -5,
    0,
    0,
    0,
    0,
    0,
    0,
    -5,
    -5,
    0,
    0,
    0,
    0,
    0,
    0,
    -5,
    0,
    0,
    0,
    5,
    5,
    0,
    0,
    0,
)

QUEEN_PST: tuple[int, ...] = (
    -20,
    -10,
    -10,
    -5,
    -5,
    -10,
    -10,
    -20,
    -10,
    0,
    0,
    0,
    0,
    0,
    0,
    -10,
    -10,
    0,
    5,
    5,
    5,
    5,
    0,
    -10,
    -5,
    0,
    5,
    5,
    5,
    5,
    0,
    -5,
    0,
    0,
    5,
    5,
    5,
    5,
    0,
    -5,
    -10,
    5,
    5,
    5,
    5,
    5,
    0,
    -10,
    -10,
    0,
    5,
    0,
    0,
    0,
    0,
    -10,
    -20,
    -10,
    -10,
    -5,
    -5,
    -10,
    -10,
    -20,
)

KING_MG: tuple[int, ...] = (
    -30,
    -40,
    -40,
    -50,
    -50,
    -40,
    -40,
    -30,
    -30,
    -40,
    -40,
    -50,
    -50,
    -40,
    -40,
    -30,
    -30,
    -40,
    -40,
    -50,
    -50,
    -40,
    -40,
    -30,
    -30,
    -40,
    -40,
    -50,
    -50,
    -40,
    -40,
    -30,
    -20,
    -30,
    -30,
    -40,
    -40,
    -30,
    -30,
    -20,
    -10,
    -20,
    -20,
    -20,
    -20,
    -20,
    -20,
    -10,
    20,
    20,
    0,
    0,
    0,
    0,
    20,
    20,
    20,
    30,
    10,
    0,
    0,
    10,
    30,
    20,
)

KING_EG: tuple[int, ...] = (
    -50,
    -40,
    -30,
    -20,
    -20,
    -30,
    -40,
    -50,
    -30,
    -20,
    -10,
    0,
    0,
    -10,
    -20,
    -30,
    -30,
    -10,
    20,
    30,
    30,
    20,
    -10,
    -30,
    -30,
    -10,
    30,
    40,
    40,
    30,
    -10,
    -30,
    -30,
    -10,
    30,
    40,
    40,
    30,
    -10,
    -30,
    -30,
    -10,
    20,
    30,
    30,
    20,
    -10,
    -30,
    -30,
    -30,
    0,
    0,
    0,
    0,
    -30,
    -30,
    -50,
    -30,
    -30,
    -30,
    -30,
    -30,
    -30,
    -50,
)

# Evaluation coefficients (tunable in M16; conservative v1 values).
BISHOP_PAIR_MG: int = 25
BISHOP_PAIR_EG: int = 45

DOUBLED_PAWN_MG: int = -12
DOUBLED_PAWN_EG: int = -18
ISOLATED_PAWN_MG: int = -14
ISOLATED_PAWN_EG: int = -20
BACKWARD_PAWN_MG: int = -8
BACKWARD_PAWN_EG: int = -12
CONNECTED_PAWN_MG: int = 8
CONNECTED_PAWN_EG: int = 6

# Passed-pawn bonus by advancement rank index 0..7 (rank 1..8 for white).
PASSED_PAWN_MG: tuple[int, ...] = (0, 5, 12, 22, 38, 60, 95, 0)
PASSED_PAWN_EG: tuple[int, ...] = (0, 10, 22, 40, 70, 110, 160, 0)
PROTECTED_PASSER_MG: int = 12
PROTECTED_PASSER_EG: int = 18

ROOK_OPEN_FILE_MG: int = 16
ROOK_OPEN_FILE_EG: int = 10
ROOK_SEMI_OPEN_MG: int = 9
ROOK_SEMI_OPEN_EG: int = 6
ROOK_SEVENTH_MG: int = 18
ROOK_SEVENTH_EG: int = 24
ROOK_CONNECTED_MG: int = 10
ROOK_BEHIND_PASSER_MG: int = 14
ROOK_BEHIND_PASSER_EG: int = 20

# Mobility: centipawns per attacked square (lightweight, attacks-based).
MOBILITY_KNIGHT: int = 3
MOBILITY_BISHOP: int = 3
MOBILITY_ROOK: int = 2
MOBILITY_QUEEN: int = 1

# King safety (middlegame-weighted).
KING_SHIELD_MISSING: int = -14
KING_OPEN_FILE_NEAR: int = -18
KING_ATTACK_UNIT: int = -9
KING_MAX_SAFETY: int = -120

# Mop-up (clearly winning): drive enemy king to edge, approach with own king.
MOP_EDGE_WEIGHT: int = 8
MOP_PROXIMITY_WEIGHT: int = 10
MOP_THRESHOLD: int = 350

TUNABLE_PARAM_NAMES: tuple[str, ...] = (
    # Material (12)
    "pawn_value_mg",
    "pawn_value_eg",
    "knight_value_mg",
    "knight_value_eg",
    "bishop_value_mg",
    "bishop_value_eg",
    "rook_value_mg",
    "rook_value_eg",
    "queen_value_mg",
    "queen_value_eg",
    "bishop_pair_mg",
    "bishop_pair_eg",
    # Mobility (4)
    "mobility_knight",
    "mobility_bishop",
    "mobility_rook",
    "mobility_queen",
    # Pawn structure (8)
    "doubled_pawn_mg",
    "doubled_pawn_eg",
    "isolated_pawn_mg",
    "isolated_pawn_eg",
    "backward_pawn_mg",
    "backward_pawn_eg",
    "connected_pawn_mg",
    "connected_pawn_eg",
    # Passed pawns by rank 2..7 (12)
    "passed_pawn_mg_r2",
    "passed_pawn_mg_r3",
    "passed_pawn_mg_r4",
    "passed_pawn_mg_r5",
    "passed_pawn_mg_r6",
    "passed_pawn_mg_r7",
    "passed_pawn_eg_r2",
    "passed_pawn_eg_r3",
    "passed_pawn_eg_r4",
    "passed_pawn_eg_r5",
    "passed_pawn_eg_r6",
    "passed_pawn_eg_r7",
    # Protected passers (2)
    "protected_passer_mg",
    "protected_passer_eg",
    # Rook activity (9)
    "rook_open_file_mg",
    "rook_open_file_eg",
    "rook_semi_open_mg",
    "rook_semi_open_eg",
    "rook_seventh_mg",
    "rook_seventh_eg",
    "rook_connected_mg",
    "rook_behind_passer_mg",
    "rook_behind_passer_eg",
    # King safety (3)
    "king_shield_missing",
    "king_open_file_near",
    "king_attack_unit",
)


@dataclass(frozen=True)
class EvalParameters:
    """Complete, immutable evaluation configuration for MilkyWay."""

    # Material
    pawn_value_mg: int = PAWN_VALUE
    pawn_value_eg: int = PAWN_VALUE
    knight_value_mg: int = KNIGHT_VALUE
    knight_value_eg: int = KNIGHT_VALUE
    bishop_value_mg: int = BISHOP_VALUE
    bishop_value_eg: int = BISHOP_VALUE
    rook_value_mg: int = ROOK_VALUE
    rook_value_eg: int = ROOK_VALUE
    queen_value_mg: int = QUEEN_VALUE
    queen_value_eg: int = QUEEN_VALUE
    bishop_pair_mg: int = BISHOP_PAIR_MG
    bishop_pair_eg: int = BISHOP_PAIR_EG

    # Mobility
    mobility_knight: int = MOBILITY_KNIGHT
    mobility_bishop: int = MOBILITY_BISHOP
    mobility_rook: int = MOBILITY_ROOK
    mobility_queen: int = MOBILITY_QUEEN

    # Pawn structure
    doubled_pawn_mg: int = DOUBLED_PAWN_MG
    doubled_pawn_eg: int = DOUBLED_PAWN_EG
    isolated_pawn_mg: int = ISOLATED_PAWN_MG
    isolated_pawn_eg: int = ISOLATED_PAWN_EG
    backward_pawn_mg: int = BACKWARD_PAWN_MG
    backward_pawn_eg: int = BACKWARD_PAWN_EG
    connected_pawn_mg: int = CONNECTED_PAWN_MG
    connected_pawn_eg: int = CONNECTED_PAWN_EG
    passed_pawn_mg: tuple[int, ...] = PASSED_PAWN_MG
    passed_pawn_eg: tuple[int, ...] = PASSED_PAWN_EG
    protected_passer_mg: int = PROTECTED_PASSER_MG
    protected_passer_eg: int = PROTECTED_PASSER_EG

    # Rook activity
    rook_open_file_mg: int = ROOK_OPEN_FILE_MG
    rook_open_file_eg: int = ROOK_OPEN_FILE_EG
    rook_semi_open_mg: int = ROOK_SEMI_OPEN_MG
    rook_semi_open_eg: int = ROOK_SEMI_OPEN_EG
    rook_seventh_mg: int = ROOK_SEVENTH_MG
    rook_seventh_eg: int = ROOK_SEVENTH_EG
    rook_connected_mg: int = ROOK_CONNECTED_MG
    rook_behind_passer_mg: int = ROOK_BEHIND_PASSER_MG
    rook_behind_passer_eg: int = ROOK_BEHIND_PASSER_EG

    # King safety
    king_shield_missing: int = KING_SHIELD_MISSING
    king_open_file_near: int = KING_OPEN_FILE_NEAR
    king_attack_unit: int = KING_ATTACK_UNIT
    king_max_safety: int = KING_MAX_SAFETY
    king_safety_variant: str = "A"

    # Mop-up
    mop_edge_weight: int = MOP_EDGE_WEIGHT
    mop_proximity_weight: int = MOP_PROXIMITY_WEIGHT
    mop_threshold: int = MOP_THRESHOLD

    # Piece-Square Tables (white perspective a8..h1)
    pawn_mg_pst: tuple[int, ...] = PAWN_MG
    pawn_eg_pst: tuple[int, ...] = PAWN_EG
    knight_pst: tuple[int, ...] = KNIGHT_PST
    bishop_pst: tuple[int, ...] = BISHOP_PST
    rook_pst: tuple[int, ...] = ROOK_PST
    queen_pst: tuple[int, ...] = QUEEN_PST
    king_mg_pst: tuple[int, ...] = KING_MG
    king_eg_pst: tuple[int, ...] = KING_EG

    def get_tunable_vector(self) -> list[float]:
        """Return the vector of first-stage tunable coefficients."""
        return [
            float(self.pawn_value_mg),
            float(self.pawn_value_eg),
            float(self.knight_value_mg),
            float(self.knight_value_eg),
            float(self.bishop_value_mg),
            float(self.bishop_value_eg),
            float(self.rook_value_mg),
            float(self.rook_value_eg),
            float(self.queen_value_mg),
            float(self.queen_value_eg),
            float(self.bishop_pair_mg),
            float(self.bishop_pair_eg),
            float(self.mobility_knight),
            float(self.mobility_bishop),
            float(self.mobility_rook),
            float(self.mobility_queen),
            float(self.doubled_pawn_mg),
            float(self.doubled_pawn_eg),
            float(self.isolated_pawn_mg),
            float(self.isolated_pawn_eg),
            float(self.backward_pawn_mg),
            float(self.backward_pawn_eg),
            float(self.connected_pawn_mg),
            float(self.connected_pawn_eg),
            float(self.passed_pawn_mg[1]),
            float(self.passed_pawn_mg[2]),
            float(self.passed_pawn_mg[3]),
            float(self.passed_pawn_mg[4]),
            float(self.passed_pawn_mg[5]),
            float(self.passed_pawn_mg[6]),
            float(self.passed_pawn_eg[1]),
            float(self.passed_pawn_eg[2]),
            float(self.passed_pawn_eg[3]),
            float(self.passed_pawn_eg[4]),
            float(self.passed_pawn_eg[5]),
            float(self.passed_pawn_eg[6]),
            float(self.protected_passer_mg),
            float(self.protected_passer_eg),
            float(self.rook_open_file_mg),
            float(self.rook_open_file_eg),
            float(self.rook_semi_open_mg),
            float(self.rook_semi_open_eg),
            float(self.rook_seventh_mg),
            float(self.rook_seventh_eg),
            float(self.rook_connected_mg),
            float(self.rook_behind_passer_mg),
            float(self.rook_behind_passer_eg),
            float(self.king_shield_missing),
            float(self.king_open_file_near),
            float(self.king_attack_unit),
        ]

    def with_tunable_vector(self, vec: list[float] | tuple[float, ...]) -> EvalParameters:
        """Construct a new EvalParameters instance replacing tunable parameters with vec."""
        if len(vec) != len(TUNABLE_PARAM_NAMES):
            msg = f"Expected vector of length {len(TUNABLE_PARAM_NAMES)}, got {len(vec)}"
            raise ValueError(msg)
        iv = [round(v) for v in vec]
        new_passed_mg = (0, iv[24], iv[25], iv[26], iv[27], iv[28], iv[29], 0)
        new_passed_eg = (0, iv[30], iv[31], iv[32], iv[33], iv[34], iv[35], 0)
        return EvalParameters(
            pawn_value_mg=iv[0],
            pawn_value_eg=iv[1],
            knight_value_mg=iv[2],
            knight_value_eg=iv[3],
            bishop_value_mg=iv[4],
            bishop_value_eg=iv[5],
            rook_value_mg=iv[6],
            rook_value_eg=iv[7],
            queen_value_mg=iv[8],
            queen_value_eg=iv[9],
            bishop_pair_mg=iv[10],
            bishop_pair_eg=iv[11],
            mobility_knight=iv[12],
            mobility_bishop=iv[13],
            mobility_rook=iv[14],
            mobility_queen=iv[15],
            doubled_pawn_mg=iv[16],
            doubled_pawn_eg=iv[17],
            isolated_pawn_mg=iv[18],
            isolated_pawn_eg=iv[19],
            backward_pawn_mg=iv[20],
            backward_pawn_eg=iv[21],
            connected_pawn_mg=iv[22],
            connected_pawn_eg=iv[23],
            passed_pawn_mg=new_passed_mg,
            passed_pawn_eg=new_passed_eg,
            protected_passer_mg=iv[36],
            protected_passer_eg=iv[37],
            rook_open_file_mg=iv[38],
            rook_open_file_eg=iv[39],
            rook_semi_open_mg=iv[40],
            rook_semi_open_eg=iv[41],
            rook_seventh_mg=iv[42],
            rook_seventh_eg=iv[43],
            rook_connected_mg=iv[44],
            rook_behind_passer_mg=iv[45],
            rook_behind_passer_eg=iv[46],
            king_shield_missing=iv[47],
            king_open_file_near=iv[48],
            king_attack_unit=iv[49],
            king_max_safety=self.king_max_safety,
            king_safety_variant=self.king_safety_variant,
            mop_edge_weight=self.mop_edge_weight,
            mop_proximity_weight=self.mop_proximity_weight,
            mop_threshold=self.mop_threshold,
            pawn_mg_pst=self.pawn_mg_pst,
            pawn_eg_pst=self.pawn_eg_pst,
            knight_pst=self.knight_pst,
            bishop_pst=self.bishop_pst,
            rook_pst=self.rook_pst,
            queen_pst=self.queen_pst,
            king_mg_pst=self.king_mg_pst,
            king_eg_pst=self.king_eg_pst,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> EvalParameters:
        # Reconstruct tuples
        tuple_fields = (
            "passed_pawn_mg", "passed_pawn_eg",
            "pawn_mg_pst", "pawn_eg_pst", "knight_pst", "bishop_pst",
            "rook_pst", "queen_pst", "king_mg_pst", "king_eg_pst",
        )
        kwargs = dict(d)
        for tf in tuple_fields:
            if tf in kwargs:
                kwargs[tf] = tuple(kwargs[tf])
        return cls(**kwargs)

    @classmethod
    def from_json(cls, s: str) -> EvalParameters:
        return cls.from_dict(json.loads(s))


MW_0_2_EVAL: EvalParameters = EvalParameters()

# Candidate M16-huber-01: Tuned offline grouped parameters via standardized robust Huber regression
M16_HUBER_01: EvalParameters = EvalParameters(
    pawn_value_mg=101,
    knight_value_mg=319,
    knight_value_eg=318,
    bishop_value_mg=328,
    bishop_value_eg=328,
    rook_value_mg=493,
    rook_value_eg=498,
    queen_value_mg=892,
    queen_value_eg=889,
    bishop_pair_mg=24,
    bishop_pair_eg=42,
    doubled_pawn_mg=-11,
    backward_pawn_mg=-9,
    passed_pawn_mg=(0, 4, 11, 19, 38, 62, 113, 0),
    passed_pawn_eg=(0, 10, 22, 40, 71, 110, 161, 0),
    protected_passer_mg=10,
    rook_open_file_mg=12,
    rook_semi_open_mg=6,
    rook_semi_open_eg=0,
    rook_seventh_mg=15,
    rook_behind_passer_mg=15,
    rook_behind_passer_eg=18,
    king_attack_unit=-8,
)

# Ablation candidate: KS-B (simplified king safety without 9 is_attacked_by loops)
MW_0_2_KS_B: EvalParameters = EvalParameters(king_safety_variant="B")

# Ablation candidate: KS-C (cheaper bitboard king zone attacks without is_attacked_by loops)
MW_0_2_KS_C: EvalParameters = EvalParameters(king_safety_variant="C")


