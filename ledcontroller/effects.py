#!/usr/bin/env python3
"""Library of programmed effects for WS281X LED strings
"""

# effects.py
#
# originally based on strandtest.py by Tony DiCola (tony@tonydicola.com)
# see https://github.com/rpi-ws281x/rpi-ws281x-python

import time
import logging
import threading

LOGGER = logging.getLogger(__name__)

def Color(red, green, blue, white=0):
    """Convert the provided red, green, blue color to a 24-bit color value.
    Each color component should be a value 0-255 where 0 is the lowest intensity
    and 255 is the highest intensity.

    Note the sequencing has been changed from RGB (most significant->least significant) to
    GRB - this seems to be a "feature" of the light strip I have!
    """
    return (white << 24) | (green << 16) | (red << 8) | blue

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


class LightSequence(threading.Thread):

    def __init__(self, strip, sequence: int = 1):
        """Initialise thread with strip object for LED strip

        :param strip:
        :param sequence:
        """

        threading.Thread.__init__(self)             # call parent constructor
        self._shutdown_event = threading.Event()    # set event flag to terminate thread
        self._strip = strip                         # set to rpi_ws281x.PixelStrip object for LED strip to control
        self._sequence = sequence                   # set to desired sequence

    def run(self):
        """Run light effect selected by sequence number passed to constructor

        :return:
        """

        start_time = time.time()

        # UK emergency blue light effect
        if self._sequence == 1:
            while not self._shutdown_event.is_set():
                curr_time = time.time() * 2
                for i in range(self._strip.numPixels()):
                    if int(curr_time % 2) > 0:
                        if i < (self._strip.numPixels() // 2):
                            if (int(curr_time * 10) % 2) > 0:
                                self._strip.setPixelColor(i, Color(0, 0, 255))
                            else:
                                self._strip.setPixelColor(i, Color(0, 0, 0))
                        else:
                            self._strip.setPixelColor(i, Color(0, 0, 0))
                    else:
                        if i < (self._strip.numPixels() // 2):
                            self._strip.setPixelColor(i, Color(0, 0, 0))
                        else:
                            if (int(curr_time * 10) % 2) > 0:
                                self._strip.setPixelColor(i, Color(0, 0, 255))
                            else:
                                self._strip.setPixelColor(i, Color(0, 0, 0))
                self._strip.show()
                time.sleep(0.01)

        # Static rainbow effect (requires LED strip of 50 LEDs)
        elif self._sequence == 2:
            rainbow = [Color(255,0,0),
                       Color(255,127,0),
                       Color(255,255,0),
                       Color(0,255,0),
                       Color(0,0,255),
                       Color(46,43,95),
                       Color(139,0,255)]
            length = len(rainbow)
            for i in range(length):
                self._strip.setPixelColor(4+(i*3),rainbow[i])
                self._strip.setPixelColor(5+(i*3),rainbow[i])
                self._strip.setPixelColor(6+(i*3),rainbow[i])
                self._strip.setPixelColor(22+((length-i)*3),rainbow[i])
                self._strip.setPixelColor(23+((length-i)*3),rainbow[i])
                self._strip.setPixelColor(24+((length-i)*3),rainbow[i])

            self._strip.show()

    def stop(self):
        """Set stop flag for thread

        :return:
        """

        self._shutdown_event.set()


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
