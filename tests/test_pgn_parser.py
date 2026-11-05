import textwrap

import pytest

chess = pytest.importorskip("chess")
import pgn_data_parser as p  # noqa: E402

PGN = textwrap.dedent(
    """
    [Result "1-0"]

    1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# 1-0

    [Result "0-1"]

    1. f3 e5 2. g4 Qh4# 0-1

    [Result "1/2-1/2"]

    1. d4 d5 1/2-1/2
    """
)


@pytest.fixture
def pgn_file(tmp_path):
    path = tmp_path / "games.pgn"
    path.write_text(PGN)
    return str(path)


def test_flip_board_mirrors_ranks_and_swaps_colours():
    after_e4 = chess.Board()
    after_e4.push_uci("e2e4")
    flipped = chess.Board(p.flip_board(after_e4.fen()))
    assert flipped.piece_at(chess.E5) == chess.Piece(chess.PAWN, chess.BLACK)
    assert flipped.piece_at(chess.E1) == chess.Piece(chess.KING, chess.WHITE)
    assert flipped.turn == chess.WHITE


def test_mirror_move_keeps_promotion():
    m = p.mirror_move(chess.Move.from_uci("a2a1q"))
    assert m.uci() == "a7a8q"


def test_winner_moves_mirrored_for_black_are_legal_for_white(pgn_file):
    rows = p.extract_winner_data_from_pgn(pgn_file)
    black_rows = [r for r in rows if r[2] == "black"]
    assert len(black_rows) == 2  # e5 and Qh4#
    for fen, uci, _ in black_rows:
        board = chess.Board(fen)
        assert board.turn == chess.WHITE
        assert chess.Move.from_uci(uci) in board.legal_moves


def test_side_extraction_skips_draws_and_losses(pgn_file):
    white = p.extract_data_for_white(pgn_file)
    black = p.extract_data_for_black(pgn_file)
    assert [m for _, m, _ in white] == ["e2e4", "d1h5", "f1c4", "h5f7"]
    assert [m for _, m, _ in black] == ["e7e5", "d8h4"]


def test_moves_wanted_caps_output(pgn_file):
    assert len(p.extract_data_for_white(pgn_file, moves_wanted=2)) == 2


def test_progress_prints_once_per_threshold(capsys):
    last = 0
    for count in (99_999, 100_000, 100_000, 150_000, 200_001):
        last = p._progress(count, last)
    assert capsys.readouterr().out.count("Processed") == 2
