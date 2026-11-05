"""Maps squares, the graveyard and the reserve tray to arm coordinates (mm).

Calibrate by jogging the gripper over the centres of a1 and h8 and recording
their (x, y). Everything else, including board rotation, follows from those
two points, so the board does not need to be squared up to the arm.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Tuple

from robot.board import FILES

Point = Tuple[float, float, float]

# Height of the grip point above the board surface, by piece type (mm).
DEFAULT_GRIP_HEIGHTS = {"p": 25.0, "n": 30.0, "b": 35.0, "r": 28.0, "q": 40.0, "k": 45.0}


@dataclass
class Calibration:
    # Defaults: 30 mm squares, board centred on the arm's x axis, a1 nearest the arm.
    a1: Tuple[float, float] = (90.0, -105.0)
    h8: Tuple[float, float] = (300.0, 105.0)
    board_z: float = 0.0
    travel_z: float = 120.0  # safe height for moving above pieces
    grip_heights: Dict[str, float] = field(default_factory=lambda: dict(DEFAULT_GRIP_HEIGHTS))
    graveyard_origin: Tuple[float, float] = (90.0, -160.0)
    graveyard_spacing: float = 28.0
    graveyard_columns: int = 8
    reserve: Dict[str, Tuple[float, float]] = field(
        default_factory=lambda: {"q": (335.0, -45.0), "r": (335.0, -15.0), "b": (335.0, 15.0), "n": (335.0, 45.0)}
    )

    @classmethod
    def load(cls, path: str) -> "Calibration":
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        raw["a1"], raw["h8"] = tuple(raw["a1"]), tuple(raw["h8"])
        raw["graveyard_origin"] = tuple(raw.get("graveyard_origin", cls().graveyard_origin))
        raw["reserve"] = {k: tuple(v) for k, v in raw.get("reserve", cls().reserve).items()}
        return cls(**raw)

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)


class BoardGeometry:
    def __init__(self, cal: Calibration):
        self.cal = cal
        ax, ay = cal.a1
        hx, hy = cal.h8
        # a1 -> h8 is 7 squares along each board axis, i.e. 7*sqrt(2) squares diagonally.
        diag = math.hypot(hx - ax, hy - ay)
        if diag < 1e-6:
            raise ValueError("a1 and h8 calibration points coincide")
        self.square_size = diag / (7 * math.sqrt(2))
        # The diagonal sits at 45 degrees to the files, so subtract that to get board rotation.
        self.rotation = math.atan2(hy - ay, hx - ax) - math.pi / 4
        self._graveyard_used = 0

    def _board_to_arm(self, file: float, rank: float) -> Tuple[float, float]:
        s, c = math.sin(self.rotation), math.cos(self.rotation)
        u, v = file * self.square_size, rank * self.square_size
        ax, ay = self.cal.a1
        return ax + u * c - v * s, ay + u * s + v * c

    def grip_z(self, piece: str) -> float:
        return self.cal.board_z + self.cal.grip_heights.get(piece.lower(), 30.0)

    def square_xy(self, square: str) -> Tuple[float, float]:
        return self._board_to_arm(FILES.index(square[0]), int(square[1]) - 1)

    def next_graveyard_xy(self) -> Tuple[float, float]:
        i = self._graveyard_used
        self._graveyard_used += 1
        col, row = i % self.cal.graveyard_columns, i // self.cal.graveyard_columns
        gx, gy = self.cal.graveyard_origin
        return gx + col * self.cal.graveyard_spacing, gy - row * self.cal.graveyard_spacing

    def reserve_xy(self, piece: str) -> Tuple[float, float]:
        try:
            return self.cal.reserve[piece.lower()]
        except KeyError:
            raise ValueError(f"no reserve slot for {piece!r}") from None

    def reset_graveyard(self) -> None:
        self._graveyard_used = 0

    def corners(self) -> List[Tuple[float, float]]:
        """Outer board corners, for reachability checks during calibration."""
        return [self._board_to_arm(f, r) for f, r in ((-0.5, -0.5), (7.5, -0.5), (7.5, 7.5), (-0.5, 7.5))]
