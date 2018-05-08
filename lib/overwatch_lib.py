import sys
from enum import Enum, auto
from typing import Tuple

try:
    from ctypes import windll
except ImportError:
    sys.exit('This script is only compatible with Windows')

_DC = windll.user32.GetDC(0)

# TODO write calibration tool to accommodate different brightness settings

_COLORS = {                                 # (RRR, GGG, BBB)
    'in_menu': (24, 133, 186),              # (16, 28, 41)
    'waiting': (175, 178, 185),             # (21, 24, 43)
    'character_select': (255, 255, 255),    # (67,85,195)
}

_PIXELS = {
    'in_menu': [(1936, 49), (1936, 109), (1989, 49), (1976, 87)],
    'waiting': [(2369, 1204), (2415, 1245), (2377, 1249), (2343, 1270)],
    'character_select': [(2357, 250), (2402, 250), (2437, 250), (2483, 250)],

}


def _get_pixel(x: int, y: int) -> int:
    """
    Get a pixel from the screen at (x, y)
    :param x: The x-coordinate
    :param y: The y-coordinate
    :return: An integer in the byte format 0xBBGGRR
    :note: These integers are calculated by taking the hex values of the RGB, then converting 0xBBGGRR to base 10
    """
    return windll.gdi32.GetPixel(_DC, x, y)


def _pixel_to_rgb(pixel: int) -> Tuple[int, int, int]:
    """
    Convert a pixel in the byte format 0xBBGGRR to a tuple
    :param pixel: The pixel to convert
    :return: A tuple in the format (R, G, B)
    """
    r = pixel & 0xff
    g = (pixel >> 8) & 0xff
    b = (pixel >> 16) & 0xff
    return r, g, b


def _in_acceptable_range(color_to_check: Tuple[int, int, int], color_ref: Tuple[int, int, int], distance: int) -> bool:
    """
    Check if each color value of a pixel is with a specified distance of the color values in the reference color
    :param color_to_check: The color to perform the bounds check on
    :param color_ref: The color to use as the reference
    :param distance: The maximum allowed distance
    :return: True if color_to_check is within the distance, false otherwise
    """
    if color_ref[0] - distance < color_to_check[0] < color_ref[0] + distance:
        if color_ref[1] - distance < color_to_check[1] < color_ref[1] + distance:
            if color_ref[2] - distance < color_to_check[2] < color_ref[2] + distance:
                return True
    return False


def _in_menu() -> bool:
    """
    Check if the Overwatch main menu is visible
    :return: True if the main menu is visible, false otherwise
    """
    # Check the bottom menu bar at the far left.
    errors = len([pair for pair in _PIXELS['in_menu']
                  if not _in_acceptable_range(_pixel_to_rgb(_get_pixel(*pair)), _COLORS['in_menu'], distance=2)])
    # Allow one error because the mouse may be covering one of the spots
    return errors < 2


def _waiting() -> bool:
    """
    Check if Check if Overwatch is loading the map, showing the 'VS' screen
    :return: True if the game is in the waiting state, false otherwise
    """
    errors = len([pair for pair in _PIXELS['waiting']
                  if not _in_acceptable_range(_pixel_to_rgb(_get_pixel(*pair)), _COLORS['waiting'], distance=2)])
    return errors < 2


def _in_character_select() -> bool:
    """
    Check if the user is in the character select menu
    :return: True if the character select menu is visible, false otherwise
    """
    errors = len([pair for pair in _PIXELS['character_select']
                  if not _in_acceptable_range(_pixel_to_rgb(_get_pixel(*pair)), _COLORS['character_select'], distance=3)])
    return errors < 2


class GameState(Enum):
    UNKNOWN = auto()

    IN_MENU = auto()
    WAITING = auto()
    CHARACTER_SELECT = auto()


def get_state() -> GameState:
    if _in_menu():
        return GameState.IN_MENU
    if _waiting():
        return GameState.WAITING
    if _in_character_select():
        return GameState.CHARACTER_SELECT

    return GameState.UNKNOWN
