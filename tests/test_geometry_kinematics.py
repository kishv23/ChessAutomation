import math

import pytest

from robot.geometry import BoardGeometry, Calibration
from robot.kinematics import ArmSpec, Joints, Unreachable, forward, inverse

SPEC = ArmSpec()


def test_square_centres_follow_calibration():
    g = BoardGeometry(Calibration(a1=(100.0, -100.0), h8=(310.0, 110.0)))
    assert g.square_xy("a1") == pytest.approx((100.0, -100.0))
    assert g.square_xy("h8") == pytest.approx((310.0, 110.0))
    assert g.square_size == pytest.approx(30.0)
    assert g.square_xy("h1") == pytest.approx((310.0, -100.0))


def test_rotated_board():
    # Board turned 90 degrees: files run along +y.
    g = BoardGeometry(Calibration(a1=(200.0, -100.0), h8=(-10.0, 110.0)))
    assert g.rotation == pytest.approx(math.pi / 2)
    assert g.square_xy("h1") == pytest.approx((200.0, 110.0))


def test_graveyard_fills_in_rows():
    cal = Calibration(graveyard_origin=(0.0, 0.0), graveyard_spacing=10.0, graveyard_columns=2)
    g = BoardGeometry(cal)
    assert [g.next_graveyard_xy() for _ in range(3)] == [(0.0, 0.0), (10.0, 0.0), (0.0, -10.0)]
    g.reset_graveyard()
    assert g.next_graveyard_xy() == (0.0, 0.0)


def test_calibration_roundtrip(tmp_path):
    cal = Calibration(a1=(1.0, 2.0), travel_z=99.0)
    path = tmp_path / "cal.json"
    cal.save(str(path))
    assert Calibration.load(str(path)) == cal


def test_coincident_calibration_points_rejected():
    with pytest.raises(ValueError):
        BoardGeometry(Calibration(a1=(1.0, 1.0), h8=(1.0, 1.0)))


@pytest.mark.parametrize("square", ["a1", "h1", "a8", "h8", "e4", "d5"])
@pytest.mark.parametrize("z", [25.0, 120.0])
def test_ik_reaches_every_board_square_and_fk_agrees(square, z):
    g = BoardGeometry(Calibration())
    x, y = g.square_xy(square)
    j = inverse(SPEC, x, y, z)
    assert forward(SPEC, j) == pytest.approx((x, y, z), abs=1e-6)


def test_gripper_stays_vertical():
    j = inverse(SPEC, 250.0, 40.0, 30.0)
    assert j.shoulder + j.elbow + j.wrist == pytest.approx(-math.pi / 2)


def test_out_of_reach_raises():
    with pytest.raises(Unreachable, match="reach"):
        inverse(SPEC, 900.0, 0.0, 0.0)


def test_joint_limits_enforced():
    tight = ArmSpec(limits=((-0.1, 0.1),) + ArmSpec().limits[1:])
    with pytest.raises(Unreachable, match="base"):
        inverse(tight, 0.0, 250.0, 30.0)


def test_degrees_helper():
    assert Joints(math.pi, 0, 0, -math.pi / 2).degrees() == {"base": 180.0, "shoulder": 0.0, "elbow": 0.0, "wrist": -90.0}


def test_default_layout_is_fully_reachable_at_grip_and_travel_height():
    cal = Calibration()
    g = BoardGeometry(cal)
    points = [g.square_xy(f"{f}{r}") for f in "abcdefgh" for r in "12345678"]
    points += [g.next_graveyard_xy() for _ in range(16)]  # every captured piece
    points += list(cal.reserve.values())
    for x, y in points:
        for z in (cal.board_z + 25.0, cal.travel_z):
            inverse(SPEC, x, y, z)
