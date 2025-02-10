#!/usr/bin/env python3
# The line above tells the Raspberry Pi that we want to run this
#   script in Python 3 - so we don't have to tell it later

import board
import neopixel
from time import sleep

# An example program that cycles through Red, Green Blue and then stops

LEDcount = 8

pixels = neopixel.NeoPixel(board.D10, LEDcount)

#red
pixels.fill((100,0,0))
sleep(1)
#green
pixels.fill((0,100,0))
sleep(1)
#blue
pixels.fill((0,0,100))
sleep(1)

# and off
pixels.fill((0,0,0))
