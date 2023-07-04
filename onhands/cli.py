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
from onhands import Collection, Game


def _add(c_add: Collection):
    """Adds the specified collection to the on-hand sheet"""
    c = Collection.from_sheet()
    c_new = c + c_add
    c_new.to_sheet()


def add_from_file(fname:str, game: Game=None):
    with open(fname, 'r') as f:
        lines = f.readlines()
    c_add = Collection.from_lines(lines, game=game)
    _add(c_add)


def add_from_stdin(game: Game=None):
    lines = sys.stdin.readlines()
    c_add = Collection.from_lines(lines, game=game)
    _add(c_add)


def parse_args():
    # parse command-line arguments
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')

    parser_add = subparsers.add_parser('add')
    parser_add.add_argument('-f', '--file', help='File to read from')
    parser_add.add_argument('-g', '--game', help='Game to add to')

    parser_rm = subparsers.add_parser('rm')
    parser_rm.add_argument('-f', '--file', help='File to read from')
    parser_rm.add_argument('-g', '--game', help='Game to remove from')

    subparsers.add_parser('status')
    return parser.parse_args()


def main():
    args = parse_args()
    print(args)


if __name__ == '__main__':
    main()
