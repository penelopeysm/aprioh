# Manage on-hands
#
# Commands:
#
#   oh add    - Add a list of on-hands
#   oh rm     - Remove a list of on-hands
#   oh status - Report quantity of on-hands in each game, split by ball
#               (aliased to `oh st`)
#   oh list   - List all Aprimon with a given ball in a given game
#   oh tidy   - Convert common Discord lists of Aprimon to a format understood
#               by the other commands in this
#
# Common command-line options:
#
#  -f [FILE] - File to read from. If not specified, read from stdin.
#  -g [GAME] - Game to add each line to. If not specified, the game must be
#              given on each line.

import sys

import argparse
from onhands import *


def _add(c_add: Collection, quiet: bool = False) -> None:
    """Adds the specified collection to the on-hand sheet"""
    c = Collection.from_sheet(quiet=quiet)
    c_new = c + c_add
    c_new.to_sheet(quiet=quiet)


def _list(game: Game, ball: Ball | None, quiet: bool = False) -> None:
    """Lists all Aprimon with a given ball in a given game"""
    c = Collection.from_sheet(quiet=quiet)
    cumulative = 0
    for apri, qty in c:
        if (ball is None or apri.ball == ball) and qty[game] > 0:
            cumulative += qty[game]
            print(f"{'(' + str(cumulative) + ')':>5s} {qty[game]:2d} {apri}")


def _rm(c_rm: Collection, quiet: bool = False) -> None:
    """Removes the specified collection from the on-hand sheet"""
    c = Collection.from_sheet(quiet=quiet)
    c_new = c - c_rm
    c_new.to_sheet(quiet=quiet)


def _search(apris: list[Aprimon], quiet: bool = False) -> None:
    c = Collection.from_sheet(quiet=quiet)

    search_hits: dict[Game, list[Aprimon]] = {g: [] for g in Game}
    search_misses: list[Aprimon] = []
    for apri in apris:
        try:
            qty = c.get(apri)
            # The ordering of this list block is important, because we want to
            # try to first find the Aprimon in the 4+IV sections. If it's not
            # found there, then we search in the 3IV sections, and then BDSP.
            for game in [Game.SWSH1, Game.SV1, Game.SWSH2, Game.SV2, Game.BDSP]:
                if qty[game] > 0:
                    search_hits[game].append(apri)
                    break
            else:  # all 0; this shouldn't happen
                search_misses.append(apri)
        except KeyError:
            search_misses.append(apri)

    # Print results
    print_heart(f"Found {sum(len(hits) for hits in search_hits.values())}"
                f" of {len(apris)} Aprimon.",
                quiet=quiet)
    for game, text in zip(Game, ["swsh1", "swsh2", "sv1", "sv2", "bdsp"]):
        for apri in sorted(search_hits[game]):
            print(f"{text} {str(apri)}")
    if len(search_misses) > 0:
        print_heart(f"Not found: {', '.join(str(a) for a in search_misses)}",
                    quiet=quiet)


def _status(quiet: bool = False) -> None:
    """Prints the status of the on-hand sheet"""
    c = Collection.from_sheet(quiet=quiet)

    # Print in tabular form
    separator = "+-----------+-------------------+------------------------+"
    fstr = (
        "|{:<10s} | {:>2s} {:>2s} {:>2s} {:>2s} {:>2s} {:>2s} | {:>2s} {:>2s}"
        " {:>2s} {:>2s} {:>2s} | {:>5s} |"
    )
    print(separator)
    print(fstr.format("Game", *[b.value[:2] for b in Ball], "Total"))
    print(separator)

    total = 0
    for game in Game:
        this_game_entries = {k: v for k, v in c.entries.items() if v[game] > 0}
        ball_entries = {}
        for ball in Ball:
            ball_entries[ball] = sum(
                v[game] for k, v in this_game_entries.items() if k.ball == ball
            )
        total_in_this_game = sum(ball_entries.values())
        total += total_in_this_game
        print(
            fstr.format(
                game.value,
                *[str(ball_entries[b]) for b in Ball],
                str(total_in_this_game),
            )
        )
    print(separator)
    print(fstr.format("Total", *["" for _ in Ball], str(total)))
    print(separator)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")

    parser_add = subparsers.add_parser("add")
    parser_add.add_argument("-f", "--file", help="File to read from")
    parser_add.add_argument("-g", "--game", help="Game to add to")
    parser_add.add_argument("-q", "--quiet", action="store_true",
                            help="Do not print progress output")

    parser_list = subparsers.add_parser("list")
    parser_list.add_argument("-g", "--game", help="Game to list from",
                             required=True)
    parser_list.add_argument("-b", "--ball", help="List only a specific ball",)
    parser_list.add_argument("-q", "--quiet", action="store_true",
                               help="Do not print progress output")

    parser_rm = subparsers.add_parser("rm")
    parser_rm.add_argument("-f", "--file", help="File to read from")
    parser_rm.add_argument("-g", "--game", help="Game to remove from")
    parser_rm.add_argument("-q", "--quiet", action="store_true",
                           help="Do not print progress output")

    parser_search = subparsers.add_parser("search")
    parser_search.add_argument("-f", "--file", help="File to read from")
    parser_search.add_argument("-q", "--quiet", action="store_true",
                               help="Do not print progress output")

    parser_status = subparsers.add_parser("status", aliases=["st"])
    parser_status.add_argument("-q", "--quiet", action="store_true",
                               help="Do not print progress output")

    parser_tidy = subparsers.add_parser("tidy", help="convert Discord lists to standard format")

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.command == "add":
        if args.game is not None:
            game = parse_game(args.game)
            game_str = f" ({game.value})"
        else:
            game = None
            game_str = f" (no game profile specified)"

        if args.file is not None:
            print_heart(f"Adding from file {args.file}{game_str}",
                        quiet=args.quiet)
            with open(args.file, "r") as f:
                lines = f.readlines()
            c_add = Collection.from_lines(lines, game=game)
            if len(c_add) > 0:
                _add(c_add, quiet=args.quiet)
        else:
            print_heart(f"Adding from stdin{game_str}",
                        quiet=args.quiet)
            lines = sys.stdin.readlines()
            c_add = Collection.from_lines(lines, game=game)
            if len(c_add) > 0:
                _add(c_add, quiet=args.quiet)

    elif args.command == "list":
        game = parse_game(args.game)
        if args.ball is not None:
            ball = parse_ball(args.ball)
        else:
            ball = None
        _list(game=game, ball=ball, quiet=args.quiet)

    elif args.command == "rm":
        if args.game is not None:
            game = parse_game(args.game)
            game_str = f" ({game.value})"
        else:
            game = None
            game_str = f" (no game profile specified)"

        if args.file is not None:
            print_heart(f"Removing from file {args.file}{game_str}",
                        quiet=args.quiet)
            with open(args.file, "r") as f:
                lines = f.readlines()
            c_rm = Collection.from_lines(lines, game=game)
            if len(c_rm) > 0:
                _rm(c_rm, quiet=args.quiet)
        else:
            print_heart(f"Removing from stdin{game_str}",
                        quiet=args.quiet)
            lines = sys.stdin.readlines()
            c_rm = Collection.from_lines(lines, game=game)
            if len(c_rm) > 0:
                _rm(c_rm, quiet=args.quiet)

    elif args.command == "search":
        apris = []

        if args.file is not None:
            print_heart(f"Searching from file {args.file}",
                        quiet=args.quiet)
            with open(args.file, "r") as f:
                lines = f.readlines()
        else:
            print_heart("Searching from stdin",
                        quiet=args.quiet)
            lines = sys.stdin.readlines()

        for line in lines:
            if line.strip() == "":
                continue
            apris.append(Aprimon.from_line(line))

        if len(apris) > 0:
            _search(apris, quiet=args.quiet)

    elif args.command == "status" or args.command == "st":
        _status(quiet=args.quiet)

    elif args.command == "tidy":
        # Convert lines that look like, e.g., "Togepi :dreamball:" to "dream togepi"
        lines = sys.stdin.readlines()
        for line in lines:
            words = line.split()
            # assume that :xxxball: is a ball
            balls = [w[1:-5] for w in words if w.startswith(":") and w.endswith("ball:")]
            species = " ".join([w for w in words if not (w.startswith(":") and w.endswith("ball:"))])
            for ball in balls:
                print(f"{ball} {species}")

if __name__ == "__main__":
    main()
