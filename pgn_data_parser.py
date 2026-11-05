##Author: Kishorekumar Vishwanathan
"""Extracts (FEN, UCI move) training pairs from Lichess PGN dumps.

    python pgn_data_parser.py LichessEliteDatabase/lichess_elite_2017-11.pgn --moves 400000

Writes one CSV per side under data/rawData/{white,black}/ containing only the
moves made by the side that went on to win the game.
"""
import argparse
import os

import chess
import chess.pgn
import pandas as pd

PROGRESS_EVERY = 100_000


def mirror_move(move: chess.Move) -> chess.Move:
    """Reflects a move across the board's horizontal axis (e7e5 becomes e2e4)."""
    return chess.Move(
        chess.square_mirror(move.from_square),
        chess.square_mirror(move.to_square),
        promotion=move.promotion,
    )


def flip_board(fen: str) -> str:
    """Returns the position from the other side's point of view.

    Ranks are mirrored and piece colours swapped, so a Black-to-move position
    becomes the equivalent White-to-move position. The previous version only
    reversed the piece string, which rotated the board 180 degrees without
    swapping colours.
    """
    return chess.Board(fen).mirror().fen()


def _progress(count: int, last_reported: int) -> int:
    """Prints once per PROGRESS_EVERY moves instead of on every loop pass."""
    if count // PROGRESS_EVERY > last_reported // PROGRESS_EVERY:
        print("Processed", count, "moves")
        return count
    return last_reported


def _games(pgn_file):
    with open(pgn_file, encoding="utf-8", errors="replace") as f:
        while True:
            game = chess.pgn.read_game(f)
            if game is None:
                return
            yield game


def extract_data_from_pgn(pgn_file):
    """Every (FEN, move) pair from every game."""
    print("Processing PGN file:", pgn_file)
    data, reported = [], 0
    for game in _games(pgn_file):
        board = game.board()
        for move in game.mainline_moves():
            data.append((board.fen(), move.uci()))
            board.push(move)
        reported = _progress(len(data), reported)
    print("*** Final count of processed moves is:", len(data), "***")
    return data


def extract_winner_data_from_pgn(pgn_file, normalise_to_white=True):
    """Moves played by the eventual winner. Black's moves can be mirrored to White's view."""
    print("Processing PGN file:", pgn_file)
    data, reported = [], 0
    for game in _games(pgn_file):
        result = game.headers.get("Result")
        if result not in ("1-0", "0-1"):
            continue
        winner = chess.WHITE if result == "1-0" else chess.BLACK
        board = game.board()
        for move in game.mainline_moves():
            if board.turn == winner:
                if winner == chess.BLACK and normalise_to_white:
                    data.append((board.mirror().fen(), mirror_move(move).uci(), "black"))
                else:
                    data.append((board.fen(), move.uci(), "white" if winner == chess.WHITE else "black"))
            board.push(move)
        reported = _progress(len(data), reported)
    print("*** Final count of processed moves is:", len(data), "***")
    return data


def extract_data_for_side(pgn_file, side: chess.Color, moves_wanted=400_000):
    """Moves made by `side` in games that `side` won, in the original orientation."""
    print("Processing PGN file:", pgn_file)
    wanted_result = "1-0" if side == chess.WHITE else "0-1"
    label = "white" if side == chess.WHITE else "black"
    data, reported = [], 0
    for game in _games(pgn_file):
        if len(data) >= moves_wanted:
            break
        if game.headers.get("Result") != wanted_result:
            continue
        board = game.board()
        for move in game.mainline_moves():
            if board.turn == side:
                data.append((board.fen(), move.uci(), label))
            board.push(move)
        reported = _progress(len(data), reported)
    data = data[:moves_wanted]
    print(f"*** Final count of processed moves for {label.upper()} is:", len(data), "***")
    return data


def extract_data_for_white(pgn_file, moves_wanted=400_000):
    return extract_data_for_side(pgn_file, chess.WHITE, moves_wanted)


def extract_data_for_black(pgn_file, moves_wanted=400_000):
    return extract_data_for_side(pgn_file, chess.BLACK, moves_wanted)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pgn", help="path to a PGN file")
    parser.add_argument("--moves", type=int, default=400_000, help="moves to keep per side")
    parser.add_argument("--out", default="data/rawData", help="output directory")
    parser.add_argument("--tag", default="", help="suffix for the CSV file names")
    args = parser.parse_args()

    columns = ["FEN Position", "UCI Move", "Winner"]
    for side, name in ((chess.WHITE, "white"), (chess.BLACK, "black")):
        rows = extract_data_for_side(args.pgn, side, args.moves)
        os.makedirs(os.path.join(args.out, name), exist_ok=True)
        path = os.path.join(args.out, name, f"chess_{name}_data{args.tag}.csv")
        pd.DataFrame(rows, columns=columns).to_csv(path, index=False)
        print("Saved", len(rows), "rows to", path)


if __name__ == "__main__":
    main()
