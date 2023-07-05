# Manage on-hands
#
# Commands:
#
#   oh add    - Add a list of on-hands
#   oh rm     - Remove a list of on-hands
#   oh status - Report quantity of on-hands in each game, split by ball
#               (aliased to `oh st`)
#
# Command-line options for `oh add` and `oh rm`:
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


def _status():
    """Prints the status of the on-hand sheet"""
    c = Collection.from_sheet()

    # Print in tabular form
    separator = "+-----------------------------+-----------------------+"
    fstr = (
        "|{:<10s} {:^2s} {:^2s} {:^2s} {:^2s} {:^2s} {:^2s} | {:^2s} {:^2s}"
        " {:^2s} {:^2s} {:^2s} | {:^5s}|"
    )
    print(separator)
    print(fstr.format("Game", *[b.value[:2] for b in Ball], "Total"))
    print(separator)

    for game in Game:
        this_game_entries = {k: v for k, v in c.entries.items() if v[game] > 0}
        ball_entries = {}
        for ball in Ball:
            ball_entries[ball] = sum(
                v[game] for k, v in this_game_entries.items() if k.ball == ball
            )
        print(
            fstr.format(
                game.value,
                *[str(ball_entries[b]) for b in Ball],
                str(sum(ball_entries.values())),
            )
        )
    print(separator)


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
    subparsers.add_parser("st")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.command == "add":
        if args.game is not None:
            game = parse_game(args.game)
            game_str = f" ({game.value})"
        else:
            game = None
            game_str = f" (no game profile specified)"

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
        if args.game is not None:
            game = parse_game(args.game)
            game_str = f" ({game.value})"
        else:
            game = None
            game_str = f" (no game profile specified)"

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

    elif args.command in ["status", "st"]:
        _status()


if __name__ == "__main__":
    main()
