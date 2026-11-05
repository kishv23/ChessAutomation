import pytest

from robot.controller import ArmController
from robot.driver import ArmError, SerialArm, SimulatedArm
from robot.geometry import BoardGeometry, Calibration
from robot.kinematics import ArmSpec, Joints, Unreachable

START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


@pytest.fixture
def setup():
    arm = SimulatedArm()
    geometry = BoardGeometry(Calibration())
    return arm, geometry, ArmController(arm, geometry)


def tips(arm):
    """Fingertip positions after each move command."""
    from robot.kinematics import forward

    return [forward(arm.spec, j) for kind, j in arm.log if kind == "move"]


def test_quiet_move_picks_and_places_at_the_right_squares(setup):
    arm, geometry, ctl = setup
    ctl.play(START, "g1f3")
    path = tips(arm)
    gx, gy = geometry.square_xy("g1")
    fx, fy = geometry.square_xy("f3")
    grip_z = geometry.grip_z("N")
    assert path[1] == pytest.approx((gx, gy, grip_z), abs=1e-6)  # descend onto g1
    assert path[4] == pytest.approx((fx, fy, grip_z), abs=1e-6)  # descend onto f3
    assert [g for kind, g in arm.log if kind == "grip"] == [False, True, False]
    assert not arm.gripping


def test_all_horizontal_travel_happens_at_safe_height(setup):
    arm, geometry, ctl = setup
    ctl.play(START, "b1c3")
    path = tips(arm)
    for a, b in zip(path, path[1:]):
        moved_sideways = abs(a[0] - b[0]) > 1e-6 or abs(a[1] - b[1]) > 1e-6
        if moved_sideways:
            assert a[2] == pytest.approx(geometry.cal.travel_z) and b[2] == pytest.approx(geometry.cal.travel_z)


def test_capture_sends_piece_to_successive_graveyard_slots(setup):
    arm, geometry, ctl = setup
    fen = "rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2"
    ctl.play(fen, "e4d5")
    first_slot = geometry.cal.graveyard_origin
    drop = tips(arm)[4]
    assert drop[:2] == pytest.approx(first_slot)
    ctl.new_game()
    assert arm.log[-1] == ("home", None)


def test_unreachable_square_aborts_before_any_motion():
    arm = SimulatedArm()
    far = BoardGeometry(Calibration(a1=(400.0, -105.0), h8=(610.0, 105.0)))
    with pytest.raises(Unreachable):
        ArmController(arm, far).play(START, "e2e4")
    assert arm.log == []


class FakeSerial:
    def __init__(self, replies):
        self.replies, self.sent = list(replies), []

    def write(self, data):
        self.sent.append(data.decode())

    def readline(self):
        return (self.replies.pop(0) + "\n").encode() if self.replies else b""

    def close(self):
        pass


def test_serial_protocol():
    conn = FakeSerial(["ok", "ok", "ok"])
    arm = SerialArm("COM3", conn=conn)
    arm.move_joints(Joints(0.0, 1.5707963267948966, -1.5707963267948966, -1.5707963267948966))
    arm.grip(True)
    arm.home()
    assert conn.sent == ["J 0.00 90.00 -90.00 -90.00\n", "G 1\n", "H\n"]


def test_serial_errors_and_timeouts_raise():
    with pytest.raises(ArmError, match="limit switch"):
        SerialArm("x", conn=FakeSerial(["err limit switch"])).home()
    with pytest.raises(ArmError, match="timeout"):
        SerialArm("x", conn=FakeSerial([])).grip(False)
