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
    board_holder = {}

    def read(_prompt):
        # The scripted human plays random legal moves on the same board the game uses.
        return human.best_move(board_holder["fen"])

    def write(msg):
        pass

    import play as play_module

    real_board = play_module.chess.Board

    class TrackedBoard(real_board):
        def push(self, move):
            super().push(move)
            board_holder["fen"] = self.fen()

    board_holder["fen"] = chess.STARTING_FEN
    play_module.chess.Board = TrackedBoard
    try:
        result = play(RandomEngine(seed=2), controller, chess.BLACK, read=read, write=write)
    finally:
        play_module.chess.Board = real_board
    assert result in ("1-0", "0-1", "1/2-1/2")
    assert any(kind == "move" for kind, _ in arm.log)


def test_resign():
    arm = SimulatedArm()
    controller = ArmController(arm, BoardGeometry(Calibration()))
    assert play(RandomEngine(), controller, chess.BLACK, read=lambda p: "resign", write=lambda m: None) == "0-1"
