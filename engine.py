#Author: Kishorekumar Vishwanathan
"""Move engines behind one interface: best_move(fen) -> UCI string.

ModelEngine   the trained White and Black PyTorch networks (with their minimax search)
RandomEngine  a legal random move; used for testing the arm and the server without weights
"""
import os
import random


class NoLegalMoves(Exception):
    """Raised when the position is checkmate or stalemate."""


class ModelEngine:
    def __init__(self, white_path=None, black_path=None, device="cpu"):
        import chess  # noqa: F401
        import torch
        from model_trainBlack import Model as BlackModel
        from model_trainWhite import Model as WhiteModel

        white_path = white_path or os.environ.get("WHITE_MODEL_PATH", "savedModels/whiteModels/model_20240118_100613_66")
        black_path = black_path or os.environ.get("BLACK_MODEL_PATH", "savedModels/blackModels/model_20240117_181529_69")
        self.white, self.black = WhiteModel(), BlackModel()
        for model, path in ((self.white, white_path), (self.black, black_path)):
            if not os.path.exists(path):
                raise FileNotFoundError(f"model weights not found: {path}")
            model.load_state_dict(torch.load(path, map_location=device))
            model.eval()

    def best_move(self, fen):
        import chess

        board = chess.Board(fen)
        if board.is_game_over():
            raise NoLegalMoves(board.result())
        model = self.white if board.turn == chess.WHITE else self.black
        # predict() keeps a found_mates flag between calls; reset it so one
        # game's mating search does not leak into the next request.
        model.found_mates = False
        move = model.predict(board)
        if move is None or move not in board.legal_moves:
            # Fall back to a legal move rather than send an illegal one to the arm.
            move = next(iter(board.legal_moves))
        return move.uci()


class RandomEngine:
    def __init__(self, seed=None):
        self.rng = random.Random(seed)

    def best_move(self, fen):
        import chess

        board = chess.Board(fen)
        moves = list(board.legal_moves)
        if not moves:
            raise NoLegalMoves(board.result())
        return self.rng.choice(moves).uci()


def engine_from_env():
    kind = os.environ.get("CHESS_ENGINE", "model")
    return RandomEngine() if kind == "random" else ModelEngine()
