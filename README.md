# Chess Automation

A chess-playing robot. Move-prediction networks trained on Lichess Elite games choose the robot's moves, and a 4-DOF robotic arm plays them on a real board against a human.

```
 human moves a piece ─► types the move ─► engine (White / Black networks + minimax)
                                                │ UCI move
                                                ▼
                         planner: which pieces to lift (captures, castling, en passant, promotion)
                                                ▼
                         geometry + inverse kinematics ─► arm driver (USB serial or simulator)
```

## Move prediction

- **Data.** `pgn_data_parser.py` extracts the winning side's (FEN, move) pairs from Lichess Elite PGN dumps. `data_encoder.py` turns them into 8×8×14 board planes and AlphaZero-style move indices (4,672 actions).
- **Models.** `model_trainWhite.py` and `model_trainBlack.py` train a separate PyTorch network per colour. At play time, each network proposes its top 10 moves, which a 4-ply alpha-beta minimax search re-ranks.
- **Serving.** `server.py` exposes `POST /predict_move` with `{"board_state": "<FEN>"}` and returns `{"move": "e2e4"}`.

```bash
python pgn_data_parser.py LichessEliteDatabase/lichess_elite_2017-11.pgn --moves 400000
python data_encoder.py
python model_trainWhite.py && python model_trainBlack.py
WHITE_MODEL_PATH=... BLACK_MODEL_PATH=... python server.py
```

## The arm (`robot/`)

| Module | Does |
| --- | --- |
| `board.py` | Dependency-free FEN parsing, so the controller runs on a Raspberry Pi |
| `planner.py` | Turns one chess move into physical transfers: the captured piece goes to the graveyard first, the en passant pawn is removed from the right square, the rook follows the king when castling, and on promotion the pawn is swapped for a reserve piece |
| `geometry.py` | Square, graveyard and reserve coordinates from a two-point calibration (a1 and h8), so board rotation is handled. Each colour has its own graveyard, with an overflow bin for long games |
| `kinematics.py` | Closed-form IK for base yaw + shoulder + elbow + wrist, with the gripper kept vertical. Forward kinematics for verification. Joint limits are enforced |
| `driver.py` | `SimulatedArm`, and `SerialArm` for Arduino or ESP32 servo firmware (`J`/`G`/`H` line protocol, `ok`/`err` replies) |
| `controller.py` | Safe waypoints: lift to travel height, move, descend, grip, and back. Every point is checked for reach before the arm moves, so a piece is never left mid-air |

### Firmware protocol

```
J <base> <shoulder> <elbow> <wrist>   joint targets in degrees  -> ok | err <reason>
G <0|1>                               open / close gripper      -> ok | err <reason>
H                                     home                      -> ok | err <reason>
```

## Playing

```bash
pip install -r requirements.txt

python calibrate.py --port /dev/ttyUSB0          # jog to a1 and h8, verifies reach, saves calibration.local.json
python play.py --port /dev/ttyUSB0 --cal calibration.local.json

python play.py --sim --engine random             # no hardware or weights needed
```

Type your moves as UCI (`e7e5`) or SAN (`Nf6`). Keep a spare queen, rook, bishop and knight in the reserve tray for promotions.

## Evaluation

```bash
python testing_vs_random.py --games 200
```

This plays the engine against a random mover with alternating colours and reports wins, draws, losses and errors separately.

## Tests

```bash
pip install python-chess numpy pandas flask pytest
pytest -q
```

The tests cover the special-move transfer plans, IK against FK across the whole board, reach for every square and graveyard slot, the controller's waypoints and abort behaviour, the serial protocol, the server's validation, the PGN extraction (including correct mirroring of Black positions), and a complete simulated game. None of them need PyTorch or model weights.
