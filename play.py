#Author: Kishorekumar Vishwanathan
"""Human vs robot.

The human moves a piece on the physical board and types the move (UCI like
e7e5 or SAN like Nf6). The engine replies and the arm plays its move.

    python play.py --sim                          # simulated arm, prints joint angles
    python play.py --port /dev/ttyUSB0 --cal calibration.local.json
    python play.py --sim --engine random --robot-color white
"""
import argparse
import logging

import chess

from engine import NoLegalMoves, RandomEngine
from robot.controller import ArmController
from robot.driver import SerialArm, SimulatedArm
from robot.geometry import BoardGeometry, Calibration


def parse_human_move(board: chess.Board, text: str) -> chess.Move:
    text = text.strip()
    for parse in (board.parse_uci, board.parse_san):
        try:
            return parse(text)
        except ValueError:
            continue
    raise ValueError(f"{text!r} is not a legal move here")


def robot_turn(board, engine, controller):
    uci = engine.best_move(board.fen())
    move = chess.Move.from_uci(uci)
    if move not in board.legal_moves:
        raise RuntimeError(f"engine returned illegal move {uci}")
    san = board.san(move)
    controller.play(board.fen(), uci)
    board.push(move)
    return san


def play(engine, controller, robot_color=chess.BLACK, read=input, write=print, board=None):
    board = board if board is not None else chess.Board()
    controller.new_game()
    while not board.is_game_over():
        if board.turn == robot_color:
            try:
                write(f"Robot plays {robot_turn(board, engine, controller)}")
            except NoLegalMoves:
                break
            continue
        write(board.unicode(invert_color=True, borders=False) if hasattr(board, "unicode") else str(board))
        text = read("Your move (or 'resign'): ")
        if text.strip().lower() in ("resign", "quit"):
            write("You resigned.")
            return "1-0" if robot_color == chess.WHITE else "0-1"
        try:
            board.push(parse_human_move(board, text))
        except ValueError as exc:
            write(str(exc))
    write(f"Game over: {board.result()}")
    return board.result()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sim", action="store_true", help="use the simulated arm")
    p.add_argument("--port", help="serial port of the arm controller")
    p.add_argument("--cal", help="calibration JSON (see calibrate.py)")
    p.add_argument("--engine", choices=["model", "random"], default="model")
    p.add_argument("--robot-color", choices=["white", "black"], default="black")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not args.sim and not args.port:
        p.error("pass --sim or --port")
    driver = SimulatedArm() if args.sim else SerialArm(args.port)
    geometry = BoardGeometry(Calibration.load(args.cal) if args.cal else Calibration())
    if args.engine == "random":
        engine = RandomEngine()
    else:
        from engine import ModelEngine

        engine = ModelEngine()
    play(engine, ArmController(driver, geometry), chess.WHITE if args.robot_color == "white" else chess.BLACK)


if __name__ == "__main__":
    main()
