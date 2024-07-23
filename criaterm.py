from __future__ import annotations
from dataclasses import dataclass, replace
from enum import Enum, auto
from functools import lru_cache
from typing import Final, TypeVar, Callable, Never
import os
import sys

__all__ = [
    # input
    'input_int',
    'input_float',
    'input_bool',

    # iterative apps
    'run_app',

    # types
    'SpecialKey',
    'CharGrid',
    'AnsiStr',
    'Color',
    'Style',

    # colors
    'rgb',
    'fixed',
    'black',
    'red',
    'green',
    'yellow',
    'blue',
    'magenta',
    'cyan',
    'white',

    # background
    'on',

    # style
    'default',
    'bold',
    'italic',
    'blink',
    'underline',
    'reverse',
    'strikethrough',
]


##################
# Input
##################

# TODO: write docs for input functions

def input_int(prompt: str = '',
              err: str = '',
              min: int | None = None,
              max: int | None = None,
              default: int | None = None) -> int:
    '''
    >>> with fake_input('32.0', '12', '32') as _:
    ...     n = input_int('Number: ', min=15, err='no for you')
    Number: 32.0
    no for you
    Number: 12
    no for you
    Number: 32
    >>> n
    32
    >>> with fake_input('') as _:
    ...     n = input_int('?', default=-12)
    ?
    >>> n
    -12
    '''
    while True:
        try:
            if (s := _input(prompt)) == '' and default is not None:
                return default
            val = int(s)
            if min and val < min or max and max < val:
                raise ValueError()
            return val
        except ValueError as _:
            if err:
                print(err)


def input_float(prompt: str = '',
                err: str = '',
                min: float | None = None,
                max: float | None = None,
                default: float | None = None) -> float:
    '''
    >>> with fake_input('num', '102.32', '50.65') as _:
    ...     n = input_float('Number: ', max=100.0)
    Number: num
    Number: 102.32
    Number: 50.65
    >>> n
    50.65
    >>> with fake_input('') as _:
    ...     n = input_int('?', default=123.456)
    ?
    >>> n
    123.456
    '''
    while True:
        try:
            if (s := _input(prompt)) == '' and default is not None:
                return default
            val = float(s)
            if min and val < min or max and max < val:
                raise ValueError()
            return val
        except ValueError as _:
            if err:
                print(err)


def input_bool(prompt: str = '',
               err: str = '',
               yes: list[str] = ['y', 'yes'],
               no: list[str] = ['n', 'no'],
               default: bool | None = None) -> bool:
    '''
    >>> with fake_input('wrong', 'y') as _:
    ...     s = input_bool('Continue? ', err='Again...')
    Continue? wrong
    Again...
    Continue? y
    >>> s
    True
    >>> with fake_input('no') as _:
    ...     s = input_bool('Continue? ')
    Continue? no
    >>> s
    False
    >>> with fake_input('') as _:
    ...     s = input_bool('Continue?', default=True)
    Continue?
    >>> s
    True
    '''
    while True:
        val = _input(prompt)
        if val == '' and default is not None:
            return default
        if val.lower() in map(str.lower, yes):
            return True
        if val.lower() in map(str.lower, no):
            return False
        if err:
            print(err)


_mocked_input: list[str] | None = None


def _input(prompt: str = '') -> str:
    '''
    >>> with fake_input() as _:
    ...     try:
    ...         _input()
    ...         assert False
    ...     except EOFError:
    ...         pass
    '''
    global _mocked_input
    if _mocked_input is not None:
        print(prompt, end='')
        if len(_mocked_input) == 0:
            raise EOFError()
        s = _mocked_input[0]
        _mocked_input = _mocked_input[1:]
        print(s)
        return s
    else:
        return input(prompt)


class fake_input:
    input: list[str] | None

    def __init__(self, *strs: str) -> None:
        self.input = list(strs)

    def __enter__(self) -> fake_input:
        global _mocked_input
        # save _mocked_input in input
        self.input, _mocked_input = _mocked_input, self.input
        return self

    def __exit__(self, _exception_type, _exception_value, _exception_traceback) -> None:
        global _mocked_input
        # restore _mocked_input
        _mocked_input = self.input


##################
# Interactive apps
##################


S = TypeVar("S")

def run_app(state: S,
            to_grid: Callable[[S], CharGrid],
            on_tick: Callable[[S], S] | None = None,
            on_key: Callable[[S, str | SpecialKey], S] | None = None,
            rate: float = 0.1) -> None:
    import time
    # TODO: improve rate handling
    last = time.time()
    with Terminal() as _, AlternateMode() as _:
        while True:
            print(CLEAR_SCREEN + MOVE_CURSOR_HOME + str(to_grid(state)))
            while (key := read()) == '' and time.time() - last < rate:
                time.sleep(0.001)
            if key == '':
                last = time.time()
                if on_tick is not None:
                    state = on_tick(state)
            elif key == SpecialKey.CRTL_C:
                break
            elif on_key is not None:
                state = on_key(state, key)


##################
# Grid and string
##################

@dataclass
class CharGrid:
    '''
    A grid of chars with fomatting.

    The grid do not have a predefined size and can grow on demand, however,
    using indices too large for line or column can result in high use of
    memory.

    Care are taken when wide characters, that is, characters that takes 2
    cells, are put on the grid. Control and zero-width joiner characters are
    not handled properly and should not be used.

    The basic usage is to create the grid and put the strings (normal or
    formatted) using indexing assigment. The chars of the string are put
    starting with the index lin, col and follow to the right. The index
    cannot be negative.

    >>> w = CharGrid()
    >>> w[1, 3] = 'abc' / bold
    >>> w[3, 2] = 'cde' / red
    >>> w[4, 3] = ' '
    >>> w[9, 3] = '' # Does not have any effect
    >>> w.print_content()
    '      '
    '   abc'
    '      '
    '  cde '
    '      '

    Note that in order to make testing easy, the print_content display a
    regular grid, with the number of columns being the max of all lines.

    The next examples show how the grid works with wide chars.

    >>> w = CharGrid()
    >>> w[0, 0] = 'abcd'
    >>> w[1, 0] = 'efgh'
    >>> w[2, 0] = 'ijkl'
    >>> w.print_content()
    'abcd'
    'efgh'
    'ijkl'
    >>> w[0, 0] = '🟥'
    >>> w[1, 1] = '🟩'
    >>> w[2, 2] = '🟨'
    >>> w.print_content()
    '🟥cd'
    'e🟩h'
    'ij🟨'

    Replacing "half" of a wide character leaves a space in the adjacent cell.

    >>> w[0, 1] = '⬜' # ' ' is put in 0, 0
    >>> w[1, 1] = '🟨' #
    >>> w[2, 1] = '🟩' # ' ' is put in 2, 2
    >>> w.print_content()
    ' ⬜d'
    'e🟨h'
    'i🟩 '
    >>> w[0, 1] = 'x' # ' ' is put in 0, 2
    >>> w[1, 2] = 'y' # ' ' is put in 1, 1
    >>> w.print_content()
    ' x d'
    'e yh'
    'i🟩 '

    Some other examples showing that the Grid works as "expected" (well, if
    you find any examples that produces unexpected results, please, open an
    issue).

    >>> w = CharGrid()
    >>> w[0, 0] = 'long string'
    >>> w[0, 2] = '😊 a 🍰'
    >>> w.print_content()
    'lo😊 a 🍰ng'
    >>> w[0, 3] = '😊 a 🍰'
    >>> w.print_content()
    'lo 😊 a 🍰g'
    >>> w[0, 8] = '日本'
    >>> w.print_content()
    'lo 😊 a 日本'
    >>> w[0, 4] = 'c🟩es'
    >>> w.print_content()
    'lo  c🟩es 本'
    '''

    lines: list[list[cstr | None]]
    # For each line in lines, the following invariants are True:
    #  - len(line) == sum((s is None or wcwidth(s)) for s in line)
    #  - For 0 <= i < len(line) - 1 and wcwidth(line[i]) == 2,
    #    line[i + 1] == AnsiStr()

    def __init__(self) -> None:
        '''
        Creates a new empty grid.
        '''
        self.lines = []

    def __setitem__(self, index: tuple[int, int], s: str | AnsiStr):
        '''
        Put the string *s* in the cell at *index*. See the class description
        for usage.
        '''
        if len(s) == 0:
            return

        lin, col = index

        assert 0 <= lin
        assert 0 <= col

        # Add missing lines
        while len(self.lines) <= lin:
            self.lines.append([])

        # Add missing columns (we are over estimating here)
        line = self.lines[lin]
        while len(line) <= col + len(s):
            line.append(None)

        # Fix wide char in col - 1 position
        if line[col] == cstr():
            line[col - 1] = cstr(' ')

        # Do the work
        dest = col
        for i in range(len(s)):
            if isinstance(s, str):
                ch = cstr(s[i])
            else:
                ch = s[i].data[0]
            line[dest] = ch
            if wcwidth(ch.value) == 2:
                dest += 1
                line[dest] = cstr()
            dest += 1

        # Fix empty left after copying s
        if dest < len(line) and line[dest] == cstr():
            line[dest] = cstr(' ')

    def print_content(self) -> None:
        '''
        Prints the content of this grid. All lines are printed with the same
        width (*self.width()*).

        Examples
        >>> g = CharGrid()
        >>> g[2, 3] = 'Emoji 😊!'
        >>> g.print_content()
        '            '
        '            '
        '   Emoji 😊!'
        '''
        width = self.width()
        for line in self.lines:
            s = ''
            for i in range(width):
                if i >= len(line) or (ch := line[i]) is None:
                    s += ' '
                else:
                    s += ch.value
            print(repr(s))

    def width(self) -> int:
        '''
        Returns the width necessary to show all the content of the grid.

        Examples
        >>> g = CharGrid()
        >>> g[0, 0] = 'home'
        >>> g[1, 0] = 'ab'
        >>> g[2, 0] = ' cd'
        >>> g.width()
        4
        '''
        width = 0
        for line in self.lines:
            last = len(line) - 1
            while last >= 0 and line[last] is None:
                last -= 1
            width = max(width, last + 1)
        return width

    def __str__(self) -> str:
        width = self.width()
        space = cstr(' ')
        s: list[cstr] = [cstr('')]
        for line in self.lines:
            for i in range(width):
                if i >= len(line) or (ch := line[i]) is None:
                    ss = space
                else:
                    ss = ch
                if s[-1].style == ss.style:
                    s[-1] = cstr(s[-1].value + ss.value, ss.style)
                else:
                    s.append(ss)
            s.append(cstr('\n\r'))
        return ''.join(map(str, s))


@dataclass(frozen=True)
class AnsiStr:
    '''
    A string with formatting info.

    A formatted string can be created from a str or a formatted string using
    the operator / with a color or a style. A formatted string supports the
    same operations as a str, including concatenation, repetition and slicing.

    >>> # The real output is formatted!
    >>> print('Hello ' / green / bold + 'world!' / red) # doctest: +SKIP
    Hello world!

    The color indicates the color of the string and can be one of the constants
    black, red, green, yellow, blue, magenta, cyan or white. Colors can also be
    created with the function *fixed*, that accepts an int (0 to 255), which is
    a pre-defined color in the terminal, and the function *rgb*, that accepts
    three ints (0 to 255), the red, green and blue values of the color. Use the
    command "python criaterm.py show-fixed" to see the fixed colors.

    To change the background color, use *on(color)*. To reverse the text color
    and the background color, use *reverse*.

    >>> # black text on yellow background (because of the reverse)
    >>> print('Warning!' / rgb(255, 255, 0) / on(black) / reverse) # doctest: +SKIP
    Warning.

    A style is one of the constants bold, italic, blink, underline or
    strikethrough.

    >>> print('Corrected.' / red / strikethrough) # doctest: +SKIP
    Corrected.

    Note that not all terminal supports all colors and styles.

    The repr of a formatted string was conceived to allow easy testing with
    doctest, it's returns a string with a call to AnsiStr contructor and the
    strings and formating. The formating is presented in the order color,
    styles (in the order showed before), background and reverse.

    >>> 'one ' + 'word' / on(green) / blink / black / bold
    AnsiStr('one ', 'word' / black / bold / blink / on(green))

    '''
    data: list[cstr]
    length: int
    # TODO: can lazy merge improves performance?
    # TODO: criar benchmark
    # TODO: cache width?

    def __init__(self, *strs: str | cstr | AnsiStr) -> None:
        '''
        Create a new AnsiString by appending all *strs* values.

        >>> AnsiStr('A ', 't' / red + 'est' / red, ' with' + ' some ', 'colors' / green)
        AnsiStr('A ', 'test' / red, ' with some ', 'colors' / green)
        '''
        data: list[cstr] = []
        length = 0
        for s in strs:
            if not s:
                continue

            if isinstance(s, AnsiStr):
                length += s.length
                if not data:
                    data.extend(s.data)
                    continue
                if data[-1].style == s.data[0].style:
                    # merge
                    data[-1] = cstr(data[-1].value + s.data[0].value,
                                    data[-1].style)
                    data.extend(s.data[1:])
                else:
                    data.extend(s.data)
                continue

            length += len(s)
            if isinstance(s, cstr):
                data.append(s)
            else:
                data.append(cstr(s))

            if len(data) == 1:
                continue

            # Check if the last two itens can be merged
            if data[-1].style == data[-2].style:
                data[-2] = cstr(data[-2].value + data[-1].value,
                                data[-2].style)
                data.pop()

        object.__setattr__(self, 'data', data)
        object.__setattr__(self, 'length', length)

    def content(self) -> str:
        '''
        Returns the content of the string, that is, the string without any formatting.

        Examples
        >>> AnsiStr('No ', 'formatting' / red, '!' / bold).content()
        'No formatting!'
        '''
        r = ''
        for s in self.data:
            if isinstance(s, str):
                r += s
            else:
                r += s.value
        return r

    def width(self) -> int:
        '''
        Return the number of cells that the string takes on the screen.

        This function is expected to work with 1 and 2 wide characters. Control
        and zero-width joiner characters are not handle properly.

        Examples
        >>> AnsiStr('Nomal "0"').width()
        9
        >>> AnsiStr('Wide "０"! 😅').width()
        13
        >>> face = AnsiStr('😅')
        >>> print(f"{face} has {len(face)} codepoint but is {face.width()} cell wide.")
        😅 has 1 codepoint but is 2 cell wide.
        '''
        return sum(wcswidth(s) for s in self.data)

    def __getitem__(self, index: int | slice) -> AnsiStr:
        '''
        Returns a substring of this string. The *index* works the same as for
        slicing normal strings, except that the stride must be 1.

        Examples
        >>> s = AnsiStr('This' / bold, ' is ', 'wrong' / red)
        >>> s[8]
        AnsiStr('w' / red)
        >>> s[-2]
        AnsiStr('n' / red)
        >>> s[2:]
        AnsiStr('is' / bold, ' is ', 'wrong' / red)
        >>> s[:3]
        AnsiStr('Thi' / bold)
        >>> s[3:10]
        AnsiStr('s' / bold, ' is ', 'wr' / red)
        >>> s[3:-3]
        AnsiStr('s' / bold, ' is ', 'wr' / red)
        '''
        alen = len(self)
        if isinstance(index, int):
            if index == -1:
                start, stop, stride = slice(-1, None).indices(alen)
            else:
                start, stop, stride = slice(index, index + 1).indices(alen)
        else:
            start, stop, stride = index.indices(alen)

        assert stride == 1

        if start >= stop:
            return AnsiStr()

        # Discover where to start
        i = 0
        while i < len(self.data) and start - len(self.data[i]) > 0:
            start -= len(self.data[i])
            stop -= len(self.data[i])
            i += 1

        # Construct the substring
        data = []
        while i < len(self.data) and stop > 0:
            data.append(self.data[i][max(0, start):stop])
            start -= len(self.data[i])
            stop -= len(self.data[i])
            i += 1

        return AnsiStr(*data)

    def __add__(self, s: str | cstr | AnsiStr) -> AnsiStr:
        '''
        Returns a new string by concataning this string with *s*.

        Examples
        >>> ab = AnsiStr('ab' / black)
        >>> cd = AnsiStr('cd' / red)
        >>> cd + ab
        AnsiStr('cd' / red, 'ab' / black)
        '''
        return AnsiStr(self, s)

    def __radd__(self, s: str) -> AnsiStr:
        return AnsiStr(s, self)

    def __truediv__(self, color_or_style: Color | Style) -> AnsiStr:
        '''
        Returns a new string updating the style of this string with *style*.

        See *Style.update*.

        Examples
        >>> AnsiStr('Word ' / italic, 'champion' / red) / bold
        AnsiStr('Word ' / bold / italic, 'champion' / red / bold)
        '''
        return AnsiStr(*(s / color_or_style for s in self.data))

    def __mul__(self, n: int) -> AnsiStr:
        '''
        Returns a new string by concatenating *n* copies of this string.
        If *n <= 0*, returns an empty string.

        Examples
        >>> AnsiStr('abc') * 2
        AnsiStr('abcabc')
        >>> AnsiStr('ab', 'cd' / underline) * 3
        AnsiStr('ab', 'cd' / underline, 'ab', 'cd' / underline, 'ab', 'cd' / underline)
        >>> AnsiStr('ab', 'cd' / underline) * 0
        AnsiStr()
        >>> AnsiStr('abc') * -2
        AnsiStr()
        '''
        s = AnsiStr()
        for _ in range(0, n):
            s = AnsiStr(*(s.data + self.data))
        return s

    def __rmul__(self, n: int) -> AnsiStr:
        return self * n

    def __len__(self) -> int:
        '''
        Return the length (the number of codepoints) of the string content.

        >>> face = AnsiStr('😅')
        >>> print(f"{face} has {len(face)} codepoint but is {face.width()} cell wide.")
        😅 has 1 codepoint but is 2 cell wide.
        '''
        return self.length

    def __repr__(self) -> str:
        return f'AnsiStr({repr(self.data)[1:-1]})'

    def __str__(self) -> str:
        # TODO: add smoke test
        return ''.join(str(s) for s in self.data)


##################
# Style and colors
##################

@dataclass(frozen=True)
class Style:
    '''
    Describe a style (format) for a string.

    See the documentation for *AnsiStr* to se how to use formatted strings.
    '''
    fg: Color | None = None
    bg: Color | None = None
    bold: bool = False
    italic: bool = False
    underline: bool = False
    blink: bool = False
    reverse: bool = False
    strikethrough: bool = False

    def update(self, other: Style) -> Style:
        '''
        Creating a new style replacing the itens of this style with the setted
        itens of *other*.

        >>> # Replace fg and add bold
        >>> Style(fg=red, underline=True).update(Style(fg=green, bold=True))
        green / bold / underline
        '''
        style = self
        if other.fg is not None:
            style = replace(style, fg=other.fg)
        if other.bg is not None:
            style = replace(style, bg=other.bg)
        return replace(style,
                       bold=style.bold or other.bold,
                       italic=style.italic or other.italic,
                       blink=style.blink or other.blink,
                       underline=style.underline or other.underline,
                       reverse=style.reverse or other.reverse,
                       strikethrough=style.strikethrough or other.strikethrough)

    def sgr(self) -> str:
        '''
        Returns the sgr ansi escape for this style (without the prefix and suffix).
        '''
        # TODO: add smoke test
        bold = '1' if self.bold else ''
        italic = '3' if self.italic else ''
        underline = '4' if self.underline else ''
        blink = '5' if self.blink else ''
        reverse = '7' if self.reverse else ''
        strikethrough = '9' if self.strikethrough else ''
        fg = self.fg.fg_sgr() if self.fg is not None else ''
        bg = self.bg.bg_sgr() if self.bg is not None else ''
        codes = [bold, italic, underline, blink,
                 reverse, strikethrough, fg, bg]
        return ';'.join(filter(None, codes))

    def __rtruediv__(self, s: str) -> AnsiStr:
        return AnsiStr(cstr(s, self))

    def __repr__(self) -> str:
        fg = repr(self.fg) if self.fg is not None else ''
        bg = f'on({self.bg!r})' if self.bg is not None else ''
        bold = 'bold' if self.bold else ''
        italic = 'italic' if self.italic else ''
        blink = 'blink' if self.blink else ''
        underline = 'underline' if self.underline else ''
        reverse = 'reverse' if self.reverse else ''
        strikethrough = 'strikethrough' if self.strikethrough else ''
        tags = [fg, bold, italic, blink, underline, strikethrough, bg, reverse]
        return ' / '.join(filter(None, tags))


@dataclass(frozen=True)
class cstr:
    value: str = ''
    # TODO: make it Style or None?
    style: Style = Style()

    def __truediv__(self, color_or_style: Color | Style) -> cstr:
        if isinstance(color_or_style, Color):
            return cstr(self.value, replace(self.style, fg=color_or_style))
        else:
            return cstr(self.value, self.style.update(color_or_style))

    def __mul__(self, n: int) -> cstr:
        return cstr(self.value * n, self.style)

    def __rmul__(self, n: int) -> cstr:
        return cstr(self.value * n, self.style)

    def __getitem__(self, index: int | slice) -> cstr:
        return cstr(self.value[index], self.style)

    def __len__(self) -> int:
        return len(self.value)

    def __repr__(self) -> str:
        if self.style == Style():
            return repr(self.value)
        else:
            return ' / '.join([repr(self.value), repr(self.style)])

    def __str__(self) -> str:
        if self.style == Style():
            return f'{self.value}'
        else:
            # TODO: add smoke test
            return f'\x1b[{self.style.sgr()}m{self.value}\x1b[0m'


@dataclass(frozen=True)
class Color:
    # TODO: use a type aliasing instead of creating the Color wrapping type.
    value: NamedColor | FixedColor | RgbColor

    def fg_sgr(self) -> str:
        # TODO: add smoke test
        c = self.value
        if isinstance(c, NamedColor):
            if c != NamedColor.DEFAULT:
                return f'{c.fg}'
            else:
                return ''
        elif isinstance(c, FixedColor):
            return f'38;5;{c.value}'
        else:
            return f'38;2;{c.red};{c.green};{c.blue}'

    def bg_sgr(self) -> str:
        # TODO: add smoke test
        c = self.value
        if isinstance(c, NamedColor):
            if c != NamedColor.DEFAULT:
                return f'{c.bg}'
            else:
                return ''
        elif isinstance(c, FixedColor):
            return f'48;5;{c.value}'
        else:
            return f'48;2;{c.red};{c.green};{c.blue}'

    def __rtruediv__(self, s: str) -> AnsiStr:
        return AnsiStr(cstr(s, Style(fg=self)))

    def __repr__(self) -> str:
        if isinstance(self.value, NamedColor):
            return self.value.name.lower()
        elif isinstance(self.value, FixedColor):
            return f'fixed({self.value.value})'
        else:
            return f'rgb({self.value.red}, {self.value.green}, {self.value.blue})'


@dataclass(frozen=True)
class RgbColor:
    red: int
    green: int
    blue: int

    def __post_init__(self):
        check_invalid_byte('red', self.red)
        check_invalid_byte('green', self.green)
        check_invalid_byte('blue', self.blue)


@dataclass(frozen=True)
class FixedColor:
    value: int

    def __post_init__(self):
        check_invalid_byte('fixed color', self.value)


def check_invalid_byte(tag: str, value: int):
    if not (0 <= value <= 255):
        return ValueError(f'Invalid {tag} value ({value}), must in range from 0 to 255.')


class NamedColor(Enum):
    BLACK = auto(), 30, 40
    RED = auto(), 31, 41
    GREEN = auto(), 32, 42
    YELLOW = auto(), 33, 43
    BLUE = auto(), 34, 44
    MAGENTA = auto(), 35, 45
    CYAN = auto(), 36, 46
    WHITE = auto(), 37, 47
    DEFAULT = auto(), 39, 49
    BRIGHT_BLACK = auto(), 90, 100
    BRIGHT_RED = auto(), 91, 101
    BRIGHT_GREEN = auto(), 92, 102
    BRIGHT_YELLOW = auto(), 93, 43
    BRIGHT_BLUE = auto(), 94, 104
    BRIGHT_MAGENTA = auto(), 95, 105
    BRIGHT_CYAN = auto(), 96, 106
    BRIGHT_WHITE = auto(), 97, 107

    def __new__(cls, *args, **kwds):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        return obj

    # Ignore the first param because it is set by __new__
    def __init__(self, _value: str, fg: int, bg: int):
        self.fg = fg
        self.bg = bg


def rgb(r: int, g: int, b: int) -> Color:
    '''
    Returns a new Color with (r, g, b) componentes.

    Requires that 0 <= r, g, b <= 255.

    >>> rgb(70, 90, 120)
    rgb(70, 90, 120)
    '''
    return Color(RgbColor(r, g, b))


def fixed(color: int) -> Color:
    '''
    Returns a new Color with the fixed color with index *color*.

    Requires that 0 <= color <= 255.

    >>> fixed(20)
    fixed(20)
    '''
    return Color(FixedColor(color))


def on(color: Color) -> Style:
    '''
    Returns a new style with the background color setted to *color*.

    >>> on(green).bg
    green
    >>> Style(bg=blue)
    on(blue)
    '''
    return Style(bg=color)


black: Final = Color(NamedColor.BLACK)
red: Final = Color(NamedColor.RED)
green: Final = Color(NamedColor.GREEN)
yellow: Final = Color(NamedColor.YELLOW)
blue: Final = Color(NamedColor.BLUE)
magenta: Final = Color(NamedColor.MAGENTA)
cyan: Final = Color(NamedColor.CYAN)
white: Final = Color(NamedColor.WHITE)

default: Final = Style()
bold: Final = Style(bold=True)
italic: Final = Style(italic=True)
underline: Final = Style(underline=True)
blink: Final = Style(blink=True)
reverse: Final = Style(reverse=True)
strikethrough: Final = Style(strikethrough=True)


def wcwidth(s: str | cstr) -> int:
    if isinstance(s, cstr):
        return _wcwidth(s.value)
    else:
        return _wcwidth(s)


def wcswidth(s: str | cstr) -> int:
    if isinstance(s, cstr):
        return _wcswidth(s.value)
    else:
        return _wcswidth(s)


##################
# Char's width
##################

@lru_cache
def _wcswidth(s: str) -> int:
    # FIXME: -1?
    return sum(_wcwidth(ch) for ch in s)


@lru_cache
def _wcwidth(ch: str) -> int:
    if len(ch) == 0:
        return 0

    ucs = ord(ch)

    # Printable ASCII
    if 32 <= ucs < 0x7f:
        return 1

    if ucs < 32 or 0x07f <= ucs < 0x0a0:
        return -1

    for a, b in WIDE:
        if a <= ucs <= b:
            return 2

    return 1


WIDE = (
    (0x01100, 0x0115f,),  # Hangul Choseong Kiyeok  ..Hangul Choseong Filler
    (0x0231a, 0x0231b,),  # Watch                   ..Hourglass
    (0x02329, 0x0232a,),  # Left-pointing Angle Brac..Right-pointing Angle Bra
    (0x023e9, 0x023ec,),  # Black Right-pointing Dou..Black Down-pointing Doub
    (0x023f0, 0x023f0,),  # Alarm Clock
    (0x023f3, 0x023f3,),  # Hourglass With Flowing Sand
    (0x025fd, 0x025fe,),  # White Medium Small Squar..Black Medium Small Squar
    (0x02614, 0x02615,),  # Umbrella With Rain Drops..Hot Beverage
    (0x02648, 0x02653,),  # Aries                   ..Pisces
    (0x0267f, 0x0267f,),  # Wheelchair Symbol
    (0x02693, 0x02693,),  # Anchor
    (0x026a1, 0x026a1,),  # High Voltage Sign
    (0x026aa, 0x026ab,),  # Medium White Circle     ..Medium Black Circle
    (0x026bd, 0x026be,),  # Soccer Ball             ..Baseball
    (0x026c4, 0x026c5,),  # Snowman Without Snow    ..Sun Behind Cloud
    (0x026ce, 0x026ce,),  # Ophiuchus
    (0x026d4, 0x026d4,),  # No Entry
    (0x026ea, 0x026ea,),  # Church
    (0x026f2, 0x026f3,),  # Fountain                ..Flag In Hole
    (0x026f5, 0x026f5,),  # Sailboat
    (0x026fa, 0x026fa,),  # Tent
    (0x026fd, 0x026fd,),  # Fuel Pump
    (0x02705, 0x02705,),  # White Heavy Check Mark
    (0x0270a, 0x0270b,),  # Raised Fist             ..Raised Hand
    (0x02728, 0x02728,),  # Sparkles
    (0x0274c, 0x0274c,),  # Cross Mark
    (0x0274e, 0x0274e,),  # Negative Squared Cross Mark
    (0x02753, 0x02755,),  # Black Question Mark Orna..White Exclamation Mark O
    (0x02757, 0x02757,),  # Heavy Exclamation Mark Symbol
    (0x02795, 0x02797,),  # Heavy Plus Sign         ..Heavy Division Sign
    (0x027b0, 0x027b0,),  # Curly Loop
    (0x027bf, 0x027bf,),  # Double Curly Loop
    (0x02b1b, 0x02b1c,),  # Black Large Square      ..White Large Square
    (0x02b50, 0x02b50,),  # White Medium Star
    (0x02b55, 0x02b55,),  # Heavy Large Circle
    (0x02e80, 0x02e99,),  # Cjk Radical Repeat      ..Cjk Radical Rap
    (0x02e9b, 0x02ef3,),  # Cjk Radical Choke       ..Cjk Radical C-simplified
    (0x02f00, 0x02fd5,),  # Kangxi Radical One      ..Kangxi Radical Flute
    (0x02ff0, 0x03029,),  # Ideographic Description ..Hangzhou Numeral Nine
    (0x03030, 0x0303e,),  # Wavy Dash               ..Ideographic Variation In
    (0x03041, 0x03096,),  # Hiragana Letter Small A ..Hiragana Letter Small Ke
    (0x0309b, 0x030ff,),  # Katakana-hiragana Voiced..Katakana Digraph Koto
    (0x03105, 0x0312f,),  # Bopomofo Letter B       ..Bopomofo Letter Nn
    (0x03131, 0x0318e,),  # Hangul Letter Kiyeok    ..Hangul Letter Araeae
    (0x03190, 0x031e3,),  # Ideographic Annotation L..Cjk Stroke Q
    (0x031ef, 0x0321e,),  # (nil)                   ..Parenthesized Korean Cha
    (0x03220, 0x03247,),  # Parenthesized Ideograph ..Circled Ideograph Koto
    (0x03250, 0x04dbf,),  # Partnership Sign        ..Cjk Unified Ideograph-4d
    (0x04e00, 0x0a48c,),  # Cjk Unified Ideograph-4e..Yi Syllable Yyr
    (0x0a490, 0x0a4c6,),  # Yi Radical Qot          ..Yi Radical Ke
    (0x0a960, 0x0a97c,),  # Hangul Choseong Tikeut-m..Hangul Choseong Ssangyeo
    (0x0ac00, 0x0d7a3,),  # Hangul Syllable Ga      ..Hangul Syllable Hih
    (0x0f900, 0x0faff,),  # Cjk Compatibility Ideogr..(nil)
    (0x0fe10, 0x0fe19,),  # Presentation Form For Ve..Presentation Form For Ve
    (0x0fe30, 0x0fe52,),  # Presentation Form For Ve..Small Full Stop
    (0x0fe54, 0x0fe66,),  # Small Semicolon         ..Small Equals Sign
    (0x0fe68, 0x0fe6b,),  # Small Reverse Solidus   ..Small Commercial At
    (0x0ff01, 0x0ff60,),  # Fullwidth Exclamation Ma..Fullwidth Right White Pa
    (0x0ffe0, 0x0ffe6,),  # Fullwidth Cent Sign     ..Fullwidth Won Sign
    (0x16fe0, 0x16fe3,),  # Tangut Iteration Mark   ..Old Chinese Iteration Ma
    (0x17000, 0x187f7,),  # (nil)
    (0x18800, 0x18cd5,),  # Tangut Component-001    ..Khitan Small Script Char
    (0x18d00, 0x18d08,),  # (nil)
    (0x1aff0, 0x1aff3,),  # Katakana Letter Minnan T..Katakana Letter Minnan T
    (0x1aff5, 0x1affb,),  # Katakana Letter Minnan T..Katakana Letter Minnan N
    (0x1affd, 0x1affe,),  # Katakana Letter Minnan N..Katakana Letter Minnan N
    (0x1b000, 0x1b122,),  # Katakana Letter Archaic ..Katakana Letter Archaic
    (0x1b132, 0x1b132,),  # Hiragana Letter Small Ko
    (0x1b150, 0x1b152,),  # Hiragana Letter Small Wi..Hiragana Letter Small Wo
    (0x1b155, 0x1b155,),  # Katakana Letter Small Ko
    (0x1b164, 0x1b167,),  # Katakana Letter Small Wi..Katakana Letter Small N
    (0x1b170, 0x1b2fb,),  # Nushu Character-1b170   ..Nushu Character-1b2fb
    (0x1f004, 0x1f004,),  # Mahjong Tile Red Dragon
    (0x1f0cf, 0x1f0cf,),  # Playing Card Black Joker
    (0x1f18e, 0x1f18e,),  # Negative Squared Ab
    (0x1f191, 0x1f19a,),  # Squared Cl              ..Squared Vs
    (0x1f200, 0x1f202,),  # Square Hiragana Hoka    ..Squared Katakana Sa
    (0x1f210, 0x1f23b,),  # Squared Cjk Unified Ideo..Squared Cjk Unified Ideo
    (0x1f240, 0x1f248,),  # Tortoise Shell Bracketed..Tortoise Shell Bracketed
    (0x1f250, 0x1f251,),  # Circled Ideograph Advant..Circled Ideograph Accept
    (0x1f260, 0x1f265,),  # Rounded Symbol For Fu   ..Rounded Symbol For Cai
    (0x1f300, 0x1f320,),  # Cyclone                 ..Shooting Star
    (0x1f32d, 0x1f335,),  # Hot Dog                 ..Cactus
    (0x1f337, 0x1f37c,),  # Tulip                   ..Baby Bottle
    (0x1f37e, 0x1f393,),  # Bottle With Popping Cork..Graduation Cap
    (0x1f3a0, 0x1f3ca,),  # Carousel Horse          ..Swimmer
    (0x1f3cf, 0x1f3d3,),  # Cricket Bat And Ball    ..Table Tennis Paddle And
    (0x1f3e0, 0x1f3f0,),  # House Building          ..European Castle
    (0x1f3f4, 0x1f3f4,),  # Waving Black Flag
    (0x1f3f8, 0x1f3fa,),  # Badminton Racquet And Sh..Amphora
    (0x1f400, 0x1f43e,),  # Rat                     ..Paw Prints
    (0x1f440, 0x1f440,),  # Eyes
    (0x1f442, 0x1f4fc,),  # Ear                     ..Videocassette
    (0x1f4ff, 0x1f53d,),  # Prayer Beads            ..Down-pointing Small Red
    (0x1f54b, 0x1f54e,),  # Kaaba                   ..Menorah With Nine Branch
    (0x1f550, 0x1f567,),  # Clock Face One Oclock   ..Clock Face Twelve-thirty
    (0x1f57a, 0x1f57a,),  # Man Dancing
    (0x1f595, 0x1f596,),  # Reversed Hand With Middl..Raised Hand With Part Be
    (0x1f5a4, 0x1f5a4,),  # Black Heart
    (0x1f5fb, 0x1f64f,),  # Mount Fuji              ..Person With Folded Hands
    (0x1f680, 0x1f6c5,),  # Rocket                  ..Left Luggage
    (0x1f6cc, 0x1f6cc,),  # Sleeping Accommodation
    (0x1f6d0, 0x1f6d2,),  # Place Of Worship        ..Shopping Trolley
    (0x1f6d5, 0x1f6d7,),  # Hindu Temple            ..Elevator
    (0x1f6dc, 0x1f6df,),  # Wireless                ..Ring Buoy
    (0x1f6eb, 0x1f6ec,),  # Airplane Departure      ..Airplane Arriving
    (0x1f6f4, 0x1f6fc,),  # Scooter                 ..Roller Skate
    (0x1f7e0, 0x1f7eb,),  # Large Orange Circle     ..Large Brown Square
    (0x1f7f0, 0x1f7f0,),  # Heavy Equals Sign
    (0x1f90c, 0x1f93a,),  # Pinched Fingers         ..Fencer
    (0x1f93c, 0x1f945,),  # Wrestlers               ..Goal Net
    (0x1f947, 0x1f9ff,),  # First Place Medal       ..Nazar Amulet
    (0x1fa70, 0x1fa7c,),  # Ballet Shoes            ..Crutch
    (0x1fa80, 0x1fa88,),  # Yo-yo                   ..Flute
    (0x1fa90, 0x1fabd,),  # Ringed Planet           ..Wing
    (0x1fabf, 0x1fac5,),  # Goose                   ..Person With Crown
    (0x1face, 0x1fadb,),  # Moose                   ..Pea Pod
    (0x1fae0, 0x1fae8,),  # Melting Face            ..Shaking Face
    (0x1faf0, 0x1faf8,),  # Hand With Index Finger A..Rightwards Pushing Hand
    (0x20000, 0x2fffd,),  # Cjk Unified Ideograph-20..(nil)
    (0x30000, 0x3fffd,),  # Cjk Unified Ideograph-30..(nil)
)


################
# Terminal input
################

class SpecialKey(Enum):
    ESC = auto(), list[str]()

    CRTL_C = auto(), ['\x03']
    TAB = auto(), ['\t']
    ENTER = auto(), ['\n']
    BACKSPACE = auto(), ['\x7f']

    UP = auto(), ['[A', 'OA']
    DOWN = auto(), ['[B', 'OB']
    RIGHT = auto(), ['[C', 'OC']
    LEFT = auto(), ['[D', 'OD']

    HOME = auto(), ['[H', 'OH', '[1~']
    INSERT = auto(), ['[2~']
    DEL = auto(), ['[3~']
    END = auto(), ['[F', 'OF', '[4~']
    PGUP = auto(), ['[5~']
    PGDOWN = auto(), ['[6~']

    F1 = auto(), ['OP']
    F2 = auto(), ['OQ']
    F3 = auto(), ['OR']
    F4 = auto(), ['OS']
    F5 = auto(), ['[15~']
    F6 = auto(), ['[17~']
    F7 = auto(), ['[18~']
    F8 = auto(), ['[19~']
    F9 = auto(), ['[20~']
    F10 = auto(), ['[21~']
    F11 = auto(), ['[23~']
    F12 = auto(), ['[24~']

    CRTL_UP = auto(), ['[1;5A']
    CRTL_DOWN = auto(), ['[1;5B']
    CRTL_RIGHT = auto(), ['[1;5C']
    CRTL_LEFT = auto(), ['[1;5D']

    CRTL_HOME = auto(), ['[1;5H']
    CRTL_INSERT = auto(), ['[2;5~']
    CRTL_DEL = auto(), ['[3;5~']
    CRTL_END = auto(), ['[1;5F']
    CRTL_PGUP = auto(), ['[6;5~']
    CRTL_PGDOWN = auto(), ['[5;5~']

    def __new__(cls, *args, **kwds):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        return obj

    def __init__(self, _value: int, seqs: list[str]):
        self.seqs = seqs

    @staticmethod
    def get(seq: str) -> str | SpecialKey:
        for key in SpecialKey:
            if seq in key.seqs:
                return key
        return ''


def read() -> str | SpecialKey:
    return _read(lambda: sys.stdin.read(1))


def _read(next: Callable[[], str]) -> str | SpecialKey:
    if (ch := next()) == '':
        return ''

    # Is not a escape sequence
    if ch != '\x1b':
        # Control keys
        if ch == '\x03':
            return SpecialKey.CRTL_C
        if ch == '\t':
            return SpecialKey.TAB
        if ch == '\r' or ch == '\n':
            return SpecialKey.ENTER
        if ch == '\x7f' or ch == '\b':
            return SpecialKey.BACKSPACE
        if ord(ch) < 32:
            return ''
        # Other keys
        return ch

    if (ch := next()) not in ['?', 'O', '[']:
        return SpecialKey.ESC

    # ESC ? Letter
    # ESC O Letter
    if ch in ['?', 'O']:
        return SpecialKey.get(ch + next())

    ch = next()
    # ESC [ Letter
    if not ch.isdigit():
        return SpecialKey.get('[' + ch)

    # ESC [ n ~
    # ESC [ n ; m R
    # ESC [ n ; m Letter

    seq = '[' + ch
    while (ch := next()).isdigit():
        seq += ch

    if ch != ';':
        return SpecialKey.get(seq + ch)

    seq += ';'
    while (ch := next()).isdigit():
        seq += ch

    return SpecialKey.get(seq + ch)


################
# Terminal setup
################

# TODO: add debug key read

# References
# - Console Virtual Terminal Sequences (Windows)
#   (https://learn.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences)
# - Build your own Command Line with ANSI escape codes
#   (https://www.lihaoyi.com/post/BuildyourownCommandLinewithANSIescapecodes.html)
# - Build Your Own Text Editor
#   (https://viewsourcecode.org/snaptoken/kilo/
# - ANSI/DEC VT Terminal Keycode Sequences
#   (https://mdfs.net/Docs/Comp/Comms/ANSIKeys)
# - Parsing ANSI/VT Terminal Keycode Sequences
#   (https://mdfs.net/Docs/Comp/Comms/ANSIParse)


ENTER_AM_MODE = '\x1b[?1049h'
EXIT_AM_MODE = '\x1b[?1049l'
HIDE_CURSOR = '\x1b[?25l'
SHOW_CURSOR = '\x1b[?25h'
CLEAR_SCREEN = '\x1b[2J'
MOVE_CURSOR_HOME = '\x1b[H'


class AlternateMode:
    def __enter__(self) -> AlternateMode:
        sys.stdout.write(ENTER_AM_MODE)
        sys.stdout.write(CLEAR_SCREEN)
        sys.stdout.write(MOVE_CURSOR_HOME)
        sys.stdout.write(HIDE_CURSOR)
        sys.stdout.flush()
        return self

    def __exit__(self, _exception_type, _exception_value, _exception_traceback) -> None:
        sys.stdout.write(EXIT_AM_MODE)
        sys.stdout.write(SHOW_CURSOR)
        sys.stdout.flush()


if sys.platform == 'win32':
    import ctypes
    from ctypes.wintypes import DWORD, HANDLE
    from ctypes import byref

    # Handles constants
    STD_INPUT_HANDLE = -10
    STD_OUTPUT_HANDLE = -11
    INVALID_HANDLE = -1

    # From https://learn.microsoft.com/en-us/windows/console/setconsolemode
    ENABLE_VIRTUAL_TERMINAL_INPUT = 0x0200
    ENABLE_PROCESSED_INPUT = 0x0001
    ENABLE_LINE_INPUT = 0x0002
    ENABLE_ECHO_INPUT = 0x0004
    ENABLE_PROCESSED_OUTPUT = 0x0001
    DISABLE_NEWLINE_AUTO_RETURN = 0x0008
    ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004

    class Terminal:
        in_handle: HANDLE
        in_mode = DWORD()

        out_mode = DWORD()
        out_handle: HANDLE

        def __init__(self) -> None:
            self.kernel32 = ctypes.windll.kernel32
            self.in_handle = self.kernel32.GetStdHandle(STD_INPUT_HANDLE)
            self.out_handle = self.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
            if not os.isatty(sys.stdin.fileno()) or \
                    self.in_handle is None or \
                    self.in_handle == INVALID_HANDLE or \
                    self.out_handle is None or\
                    self.out_handle == INVALID_HANDLE:
                cannot_setup_term('cannot get in/out handles')

        def set_inmode(self) -> None:
            if self.kernel32.GetConsoleMode(self.in_handle, byref(self.in_mode)):
                mode = (self.in_mode.value | ENABLE_VIRTUAL_TERMINAL_INPUT) & \
                    ~(ENABLE_PROCESSED_INPUT |
                      ENABLE_LINE_INPUT |
                      ENABLE_ECHO_INPUT)
                if self.kernel32.SetConsoleMode(self.in_handle, DWORD(mode)):
                    return
            cannot_setup_term('input mode')

        def set_outmode(self) -> None:
            if self.kernel32.GetConsoleMode(self.out_handle, byref(self.out_mode)):
                mode = self.out_mode.value | \
                    ENABLE_VIRTUAL_TERMINAL_PROCESSING | \
                    DISABLE_NEWLINE_AUTO_RETURN | \
                    ENABLE_PROCESSED_OUTPUT
                if self.kernel32.SetConsoleMode(self.out_handle, DWORD(mode)):
                    return
            cannot_setup_term('output mode')

        def __enter__(self) -> Terminal:
            self.set_inmode()
            self.set_outmode()
            return self

        def __exit__(self, _exception_type, _exception_value, _exception_traceback) -> None:
            self.kernel32.SetConsoleMode(self.in_handle, self.in_mode)
            self.kernel32.SetConsoleMode(self.out_handle, self.out_mode)

elif sys.platform == 'linux' or sys.platform == 'darwin':
    import termios
    import tty

    class Terminal:
        settings: None | list = None

        def __init__(self) -> None:
            if not os.isatty(sys.stdin.fileno()):
                cannot_setup_term('is not a tty')

        def __enter__(self) -> Terminal:
            self.settings = termios.tcgetattr(sys.stdin)
            tty.setraw(sys.stdin)
            settings = termios.tcgetattr(sys.stdin)
            cc = settings[6]
            cc[termios.VMIN] = 0
            cc[termios.VTIME] = 0
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
            return self

        def __exit__(self, _exception_type, _exception_value, _exception_traceback) -> None:
            if self.settings is not None:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.settings)

else:
    raise Exception(f'Unsuported platform {sys.platform}')


def cannot_setup_term(msg: str) -> Never:
    print('Cannot setup terminal ({msg}). Are you in an ansi terminal?')
    sys.exit(1)
