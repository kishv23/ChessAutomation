import pytest

from robot.board import parse_fen, square_index, square_name
from robot.planner import GRAVEYARD, RESERVE, plan_move

START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def test_square_index_roundtrip():
    assert square_index("a1") == 0 and square_index("h8") == 63
    assert all(square_name(square_index(f"{f}{r}")) == f"{f}{r}" for f in "abcdefgh" for r in "12345678")
    with pytest.raises(ValueError):
        square_index("i9")


def test_parse_fen_start_position():
    pos = parse_fen(START)
    assert len(pos.squares) == 32
    assert pos.piece_at("e1") == "K" and pos.piece_at("d8") == "q"
    assert pos.white_to_move and pos.en_passant is None


@pytest.mark.parametrize("fen", ["8/8/8/8/8/8/8 w - - 0 1", "9/8/8/8/8/8/8/8 w - - 0 1", "8/8/8/8/8/8/8/7X w - - 0 1", "8/8/8/8/8/8/8/8 x"])
def test_parse_fen_rejects_malformed(fen):
    with pytest.raises(ValueError):
        parse_fen(fen)


def test_quiet_move_is_one_transfer():
    [t] = plan_move(START, "g1f3")
    assert (t.src, t.dst, t.piece) == ("g1", "f3", "N")


def test_capture_clears_target_first():
    fen = "rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2"
    steps = plan_move(fen, "e4d5")
    assert [(s.src, s.dst) for s in steps] == [("d5", GRAVEYARD), ("e4", "d5")]


def test_en_passant_removes_the_passed_pawn():
    fen = "rnbqkbnr/ppp1p1pp/8/3pPp2/8/8/PPPP1PPP/RNBQKBNR w KQkq f6 0 3"
    steps = plan_move(fen, "e5f6")
    assert steps[0].src == "f5" and steps[0].reason == "en passant"
    assert (steps[1].src, steps[1].dst) == ("e5", "f6")


@pytest.mark.parametrize(
    "fen,uci,rook",
    [
        ("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", "e1g1", ("h1", "f1")),
        ("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", "e1c1", ("a1", "d1")),
        ("r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1", "e8g8", ("h8", "f8")),
    ],
)
def test_castling_moves_the_rook(fen, uci, rook):
    steps = plan_move(fen, uci)
    assert (steps[-1].src, steps[-1].dst) == rook and steps[-1].reason == "castling"


def test_promotion_swaps_the_pawn_for_a_reserve_piece():
    steps = plan_move("8/P7/8/8/8/8/8/k6K w - - 0 1", "a7a8q")
    assert [(s.src, s.dst, s.piece) for s in steps] == [("a7", GRAVEYARD, "P"), (RESERVE, "a8", "Q")]


def test_black_capture_promotion():
    fen = "7K/8/8/8/8/8/1p6/R6k b - - 0 1"
    steps = plan_move(fen, "b2a1n")
    assert [(s.src, s.dst, s.piece) for s in steps] == [("a1", GRAVEYARD, "R"), ("b2", GRAVEYARD, "p"), (RESERVE, "a1", "n")]


@pytest.mark.parametrize(
    "uci,msg",
    [("e3e4", "no piece"), ("e7e5", "side to move"), ("e1d1", "same colour"), ("e2d3", "nothing to capture"), ("g1f3q", "not a promotion")],
)
def test_rejects_impossible_moves(uci, msg):
    with pytest.raises(ValueError, match=msg):
        plan_move(START, uci)
