from calibrate import jog_to, reach_report
from robot.driver import SimulatedArm
from robot.geometry import Calibration


def test_default_calibration_has_no_reach_problems():
    assert reach_report(Calibration()) == []


def test_far_board_is_reported():
    problems = reach_report(Calibration(a1=(300.0, -105.0), h8=(510.0, 105.0)))
    assert problems and any(p.startswith("h8") for p in problems)


def test_jog_moves_and_returns_final_xy():
    arm = SimulatedArm()
    script = iter(["x+5", "y-2.5", "bogus", "z+10", "ok"])
    out = []
    xy = jog_to(arm, "a1", (100.0, -100.0, 40.0), read=lambda _p: next(script), write=out.append)
    assert xy == (105.0, -102.5)
    assert arm.tip[2] == 50.0
    assert "  unknown command" in out
