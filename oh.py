import gspread

from enum import Enum
from typing import Optional


# --- Global variables / config ----------------------------------------------
SPREADSHEET_ID = '1IR6rCNQYFccBrc_cxNVv2gEQnVpecEAo58IDRJYWNlo'
TAB_NAME = 'On-hands'

N_HEADER_ROWS = 3

BALL_COL = 0    # 0 = 'A'
SPECIES_COL = 1
SWSH1_COL = 9
SWSH2_COL = 10
SV1_COL = 11
SV2_COL = 12
BDSP_COL = 13

LAST_COL = BDSP_COL  # Last column of interest.


# --- Initialise gspread -----------------------------------------------------
# This assumes that a service account exists with its credentials are stored in
# ~/.config/gspread/service_account.json.
gs = gspread.service_account()
ws = gs.open_by_key(SPREADSHEET_ID).worksheet(TAB_NAME)


# --- String manipulation functions --------------------------------------------
def capitalise_first(s):
    if s == 'o':
        # Don't capitalise 'o' in Jangmo-o.
        return s
    else:
        return s[0].upper() + s[1:]


def canonicalise(species_name):
    """
    Convert a Pokemon name to its canonical capitalisation. e.g.
      'togepi'     -> 'Togepi'
      'indeedee-f' -> 'Indeedee-F'
      'jangmo-o'   -> 'Jangmo-o'
    """
    words = species_name.lower().split('-')
    return '-'.join([capitalise_first(w) for w in words])


# --- Data structures --------------------------------------------------------
class Game(Enum):
    """The games / profiles that I use to store on-hands."""
    SWSH1 = 'SwSh 4+IV'
    SWSH2 = 'SwSh 3IV'
    SV1 = 'SV 4+IV'
    SV2 = 'SV 3IV'
    BDSP = 'BDSP'


def parse_game(s):
    s2 = s.lower()
    if s2 == 'swsh1':
        return Game.SWSH1
    elif s2 == 'swsh2':
        return Game.SWSH2
    elif s2 == 'sv1':
        return Game.SV1
    elif s2 == 'sv2':
        return Game.SV2
    elif s2 == 'bdsp':
        return Game.BDSP
    else:
        raise ValueError(f'Could not parse game: <{s}>')


class Ball(Enum):
    """The special balls that we care about."""
    BEAST = 'Beast'
    DREAM = 'Dream'
    FAST = 'Fast'
    FRIEND = 'Friend'
    HEAVY = 'Heavy'
    LEVEL = 'Level'
    LOVE = 'Love'
    LURE = 'Lure'
    MOON = 'Moon'
    SAFARI = 'Safari'
    SPORT = 'Sport'


def parse_ball(s):
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
        raise ValueError(f'Could not parse ball: <{s}>')
    else:
        return Ball(matching_balls[0])


# --- Interlude: a custom exception ------------------------------------------
class NegativeQuantityError(Exception):
    def __init__(self, game: Game, i: int, j: int):
        self.game = game
        self.i = i
        self.j = j

    def __str__(self):
        return (f'Subtraction would result in negative quantity for game'
                f' <{self.game.value}> (original had {self.i};'
                f' trying to subtract {self.j}).')


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

    def __str__(self):
        return "{:2d}|{:2d}|{:2d}|{:2d}|{:2d}".format(
            self.qty[Game.SWSH1], self.qty[Game.SWSH2],
            self.qty[Game.SV1], self.qty[Game.SV2],
            self.qty[Game.BDSP]
        )

    def __add__(self, other):
        new_qty: dict[Game, int] = {}
        for game in Game:
            new_qty[game] = self.qty[game] + other.qty[game]
        return Quantity(new_qty)

    def __sub__(self, other):
        new_qty: dict[Game, int] = {}
        for game in Game:
            new_qty[game] = self.qty[game] - other.qty[game]
            if new_qty[game] < 0:
                raise NegativeQuantityError(game, self.qty[game], other.qty[game])
        return Quantity(new_qty)


class Aprimon:
    ball: Ball
    species: str

    def __init__(self, ball: str, species: str):
        self.ball = parse_ball(ball)
        self.species = canonicalise(species)

    def __str__(self):
        return f'{self.ball.value} {self.species}'

    def __eq__(self, other):
        return self.ball == other.ball and self.species == other.species

    def __lt__(self, other):
        return (self.ball.value, self.species) < (other.ball.value, other.species)

    def __hash__(self):
        return hash((self.ball, self.species))


def parse_apri_qty_from_line(line, game_name=None):
    """
    Parse a line of the form
        [<game_name>] <ball_name> <species> <quantity>
    into an (Aprimon, Quantity) pair. If `game_name` is specified, then the
    line should not contain game.
    """
    try:
        if game_name is not None:
            ball_name, species, quantity = line.split()
        else:
            game_name, ball_name, species, quantity = line.split()
    except ValueError:
        raise ValueError(f'Could not parse line: <{line}>')

    try:
        quantity = int(quantity)
    except ValueError:
        raise ValueError(f'Could not parse quantity: <{quantity}>')

    game = parse_game(game_name)
    apri = Aprimon(ball_name, species)
    qty = Quantity({game: quantity})
    return (apri, qty)


def parse_apri_qty_from_gsheet_row(row: list[str]):
    # gspread (or perhaps Google's API) doesn't return empty cells at the end
    # of the list. So, we must manually pad the list to the correct length to
    # avoid IndexErrors.
    if len(row) < BDSP_COL + 1:
        row += [''] * (BDSP_COL + 1 - len(row))

    ball = row[BALL_COL]
    species = row[SPECIES_COL]

    qty = {}
    for col, game in zip([SWSH1_COL, SWSH2_COL, SV1_COL, SV2_COL, BDSP_COL],
                         [Game.SWSH1, Game.SWSH2, Game.SV1, Game.SV2, Game.BDSP]):
        if row[col] == '':
            continue
        try:
            qty[game] = int(row[col])
        except ValueError:
            raise ValueError(f'Could not parse quantity: <{row[col]}>')

    return (Aprimon(ball, species), Quantity(qty))


class Spreadsheet:
    entries: dict[Aprimon, Quantity]

    def __init__(self, entries: dict[Aprimon, Quantity]):
        self.entries = entries

    @classmethod
    def empty(cls):
        """Initialise a new empty Spreadsheet."""
        return cls({})

    def add_entry(self, aprimon: Aprimon, quantity: Quantity):
        """Add one entry to an existing spreadsheet."""
        if aprimon in self.entries:
            self.entries[aprimon] += quantity
        else:
            self.entries[aprimon] = quantity

    @classmethod
    def from_list(cls, entry_list: list[tuple[Aprimon, Quantity]]):
        """
        Create a Spreadsheet from a list of (Aprimon, Quantity) pairs. The
        Aprimon need not be unique.
        """
        spreadsheet = cls.empty()
        for (aprimon, quantity) in entry_list:
            spreadsheet.add_entry(aprimon, quantity)
        return spreadsheet

    def pretty_print(self):
        sorted_entries = sorted(self.entries.items(), key=lambda t: t[0])
        longest_aprimon = max(len(str(apri)) for (apri, _) in sorted_entries)

        print('\n'.join(f'{str(apri):{longest_aprimon}s} {str(qty)}'
                        for (apri, qty) in sorted_entries))

    @classmethod
    def from_sheet(cls):
        """Create a Spreadsheet by reading in a Google sheet. This uses the
        global variables defined at the top of the file to find and parse the
        sheet."""
        last_col_letter = chr(ord('A') + LAST_COL)
        cells = f'A{N_HEADER_ROWS + 1}:{last_col_letter}'
        values = ws.get_values(cells)

        sheet = cls.empty()
        for row in values:
            apri, qty = parse_apri_qty_from_gsheet_row(row)
            sheet.add_entry(apri, qty)
        return sheet

    @classmethod
    def from_lines(cls, lines: list[str], game: Game = None):
        """Create a spreadsheet by reading in a list of lines."""
        sheet = cls.empty()
        for line in lines:
            apri, qty = parse_apri_qty_from_line(line, game)
            sheet.add_entry(apri, qty)
        return sheet

    def __add__(self, other):
        all_apris = set(self.entries.keys()) | set(other.entries.keys())
        new_entries = {}
        for apri in all_apris:
            if apri in self.entries and apri in other.entries:
                new_entries[apri] = self.entries[apri] + other.entries[apri]
            elif apri in self.entries:
                new_entries[apri] = self.entries[apri]
            else:
                new_entries[apri] = other.entries[apri]
        return Spreadsheet(new_entries)

    def __sub__(self, other):
        all_apris = set(self.entries.keys()) | set(other.entries.keys())
        new_entries = {}
        for apri in all_apris:
            if apri in self.entries and apri in other.entries:
                try:
                    new_entries[apri] = self.entries[apri] - other.entries[apri]
                except NegativeQuantityError as e:
                    raise ValueError(f'Cannot subtract spreadsheets: entry {apri}'
                                     f' would have negative quantity in game'
                                     f' <{e.game.value}> (original quantity'
                                     f' was {e.i}; trying to subtract'
                                     f' {e.j}).') from None
            elif apri in self.entries:
                new_entries[apri] = self.entries[apri]
            else:
                raise ValueError(f'Cannot subtract spreadsheets: entry {apri}'
                                 f' was not present in first spreadsheet.')
        return Spreadsheet(new_entries)


s = Spreadsheet.from_sheet()
s.pretty_print()

s - Spreadsheet.from_lines(['swsh2 beast charmander 1'])
