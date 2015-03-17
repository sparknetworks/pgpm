class TermStyle(object):
    """
    Text styles for terminal
    """
    def __init__(self):
        pass

    RESET = '\033[0m'  # reset; clears all colors and styles (to white on black)
    BOLD_ON = '\033[1m'
    BOLD_OFF = '\033[22m'
    ITALICS_ON = '\033[3m'
    ITALICS_OFF = '\033[23m'
    UNDERLINE_ON = '\033[4m'
    UNDERLINE_OFF = '\033[24m'
    INVERSE_ON = '\033[7m'  # inverse on; reverses foreground & background colors
    INVERSE_OFF = '\033[27m'
    STRIKETHROUGH_ON = '\033[9m'
    STRIKETHROUGH_OFF = '\033[29m'
    FONT_BLACK = '\033[30m'  # set foreground color to black
    FONT_RED = '\033[31m'  # set foreground color to red
    FONT_GREEN = '\033[32m'  # set foreground color to green
    FONT_YELLOW = '\033[33m'  # set foreground color to yellow
    FONT_BLUE = '\033[34m'  # set foreground color to blue
    FONT_MAGENTA = '\033[35m'  # set foreground color to magenta (purple)
    FONT_CYAN = '\033[36m'  # set foreground color to cyan
    FONT_WHITE = '\033[37m'  # set foreground color to white
    FONT_DEFAULT = '\033[39m'  # set foreground color to default (white)
    BG_BLACK = '\033[40m'  # set background color to black
    BG_RED = '\033[41m'  # set background color to red
    BG_GREEN = '\033[42m'  # set background color to green
    BG_YELLOW = '\033[43m'  # set background color to yellow
    BG_BLUE = '\033[44m'  # set background color to blue
    BG_MAGENTA = '\033[45m'  # set background color to magenta (purple)
    BG_CYAN = '\033[46m'  # set background color to cyan
    BG_WHITE = '\033[47m'  # set background color to white
    BG_DEFAULT = '\033[49m'  # set background color to default (black)

    PREFIX_INFO = BG_WHITE + FONT_BLACK + UNDERLINE_ON + 'INFO:' + RESET + ' '
    PREFIX_WARNING = BG_YELLOW + FONT_BLACK + UNDERLINE_ON + 'WARN:' + RESET + ' '
    PREFIX_ERROR = BG_RED + FONT_BLACK + UNDERLINE_ON + 'ERR:' + RESET + ' '
    PREFIX_INFO_IMPORTANT = '  ==> ' + RESET

    def disable(self):
        self.RESET = ''
        self.BOLD_ON = ''
        self.BOLD_OFF = ''
        self.ITALICS_ON = ''
        self.ITALICS_OFF = ''
        self.UNDERLINE_ON = ''
        self.UNDERLINE_OFF = ''
        self.INVERSE_ON = ''
        self.INVERSE_OFF = ''
        self.STRIKETHROUGH_ON = ''
        self.STRIKETHROUGH_OFF = ''
        self.FONT_BLACK = ''
        self.FONT_RED = ''
        self.FONT_GREEN = ''
        self.FONT_YELLOW = ''
        self.FONT_BLUE = ''
        self.FONT_MAGENTA = ''
        self.FONT_CYAN = ''
        self.FONT_WHITE = ''
        self.FONT_DEFAULT = ''
        self.BG_BLACK = ''
        self.BG_RED = ''
        self.BG_GREEN = ''
        self.BG_YELLOW = ''
        self.BG_BLUE = ''
        self.BG_MAGENTA = ''
        self.BG_CYAN = ''
        self.BG_WHITE = ''
        self.BG_DEFAULT = ''
