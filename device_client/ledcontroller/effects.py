#!/usr/bin/env python3
"""Library of programmed effects for WS281X LED strings
"""

# effects.py
#
# by Darren Dunford
#
# originally based on strandtest.py by Tony DiCola (tony@tonydicola.com)
# see https://github.com/rpi-ws281x/rpi-ws281x-python

import logging
import threading
import time
from rpi_ws281x import PixelStrip

LOGGER = logging.getLogger(__name__)


class LockingPixelStrip(PixelStrip):
    """extends PixelStrip to expose a thread lock which can be used to ensure exclusive access to the strip

    """

    lock: threading.Lock

    def __init__(self, num, pin, freq, dma, invert, brightness, channel):
        """constructor called to construct the thread lock object

        :param num:
        :param pin:
        """
        super().__init__(num, pin, freq, dma, invert, brightness, channel)
        self.lock = threading.Lock()


def color(red: int, green: int, blue: int, white: int = 0):
    """Convert the provided red, green, blue color to a 24-bit color value.
    Each color component should be a value 0-255 where 0 is the lowest intensity
    and 255 is the highest intensity.

    Note the sequencing has been changed from RGB (most significant->least significant) to
    GRB - this seems to be a "feature" of the light strip I have!

    :param red: red component 0-255
    :param green: green component 0-255
    :param blue: blue component 0-255
    :param white: overall brightness, 0-255, defaults to 0
    :return:
    """
    return (white << 24) | (green << 16) | (red << 8) | blue


def color_wipe(strip: PixelStrip, color: color, wait_ms: int = 50):
    """Wipe color across display a pixel at a time.

    :param strip: PixelStrip object to apply the effect to
    :param color: Color to wipe
    :param wait_ms: blocking time to wait (in ms) before returning
    :return:
    """
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
        strip.show()
        time.sleep(wait_ms / 1000.0)


class LightEffect(threading.Thread):
    """Thread object constructed to run a specific effect on a specific PixelStrip

    """

    def __init__(self, strip: LockingPixelStrip, effect: int = 1, program=None):
        """Initialise thread with strip object for LED strip

        :param strip: PixelStrip to apply the effect to
        :param effect: effect to initiate
        """

        threading.Thread.__init__(self)  # call parent constructor
        self._shutdown_event = threading.Event()  # set event flag to terminate thread
        self._strip = strip  # set to rpi_ws281x.PixelStrip object for LED strip to control
        if program:
            self._program = program
        else:
            self._program = [{"effect": effect}]

    def run(self):
        """Run light effect selected by effect number passed to constructor

        :return:
        """

        with self._strip.lock:
            for step in self._program:
                start_time: float = time.time()

                # UK emergency blue light effect
                if step.get("effect") == 1 or step.get("effect") == "EmergencyBlueLight":
                    while (not self._shutdown_event.is_set()) and (
                            time.time() < start_time + step.get("duration", 86400)):
                        curr_time = time.time() * 2
                        for i in range(self._strip.numPixels()):
                            if int(curr_time % 2) > 0:
                                if i < (self._strip.numPixels() // 2):
                                    if (int(curr_time * 10) % 2) > 0:
                                        self._strip.setPixelColor(i, color(0, 0, 255))
                                    else:
                                        self._strip.setPixelColor(i, color(0, 0, 0))
                                else:
                                    self._strip.setPixelColor(i, color(0, 0, 0))
                            else:
                                if i < (self._strip.numPixels() // 2):
                                    self._strip.setPixelColor(i, color(0, 0, 0))
                                else:
                                    if (int(curr_time * 10) % 2) > 0:
                                        self._strip.setPixelColor(i, color(0, 0, 255))
                                    else:
                                        self._strip.setPixelColor(i, color(0, 0, 0))
                        self._strip.show()
                        time.sleep(0.01)

                # Static rainbow effect (requires LED strip of 50 LEDs)
                elif step.get("effect") == 2 or step.get("effect") == "RainbowStatic":
                    rainbow = [color(255, 0, 0),
                               color(255, 127, 0),
                               color(255, 255, 0),
                               color(0, 255, 0),
                               color(0, 0, 255),
                               color(46, 43, 95),
                               color(139, 0, 255)]
                    length = len(rainbow)
                    for i in range(length):
                        self._strip.setPixelColor(4 + (i * 3), rainbow[i])
                        self._strip.setPixelColor(5 + (i * 3), rainbow[i])
                        self._strip.setPixelColor(6 + (i * 3), rainbow[i])
                        self._strip.setPixelColor(22 + ((length - i) * 3), rainbow[i])
                        self._strip.setPixelColor(23 + ((length - i) * 3), rainbow[i])
                        self._strip.setPixelColor(24 + ((length - i) * 3), rainbow[i])

                    self._strip.show()

                # rainbow_cycle effect
                elif step.get("effect") == 3 or step.get("effect") == "RainbowCycle":

                    wait_ms: int = 20

                    while (not self._shutdown_event.is_set()) and (
                            time.time() < start_time + step.get("duration", 86400)):
                        for j in range(256):
                            for i in range(self._strip.numPixels()):
                                self._strip.setPixelColor(i, wheel(
                                    (int(i * 256 / self._strip.numPixels()) + j) & 255))
                            self._strip.show()
                            time.sleep(wait_ms / 1000.0)

                # landing strip effect
                elif step.get("effect") == 4 or step.get("effect") == "LandingStrip":

                    while (not self._shutdown_event.is_set()) and (
                            time.time() < start_time + step.get("duration", 86400)):
                        for i in range(self._strip.numPixels()):
                            self._strip.setPixelColor(i, color(200, 200, 200))
                        self._strip.show()
                        time.sleep(0.05)
                        for i in range(self._strip.numPixels()):
                            if (i % 2) == 0:
                                self._strip.setPixelColor(i, color(0, 0, 0))
                        self._strip.show()
                        time.sleep(0.95)

                # red, white and blue (for VE day) - requires ledstip of length 50
                elif step.get("effect") == 5 or step.get("effect") == "RedWhiteBlueVEDay":

                    for i in range(8):
                        self._strip.setPixelColor(i * 6 + 1, color(255, 0, 0))
                        self._strip.setPixelColor(i * 6 + 2, color(255, 0, 0))
                        self._strip.setPixelColor(i * 6 + 3, color(255, 255, 255))
                        self._strip.setPixelColor(i * 6 + 4, color(255, 255, 255))
                        self._strip.setPixelColor(i * 6 + 5, color(0, 0, 255))
                        self._strip.setPixelColor(i * 6 + 6, color(0, 0, 255))

                    self._strip.show()

            # after program complete, loop until terminate flag received
            while not self._shutdown_event.is_set():
                pass

    def stop(self):
        """Set stop flag for thread

        :return:
        """

        self._shutdown_event.set()


def theater_chase(strip: PixelStrip, color: color, wait_ms: int = 50, iterations: int = 10):
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
        return color(pos * 3, 255 - pos * 3, 0)
    if pos < 170:
        pos -= 85
        return color(255 - pos * 3, 0, pos * 3)
    pos -= 170
    return color(0, pos * 3, 255 - pos * 3)


def rainbow(strip: PixelStrip, wait_ms: int = 20, iterations: int = 1):
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


def rainbow_cycle(strip: PixelStrip, wait_ms: int = 20, iterations: int = 5):
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


def theater_chase_rainbow(strip: PixelStrip, wait_ms: int = 50):
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
