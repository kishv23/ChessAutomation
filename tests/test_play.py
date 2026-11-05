import pytest

chess = pytest.importorskip("chess")

from engine import RandomEngine  # noqa: E402
from play import parse_human_move, play  # noqa: E402
from robot.controller import ArmController  # noqa: E402
from robot.driver import SimulatedArm  # noqa: E402
from robot.geometry import BoardGeometry, Calibration  # noqa: E402


def test_parse_human_move_accepts_uci_and_san():
    b = chess.Board()
    assert parse_human_move(b, "e2e4").uci() == "e2e4"
    assert parse_human_move(b, "Nf3").uci() == "g1f3"
    with pytest.raises(ValueError):
        parse_human_move(b, "e2e5")


def test_robot_plays_a_whole_game_against_a_scripted_human():
    arm = SimulatedArm()
    controller = ArmController(arm, BoardGeometry(Calibration()))
    human = RandomEngine(seed=1)
    board = chess.Board()
    result = play(RandomEngine(seed=2), controller, chess.BLACK,
                  read=lambda _prompt: human.best_move(board.fen()), write=lambda _msg: None, board=board)
    assert result in ("1-0", "0-1", "1/2-1/2")
    assert board.is_game_over()
    assert any(kind == "move" for kind, _ in arm.log)


def test_resign():
    arm = SimulatedArm()
    controller = ArmController(arm, BoardGeometry(Calibration()))
    assert play(RandomEngine(), controller, chess.BLACK, read=lambda p: "resign", write=lambda m: None) == "0-1"
