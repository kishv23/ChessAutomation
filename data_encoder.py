# -*- coding: utf-8 -*-
"""
Created on Fri Nov  3 21:19:28 2023

##Author: Kishorekumar Vishwanathan
"""

import argparse
import os

import chess
import numpy as np
import pandas as pd


def make_env():
    """AlphaZero-style 8x8x73 move encoder from gym-chess. Imported lazily: heavy."""
    import gym
    import gym_chess  # noqa: F401  registers ChessAlphaZero-v0

    env = gym.make('ChessAlphaZero-v0')
    env.reset()
    return env


# Function to decode a chess move
def decode_move(move_int, env):
    return env.decode(move_int)

# Function to encode a chess move
def encode_move(move_str, env):
    move = chess.Move.from_uci(move_str)
    
    # Check for underpromotion
    if move.promotion in [chess.KNIGHT, chess.BISHOP, chess.ROOK]:
        move.promotion = chess.QUEEN  # Change underpromotion to promotion

    encoded_move = env.encode(move)
    return encoded_move

# Function to encode a chess position
def encode_position(board: chess.Board) -> np.array:

 array = np.zeros((8, 8, 14), dtype=float)

 for square, piece in board.piece_map().items():
  rank, file = chess.square_rank(square), chess.square_file(square)
  piece_type, color = piece.piece_type, piece.color
 
  offset = 0 if color == chess.WHITE else 6
  

  idx = piece_type - 1
 
  array[rank, file, idx + offset] = 1

 array[:, :, 12] = board.is_repetition(2)
 array[:, :, 13] = board.is_repetition(3)

 return array


# Function to automate encoding for an entire dataset
def encode_moves_and_positions(dataset, env):
    encoded_data = []
    for fen, move_str in dataset:
        board = chess.Board(fen)
        encoded_position = encode_position(board)
        encoded_move = encode_move(move_str, env)
        encoded_data.append((encoded_position, encoded_move))
    return encoded_data

# Function to encode all moves and positions from CSV files in a directory
def encode_all_moves_and_positions_from_directory(directory, env):
    encoded_positions = []
    encoded_moves = []

    # List all files in the directory
    files = os.listdir(directory)
    
    processed_count = 0
    for file in files:
        if file.endswith('.csv'):
            print("Encoding file: ",file)
            df = pd.read_csv(os.path.join(directory, file))

            for i, row in df.iterrows():
                
                encoded_moves.append(encode_move(row['UCI Move'], env))
                board = chess.Board(row['FEN Position'])
                encoded_positions.append(encode_position(board))
                processed_count += 1
                if processed_count % 100000 == 0:
                    print("Encoded", processed_count/1000, "K moves")

    return encoded_positions, encoded_moves

# Function to save encoded positions and moves to files
def save_encoded_data(encoded_positions, encoded_moves, player, out_dir='data/preparedData'):
    os.makedirs(out_dir, exist_ok=True)
    np.save(os.path.join(out_dir, 'encoded_positions_' + player + '.npy'), np.asarray(encoded_positions, dtype=np.int8))
    np.save(os.path.join(out_dir, 'encoded_moves_' + player + '.npy'), np.asarray(encoded_moves, dtype=np.int64))  # CrossEntropyLoss needs int64 targets


def main():
    parser = argparse.ArgumentParser(description='Encode raw (FEN, move) CSVs into training arrays.')
    parser.add_argument('--raw', default='data/rawData', help='directory with white/ and black/ CSV folders')
    parser.add_argument('--out', default='data/preparedData')
    parser.add_argument('--sides', nargs='+', default=['white', 'black'])
    args = parser.parse_args()

    env = make_env()
    for side in args.sides:
        positions, moves = encode_all_moves_and_positions_from_directory(os.path.join(args.raw, side), env)
        save_encoded_data(positions, moves, side, args.out)
        print('Saved', len(moves), side, 'samples to', args.out)


if __name__ == '__main__':
    main()
