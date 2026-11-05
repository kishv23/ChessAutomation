"""Turns a chess move into the physical pick-and-place steps the arm performs.

Handles the cases where one move touches more than one piece:
  capture       remove the captured piece to the graveyard first
  en passant    the captured pawn is not on the destination square
  castling      the rook moves as well as the king
  promotion     the pawn goes to the graveyard and a spare piece is placed
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from robot.board import Position, parse_fen

GRAVEYARD = "graveyard"
RESERVE = "reserve"  # tray holding spare queens, rooks, bishops and knights


@dataclass(frozen=True)
class Transfer:
    """Move one physical piece from `src` to `dst` (squares, graveyard or reserve)."""

    src: str
    dst: str
    piece: str
    reason: str


CASTLING_ROOKS = {
    ("e1", "g1"): ("h1", "f1"),
    ("e1", "c1"): ("a1", "d1"),
    ("e8", "g8"): ("h8", "f8"),
    ("e8", "c8"): ("a8", "d8"),
}


def plan_move(fen: str, uci: str) -> List[Transfer]:
    """Plans the transfers for `uci` played from position `fen`.

    The move is assumed legal (the engine or python-chess checks legality); this
    only works out which pieces have to be lifted and where they go.
    """
    pos: Position = parse_fen(fen)
    if len(uci) not in (4, 5):
        raise ValueError(f"not a UCI move: {uci!r}")
    src, dst, promo = uci[:2], uci[2:4], uci[4:] or None

    piece = pos.piece_at(src)
    if piece is None:
        raise ValueError(f"no piece on {src}")
    if pos.is_white(piece) != pos.white_to_move:
        raise ValueError(f"{piece} on {src} does not belong to the side to move")

    steps: List[Transfer] = []
    target = pos.piece_at(dst)
    is_pawn = piece.lower() == "p"

    if target is not None:
        if pos.is_white(target) == pos.is_white(piece):
            raise ValueError(f"{dst} holds a piece of the same colour")
        steps.append(Transfer(dst, GRAVEYARD, target, "capture"))
    elif is_pawn and src[0] != dst[0]:
        # Diagonal pawn move onto an empty square: en passant.
        captured_sq = dst[0] + src[1]
        captured = pos.piece_at(captured_sq)
        is_enemy_pawn = captured is not None and captured.lower() == "p" and pos.is_white(captured) != pos.is_white(piece)
        if not is_enemy_pawn or (pos.en_passant is not None and pos.en_passant != dst):
            raise ValueError(f"{uci} is a diagonal pawn move with nothing to capture")
        steps.append(Transfer(captured_sq, GRAVEYARD, captured, "en passant"))

    if promo:
        if not is_pawn or dst[1] not in "18":
            raise ValueError(f"{uci} is not a promotion")
        new_piece = promo.upper() if pos.is_white(piece) else promo.lower()
        steps.append(Transfer(src, GRAVEYARD, piece, "promotion"))
        steps.append(Transfer(RESERVE, dst, new_piece, "promotion"))
        return steps

    steps.append(Transfer(src, dst, piece, "move"))

    if piece.lower() == "k" and (src, dst) in CASTLING_ROOKS:
        r_src, r_dst = CASTLING_ROOKS[(src, dst)]
        rook = pos.piece_at(r_src)
        if rook is None or rook.lower() != "r":
            raise ValueError(f"castling {uci} but no rook on {r_src}")
        steps.append(Transfer(r_src, r_dst, rook, "castling"))
    return steps
