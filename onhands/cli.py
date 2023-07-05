# Manage on-hands
#
# Commands:
#
#   oh add    - Add a list of on-hands
#   oh rm     - Remove a list of on-hands
#   oh status - Report quantity of on-hands in each game, split by ball
#
# Command-line options for 'oh add' and 'oh rm':
#
#  -f [FILE] - File to read from. If not specified, read from stdin.
#  -g [GAME] - Game to add each line to. If not specified, the game must be
#              given on each line.

import sys

import argparse
from onhands import *


def _add(c_add: Collection):
    """Adds the specified collection to the on-hand sheet"""
    c = Collection.from_sheet()
    c_new = c + c_add
    c_new.to_sheet()


def _rm(c_rm: Collection):
    """Removes the specified collection from the on-hand sheet"""
    c = Collection.from_sheet()
    c_new = c - c_rm
    c_new.to_sheet()


def parse_args():
    # parse command-line arguments
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")

    parser_add = subparsers.add_parser("add")
    parser_add.add_argument("-f", "--file", help="File to read from")
    parser_add.add_argument("-g", "--game", help="Game to add to")

    parser_rm = subparsers.add_parser("rm")
    parser_rm.add_argument("-f", "--file", help="File to read from")
    parser_rm.add_argument("-g", "--game", help="Game to remove from")

    subparsers.add_parser("status")
    return parser.parse_args()


def main():
    args = parse_args()

    # Parse game argument (for oh add and oh rm)
    if args.game is not None:
        game = parse_game(args.game)
        game_str = f" ({game.value})"
    else:
        game = None
        game_str = f" (no game profile specified)"

    if args.command == "add":
        if args.file is not None:
            print_heart(f"Adding from file {args.file}{game_str}")
            with open(args.file, "r") as f:
                lines = f.readlines()
            c_add = Collection.from_lines(lines, game=game)
            if len(c_add) > 0:
                _add(c_add)
        else:
            print_heart(f"Adding from stdin{game_str}")
            lines = sys.stdin.readlines()
            c_add = Collection.from_lines(lines, game=game)
            if len(c_add) > 0:
                _add(c_add)

    elif args.command == "rm":
        if args.file is not None:
            print_heart(f"Removing from file {args.file}{game_str}")
            with open(args.file, "r") as f:
                lines = f.readlines()
            c_rm = Collection.from_lines(lines, game=game)
            if len(c_rm) > 0:
                _rm(c_rm)
        else:
            print_heart(f"Removing from stdin{game_str}")
            lines = sys.stdin.readlines()
            c_rm = Collection.from_lines(lines, game=game)
            if len(c_rm) > 0:
                _rm(c_rm)

    elif args.command == "status":
        raise NotImplementedError("status not implemented")


if __name__ == "__main__":
    main()
