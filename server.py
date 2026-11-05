#Author: Kishorekumar Vishwanathan
"""HTTP move server for the robot and any UI.

    POST /predict_move  {"board_state": "<FEN>"}  ->  {"move": "e2e4"}
    GET  /health

    CHESS_ENGINE=random python server.py     # no model weights needed
"""
import os

from flask import Flask, jsonify, request

from robot.board import parse_fen


def create_app(engine=None):
    app = Flask(__name__)
    try:
        from flask_cors import CORS

        CORS(app)
    except ImportError:
        pass

    state = {"engine": engine}

    def get_engine():
        if state["engine"] is None:
            from engine import engine_from_env

            state["engine"] = engine_from_env()  # load weights on first request, not at import
        return state["engine"]

    @app.get("/health")
    def health():
        return jsonify({"ok": True, "engine": type(state["engine"]).__name__ if state["engine"] else "not loaded"})

    @app.post("/predict_move")
    def predict_move():
        from engine import NoLegalMoves

        body = request.get_json(silent=True) or {}
        fen = body.get("board_state")
        if not isinstance(fen, str) or not fen.strip():
            return jsonify({"error": "board_state (a FEN string) is required"}), 400
        try:
            parse_fen(fen)
        except ValueError as exc:
            return jsonify({"error": f"invalid FEN: {exc}"}), 400
        try:
            move = get_engine().best_move(fen)
        except NoLegalMoves as exc:
            return jsonify({"error": "game over", "result": str(exc)}), 409
        app.logger.info("%s -> %s", fen, move)
        return jsonify({"move": move})

    return app


if __name__ == "__main__":
    create_app().run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", 5000)))
