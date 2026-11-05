"""Lightweight FEN parsing for the arm controller.

The robot only needs to know which square holds which piece, so this module
avoids a python-chess dependency and runs on a Raspberry Pi as-is.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

FILES = "abcdefgh"
PIECES = set("pnbrqkPNBRQK")


def square_index(name: str) -> int:
    """'a1' -> 0, 'h8' -> 63."""
    if len(name) != 2 or name[0] not in FILES or name[1] not in "12345678":
        raise ValueError(f"not a square: {name!r}")
    return (int(name[1]) - 1) * 8 + FILES.index(name[0])


def square_name(idx: int) -> str:
    if not 0 <= idx < 64:
        raise ValueError(f"square index out of range: {idx}")
    return f"{FILES[idx % 8]}{idx // 8 + 1}"


@dataclass(frozen=True)
class Position:
    squares: Dict[str, str]  # 'e1' -> 'K'
    white_to_move: bool
    en_passant: Optional[str]

    def piece_at(self, square: str) -> Optional[str]:
        return self.squares.get(square)

    @staticmethod
    def is_white(piece: str) -> bool:
        return piece.isupper()


def parse_fen(fen: str) -> Position:
    parts = fen.strip().split()
    if len(parts) < 2:
        raise ValueError("FEN needs at least piece placement and side to move")
    placement, turn = parts[0], parts[1]
    ranks = placement.split("/")
    if len(ranks) != 8:
        raise ValueError("FEN placement must have 8 ranks")

    squares: Dict[str, str] = {}
    for r, row in enumerate(ranks):
        rank = 8 - r
        file = 0
        for ch in row:
            if ch.isdigit():
                file += int(ch)
            elif ch in PIECES:
                if file > 7:
                    raise ValueError(f"rank {rank} overflows")
                squares[f"{FILES[file]}{rank}"] = ch
                file += 1
            else:
                raise ValueError(f"invalid FEN character {ch!r}")
        if file != 8:
            raise ValueError(f"rank {rank} has {file} files")
    if turn not in ("w", "b"):
        raise ValueError("side to move must be w or b")
    ep = parts[3] if len(parts) > 3 and parts[3] != "-" else None
    return Position(squares, turn == "w", ep)
