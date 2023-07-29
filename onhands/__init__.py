import gspread  # type: ignore
from gspread.utils import ValueInputOption  # type: ignore

import sys
from itertools import cycle
from enum import Enum
from typing import Optional, Iterator


# --- Global variables / config ----------------------------------------------
SPREADSHEET_ID = "1IR6rCNQYFccBrc_cxNVv2gEQnVpecEAo58IDRJYWNlo"
TAB_NAME = "On-hands"
N_HEADER_ROWS = 3
BALL_COL = 0  # 0 = 'A'
SPECIES_COL = 1
SWSH1_COL = 9
SWSH2_COL = 10
SV1_COL = 11
SV2_COL = 12
BDSP_COL = 13
LAST_COL = BDSP_COL  # Last column of interest.


# --- Initialise gspread -----------------------------------------------------
# This assumes that a service account exists with its credentials stored in
# ~/.config/gspread/service_account.json.
gs = gspread.service_account()


# --- String manipulation functions --------------------------------------------
def capitalise_first(s: str) -> str:
    if s == "o":
        # Don't capitalise 'o' in Jangmo-o.
        return s
    else:
        return s[0].upper() + s[1:]


def canonicalise(species_name: str) -> str:
    """
    Convert a Pokemon name to its canonical capitalisation. e.g.
      'togepi'       -> 'Togepi'
      'indeedee-f'   -> 'Indeedee-F'
      'jangmo-o'     -> 'Jangmo-o'

    Also, add accents to Flabebe's name:
      'flabebe-blue' -> 'Flabébé-Blue'
    and convert 'mime' or 'mrmime' to 'Mr. Mime':
      'mime-galar'   -> 'Mr. Mime-Galar'
    """
    species_name = species_name.lower().replace("mr. mime", "mime")
    words = species_name.split("-")
    name = "-".join([capitalise_first(w) for w in words])
    name = name.replace("Flabebe", "Flabébé")
    name = name.replace("Mime", "Mr. Mime")
    return name


def yield_heart() -> Iterator[str]:
    yield from cycle(["❤️ ", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍", "🤎"])


heart_generator = yield_heart()


def print_heart(s: str, quiet: bool = False) -> None:
    """Print a string to stderr, with bold ANSI escape sequences and prefixed
    with a colourful heart emoji (because why not). If quiet is True, doesn't
    do anything."""
    if not quiet:
        heart_emoji = next(heart_generator)
        print(f" {heart_emoji} \033[1m{s}\033[0m", file=sys.stderr)


# --- Data structures --------------------------------------------------------
class Game(Enum):
    """The games / profiles that I use to store on-hands."""

    SWSH1 = "SwSh 4+IV"
    SWSH2 = "SwSh 3IV"
    SV1 = "SV 4+IV"
    SV2 = "SV 3IV"
    BDSP = "BDSP"


def parse_game(s: str) -> Game:
    s2 = s.lower()
    if s2 == "swsh1":
        return Game.SWSH1
    elif s2 == "swsh2":
        return Game.SWSH2
    elif s2 == "sv1":
        return Game.SV1
    elif s2 == "sv2":
        return Game.SV2
    elif s2 == "bdsp":
        return Game.BDSP
    else:
        raise ValueError(f"Could not parse game: <{s}>")


class Ball(Enum):
    """The special balls that we care about."""

    BEAST = "Beast"
    DREAM = "Dream"
    FAST = "Fast"
    FRIEND = "Friend"
    HEAVY = "Heavy"
    LEVEL = "Level"
    LOVE = "Love"
    LURE = "Lure"
    MOON = "Moon"
    SAFARI = "Safari"
    SPORT = "Sport"


def parse_ball(s: str) -> Ball:
    """
    Parse a string into a member of the Ball enum. The string must be a
    (case-insensitive) prefix of exactly one ball name.

    e.g. parse_ball('b')  -> Ball.BEAST
         parse_ball('s')  -> error
         parse_ball('fr') -> Ball.FRIEND
    """
    all_ball_values = [b.value for b in Ball]
    matching_balls = [b for b in all_ball_values if b.lower().startswith(s.lower())]
    if len(matching_balls) != 1:
        raise ValueError(f"Could not parse ball: <{s}>")
    else:
        return Ball(matching_balls[0])


# --- Interlude: a custom exception ------------------------------------------
class NegativeQuantityError(Exception):
    def __init__(self, game: Game, i: int, j: int):
        self.game = game
        self.i = i
        self.j = j

    def __str__(self):
        return (
            f"Subtraction would result in negative quantity for game"
            f" <{self.game.value}> (original had {self.i};"
            f" trying to subtract {self.j})."
        )


# --- Data structures, continued ---------------------------------------------
class Quantity:
    """
    Represents the quantity of a given Aprimon combination, split by game /
    profile.
    """

    qty: dict[Game, int]

    def __init__(self, qty: Optional[dict[Game, int]] = None):
        if qty is None:
            self.qty = {game: 0 for game in Game}
        else:
            self.qty = qty
            # Fill missing values with 0
            for game in Game:
                if game not in qty:
                    self.qty[game] = 0

    def __str__(self) -> str:
        return "{:2d}|{:2d}|{:2d}|{:2d}|{:2d}".format(
            *(self.qty[game] for game in Game)
        )

    def __add__(self, other: "Quantity") -> "Quantity":
        new_qty: dict[Game, int] = {}
        for game in Game:
            new_qty[game] = self.qty[game] + other.qty[game]
        return Quantity(new_qty)

    def __sub__(self, other: "Quantity") -> "Quantity":
        new_qty: dict[Game, int] = {}
        for game in Game:
            new_qty[game] = self.qty[game] - other.qty[game]
            if new_qty[game] < 0:
                raise NegativeQuantityError(game, self.qty[game], other.qty[game])
        return Quantity(new_qty)

    def __getitem__(self, game: Game) -> int:
        return self.qty[game]

    def __setitem__(self, game: Game, value: int) -> None:
        self.qty[game] = value

    def is_empty(self) -> bool:
        return all(q == 0 for q in self.qty.values())

    @property
    def swsh1(self) -> int:
        return self.qty[Game.SWSH1]

    @property
    def swsh2(self) -> int:
        return self.qty[Game.SWSH2]

    @property
    def sv1(self) -> int:
        return self.qty[Game.SV1]

    @property
    def sv2(self) -> int:
        return self.qty[Game.SV2]

    @property
    def bdsp(self) -> int:
        return self.qty[Game.BDSP]


class Aprimon:
    ball: Ball
    species: str

    def __init__(self, ball: str, species: str):
        self.ball = parse_ball(ball)
        self.species = canonicalise(species)

    def __str__(self) -> str:
        return f"{self.ball.value} {self.species}"

    def pretty_print(self) -> None:
        print(str(self))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Aprimon):
            return NotImplemented
        return self.ball == other.ball and self.species == other.species

    def __lt__(self, other: "Aprimon") -> bool:
        # Lexicographic ordering
        return (self.ball.value, self.species) < (other.ball.value, other.species)

    def __hash__(self) -> int:
        return hash((self.ball, self.species))

    @classmethod
    def from_line(cls, line: str) -> "Aprimon":
        try:
            (ball_name, species) = line.split()
        except ValueError:
            raise ValueError(f"Could not parse line: <{line}> into Aprimon")
        return cls(ball_name, species)


def parse_apri_qty_from_line(
    line: str, game: Optional[Game] = None
) -> tuple[Aprimon, Quantity]:
    """
    Parse a line of the form
        [<game_name>] <ball_name> <species> <quantity>
    into an (Aprimon, Quantity) pair. If `game_name` is specified, then the
    line should not contain game.
    """
    if game is None:
        game_name, line = line.split(maxsplit=1)
        try:
            game = parse_game(game_name)
        except ValueError:
            raise ValueError(f"Could not parse game: <{game_name}>")

    words = line.split()
    if len(words) == 2:
        ball_name, species = words
        quantity = 1
    elif len(words) == 3:
        ball_name, species, quantity_str = words
        try:
            quantity = int(quantity_str)
        except ValueError:
            raise ValueError(f"Could not parse quantity: <{quantity_str}>")
    else:
        raise ValueError(f"Could not parse line: <{line}> into Aprimon and quantity")

    apri = Aprimon(ball_name, species)
    qty = Quantity({game: quantity})
    return (apri, qty)


def parse_apri_qty_from_gsheet_row(row: list[str]) -> tuple[Aprimon, Quantity]:
    # gspread (or perhaps Google's API) doesn't return empty cells at the end
    # of the list. So, we must manually pad the list to the correct length to
    # avoid IndexErrors.
    if len(row) < BDSP_COL + 1:
        row += [""] * (BDSP_COL + 1 - len(row))

    ball = row[BALL_COL]
    species = row[SPECIES_COL]

    qty = {}
    for col, game in zip([SWSH1_COL, SWSH2_COL, SV1_COL, SV2_COL, BDSP_COL], Game):
        if row[col] == "":
            continue
        try:
            qty[game] = int(row[col])
        except ValueError:
            raise ValueError(f"Could not parse quantity: <{row[col]}>")

    return (Aprimon(ball, species), Quantity(qty))


def make_gsheet_row_from_apri_qty(
    apri: Aprimon, qty: Quantity, row_number: int
) -> list[str]:
    row = [""] * (LAST_COL + 1)
    # Ball and name
    row[BALL_COL] = apri.ball.value
    row[SPECIES_COL] = canonicalise(apri.species)
    # Custom formulas for the stuff in the middle
    row[2] = rf"=VLOOKUP(A{row_number}, Backend!$AD$4:$AE$20, 2)"
    row[3] = rf"=VLOOKUP(B{row_number}, Backend!$A$4:$V, Backend!$C$2)"
    row[4] = rf"=SUM($J{row_number}:$N{row_number})"
    row[5] = rf"=VLOOKUP($B{row_number}, Backend!$A$4:$V, Backend!S$2)"
    row[6] = rf"=VLOOKUP($B{row_number}, Backend!$A$4:$V, Backend!U$2)"
    row[7] = rf"=VLOOKUP($B{row_number}, Backend!$A$4:$V, Backend!V$2)"
    # Quantities
    for col, game in zip([SWSH1_COL, SWSH2_COL, SV1_COL, SV2_COL, BDSP_COL], Game):
        row[col] = "" if qty[game] == 0 else str(qty[game])
    return row


class Collection:
    entries: dict[Aprimon, Quantity]

    def __init__(self, entries: dict[Aprimon, Quantity]):
        self.entries = entries

    @classmethod
    def empty(cls) -> "Collection":
        """Initialise a new empty Collection."""
        return cls({})

    def add_entry(self, aprimon: Aprimon, quantity: Quantity) -> None:
        """Add one entry to an existing spreadsheet."""
        if aprimon in self.entries:
            self.entries[aprimon] += quantity
        else:
            self.entries[aprimon] = quantity

    def __len__(self) -> int:
        return len(self.entries)

    @classmethod
    def from_list(cls, entry_list: list[tuple[Aprimon, Quantity]]) -> "Collection":
        """
        Create a Collection from a list of (Aprimon, Quantity) pairs. The
        Aprimon need not be unique.
        """
        spreadsheet = cls.empty()
        for aprimon, quantity in entry_list:
            spreadsheet.add_entry(aprimon, quantity)
        return spreadsheet

    def pretty_print(self) -> None:
        sorted_entries = sorted(self.entries.items(), key=lambda t: t[0])
        longest_aprimon = max(len(str(apri)) for (apri, _) in sorted_entries)

        print(
            "\n".join(
                f"{str(apri):{longest_aprimon}s} {str(qty)}"
                for (apri, qty) in sorted_entries
            )
        )

    @classmethod
    def from_sheet(cls, quiet=False) -> "Collection":
        """Create a Collection by reading in a (preset) Google sheet. This uses
        the global variables defined at the top of the file to find and parse
        the sheet."""
        print_heart("Reading in spreadsheet...", quiet=quiet)
        ws = gs.open_by_key(SPREADSHEET_ID).worksheet(TAB_NAME)

        last_col_letter = chr(ord("A") + LAST_COL)
        cells = f"A{N_HEADER_ROWS + 1}:{last_col_letter}"
        values = ws.get_values(cells)

        sheet = cls.empty()
        for row in values:
            apri, qty = parse_apri_qty_from_gsheet_row(row)
            sheet.add_entry(apri, qty)
        return sheet

    @classmethod
    def from_lines(cls, lines: list[str], game: Optional[Game] = None) -> "Collection":
        """Create a spreadsheet by reading in a list of lines."""
        sheet = cls.empty()
        for line in lines:
            line = line.strip()
            if line == "":
                continue
            apri, qty = parse_apri_qty_from_line(line, game)
            sheet.add_entry(apri, qty)
        return sheet

    def __add__(self, other: "Collection") -> "Collection":
        all_apris = set(self.entries.keys()) | set(other.entries.keys())
        new_entries = {}
        for apri in all_apris:
            if apri in self.entries and apri in other.entries:
                new_entries[apri] = self.entries[apri] + other.entries[apri]
            elif apri in self.entries:
                new_entries[apri] = self.entries[apri]
            else:
                new_entries[apri] = other.entries[apri]
        return Collection(new_entries)

    def __sub__(self, other: "Collection") -> "Collection":
        all_apris = set(self.entries.keys()) | set(other.entries.keys())
        new_entries = {}
        for apri in all_apris:
            if apri in self.entries and apri in other.entries:
                try:
                    new_entries[apri] = self.entries[apri] - other.entries[apri]
                except NegativeQuantityError as e:
                    raise ValueError(
                        f"Cannot subtract spreadsheets: entry {apri}"
                        f" would have negative quantity in game"
                        f" <{e.game.value}> (original quantity"
                        f" was {e.i}; trying to subtract"
                        f" {e.j})."
                    ) from None
            elif apri in self.entries:
                new_entries[apri] = self.entries[apri]
            else:
                raise ValueError(
                    f"Cannot subtract spreadsheets: entry {apri}"
                    f" was not present in first spreadsheet."
                )
        return Collection(new_entries).prune()

    def prune(self) -> "Collection":
        """Remove all empty entries."""
        return Collection({apri: qty
                           for apri, qty in self.entries.items()
                           if not qty.is_empty()})

    def get(self, apri: Aprimon) -> Quantity:
        """Get an entry in the spreadsheet."""
        if apri in self.entries:
            return self.entries[apri]
        else:
            raise KeyError(f"Could not find entry for {apri}.")

    def _to_sheet_values(self) -> list[list[str]]:
        nonempty_entries = [
            (apri, qty) for apri, qty in self.entries.items() if not qty.is_empty()
        ]
        sorted_entries = sorted(nonempty_entries, key=lambda t: t[0])
        return [
            make_gsheet_row_from_apri_qty(apri, qty, N_HEADER_ROWS + i)
            for i, (apri, qty) in enumerate(sorted_entries, start=1)
        ]

    def to_sheet(self, quiet=False) -> None:
        gs = gspread.service_account()
        ws = gs.open_by_key(SPREADSHEET_ID).worksheet(TAB_NAME)
        values = ws.get_values()

        nrows = len(values)
        nrows_new = len(self.entries) + N_HEADER_ROWS

        print_heart("Updating number of rows in spreadsheet...", quiet=quiet)
        if nrows_new > nrows:
            # Insert phantom rows at the bottom of the spreadsheet
            phantom_values = [[""] * LAST_COL] * (nrows_new - nrows)
            ws.insert_rows(
                values=phantom_values, row=nrows + 1, inherit_from_before=True
            )
        elif nrows_new < nrows:
            # Delete rows at the bottom
            ws.delete_rows(start_index=nrows_new + 1, end_index=nrows)

        # Update the spreadsheet values
        print_heart("Updating spreadsheet values...", quiet=quiet)
        values = self._to_sheet_values()
        ws.batch_update(
            [
                {
                    "range": f'A{N_HEADER_ROWS + 1}:{chr(ord("A") + LAST_COL)}',
                    "values": self._to_sheet_values(),
                }
            ],
            value_input_option=ValueInputOption.user_entered,
        )

        # Update spreadsheet borders
        print_heart("Updating spreadsheet borders...", quiet=quiet)
        border_style = {
            "style": "SOLID",
            "colorStyle": {
                "rgbColor": {
                    "red": 0.95294,
                    "green": 0.95294,
                    "blue": 0.95294,
                    "alpha": 1,
                }
            },
        }
        ws.format(
            f"{chr(ord('A') + SWSH1_COL)}{N_HEADER_ROWS + 1}:{chr(ord('A') + LAST_COL)}",
            {
                "borders": {
                    "bottom": border_style,
                    "right": border_style,
                }
            },
        )

        print_heart("Done.", quiet=quiet)
