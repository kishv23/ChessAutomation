import pytest

pytest.importorskip("flask")

from engine import NoLegalMoves  # noqa: E402
from server import create_app  # noqa: E402

START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


class FakeEngine:
    def __init__(self, move="e2e4", over=False):
        self.move, self.over, self.seen = move, over, []

    def best_move(self, fen):
        self.seen.append(fen)
        if self.over:
            raise NoLegalMoves("1-0")
        return self.move


def client(engine):
    return create_app(engine).test_client()


def test_returns_engine_move():
    eng = FakeEngine()
    res = client(eng).post("/predict_move", json={"board_state": START})
    assert res.status_code == 200 and res.get_json() == {"move": "e2e4"}
    assert eng.seen == [START]


@pytest.mark.parametrize("body", [{}, {"board_state": ""}, {"board_state": 42}, None])
def test_missing_board_state_is_400(body):
    res = client(FakeEngine()).post("/predict_move", json=body) if body is not None else client(FakeEngine()).post("/predict_move", data="nope")
    assert res.status_code == 400


def test_invalid_fen_never_reaches_the_engine():
    eng = FakeEngine()
    res = client(eng).post("/predict_move", json={"board_state": "not/a/fen w"})
    assert res.status_code == 400 and "invalid FEN" in res.get_json()["error"]
    assert eng.seen == []


def test_game_over_is_409():
    res = client(FakeEngine(over=True)).post("/predict_move", json={"board_state": START})
    assert res.status_code == 409 and res.get_json()["result"] == "1-0"


def test_health_does_not_load_models():
    res = create_app().test_client().get("/health")
    assert res.get_json() == {"ok": True, "engine": "not loaded"}
