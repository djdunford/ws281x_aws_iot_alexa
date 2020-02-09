#!/usr/bin/env python3
"""Library of programmed effects for WS281X LED strings
"""

# effects.py
#
# originally based on strandtest.py by Tony DiCola (tony@tonydicola.com)
# see https://github.com/rpi-ws281x/rpi-ws281x-python

import time
from rpi_ws281x import Color


def color_wipe(strip, color, wait_ms: int = 50):
    """Wipe color across display a pixel at a time.

    :param strip:
    :param color:
    :param wait_ms:
    :return:
    """
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
        strip.show()
        time.sleep(wait_ms / 1000.0)


def theater_chase(strip, color, wait_ms: int = 50, iterations: int = 10):
    """Movie theater light style chaser animation.

    :param strip:
    :param color:
    :param wait_ms:
    :param iterations:
    :return:
    """
    for j in range(iterations):
        for q in range(3):
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i + q, color)
            strip.show()
            time.sleep(wait_ms / 1000.0)
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i + q, 0)


def wheel(pos: int):
    """Generate rainbow colors across 0-255 positions.

    :param pos:
    :return:
    """
    if pos < 85:
        return Color(pos * 3, 255 - pos * 3, 0)
    if pos < 170:
        pos -= 85
        return Color(255 - pos * 3, 0, pos * 3)
    else:
        pos -= 170
        return Color(0, pos * 3, 255 - pos * 3)


def rainbow(strip, wait_ms: int = 20, iterations: int = 1):
    """Draw rainbow that fades across all pixels at once.

    :param strip:
    :param wait_ms:
    :param iterations:
    :return:
    """
    for j in range(256 * iterations):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, wheel((i + j) & 255))
        strip.show()
        time.sleep(wait_ms / 1000.0)


def rainbow_cycle(strip, wait_ms: int = 20, iterations: int = 5):
    """Draw rainbow that uniformly distributes itself across all pixels.

    :param strip:
    :param wait_ms:
    :param iterations:
    :return:
    """
    for j in range(256 * iterations):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, wheel(
                (int(i * 256 / strip.numPixels()) + j) & 255))
        strip.show()
        time.sleep(wait_ms / 1000.0)


def theater_chase_rainbow(strip, wait_ms: int = 50):
    """Rainbow movie theater light style chaser animation.

    :param strip:
    :param wait_ms:
    :return:
    """
    for j in range(256):
        for q in range(3):
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i + q, wheel((i + j) % 255))
            strip.show()
            time.sleep(wait_ms / 1000.0)
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i + q, 0)
