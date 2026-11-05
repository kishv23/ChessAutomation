#Author: Kishorekumar Vishwanathan
"""Benchmarks the trained engine against a random mover.

    python testing_vs_random.py --games 200
    python testing_vs_random.py --games 20 --engine random   # sanity check, no weights

Reports wins, draws, losses and average game length. The previous version
counted any exception as a loss and reused the loop variable for both games
and moves; errors are now reported separately.
"""
import argparse
import random
import statistics

import chess

from engine import NoLegalMoves, RandomEngine


def play_game(engine, rng, max_plies=300, engine_color=chess.WHITE):
    board = chess.Board()
    while not board.is_game_over() and board.ply() < max_plies:
        if board.turn == engine_color:
            board.push_uci(engine.best_move(board.fen()))
        else:
            board.push(rng.choice(list(board.legal_moves)))
    outcome = board.outcome()
    if outcome is None or outcome.winner is None:
        return "draw", board.ply()
    return ("win" if outcome.winner == engine_color else "loss"), board.ply()


def evaluate(engine, games=200, seed=0, max_plies=300):
    rng = random.Random(seed)
    tally = {"win": 0, "draw": 0, "loss": 0, "error": 0}
    lengths = []
    for g in range(games):
        color = chess.WHITE if g % 2 == 0 else chess.BLACK  # alternate colours for fairness
        try:
            result, plies = play_game(engine, rng, max_plies, color)
        except (NoLegalMoves, ValueError) as exc:
            print(f"game {g}: engine error: {exc}")
            tally["error"] += 1
            continue
        tally[result] += 1
        lengths.append(plies)
    tally["avg_plies"] = round(statistics.mean(lengths), 1) if lengths else 0
    return tally


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--games", type=int, default=200)
    p.add_argument("--engine", choices=["model", "random"], default="model")
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args()
    if args.engine == "random":
        engine = RandomEngine(seed=args.seed + 1)
    else:
        from engine import ModelEngine

        engine = ModelEngine()
    r = evaluate(engine, args.games, args.seed)
    print(f"Games: {args.games}  Wins: {r['win']}  Draws: {r['draw']}  Losses: {r['loss']}  Errors: {r['error']}  Avg plies: {r['avg_plies']}")


if __name__ == "__main__":
    main()
