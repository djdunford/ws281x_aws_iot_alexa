#!/usr/bin/env python3
"""Raspbian python app to control a WS281X LED string

Controller for WS281x LED string
with AWSIoT integration to allow remote control

originally based on strandtest.py by Tony DiCola (tony@tonydicola.com)
see https://github.com/rpi-ws281x/rpi-ws281x-python

Author: Darren Dunford (djdunford@gmail.com)
"""

import configparser
import json
import logging.handlers
import os
import sys
import threading
import time
import yaml
import queue
from gpiozero import CPUTemperature
from rpi_ws281x import PixelStrip
from ledcontroller.deviceshadowhandler import DeviceShadowHandler
from ledcontroller.effects import color_wipe, LightEffect, color
from exceptions import InterruptException, ExitException

# LED strip configuration:
LED_COUNT = 50  # Number of LED pixels.
LED_PIN = 18  # GPIO pin connected to the pixels (18 uses PWM!).
# LED_PIN = 10        # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA = 10  # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
LED_INVERT = False  # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL = 0  # set to '1' for GPIOs 13, 19, 41, 45 or 53


# define helper functions
def post_temperature(interval: int=300):
    """
    thread safe daemon function posts temperature every interval seconds

    :param interval:
    :return:
    """
    while True:
        cpu = CPUTemperature()
        device.post_temperature(cpu.temperature)
        time.sleep(interval)


# Main program logic follows:
if __name__ == '__main__':

    # Change CWD to location of this script
    os.chdir(os.path.dirname(sys.argv[0]))

    # read config file and settings
    config = configparser.ConfigParser()
    config.read('ledcontroller.ini')

    # retrieve AWSIoT settings from config file
    AWSIOT_PRIVATE_KEY_PATH = config['aws']['privatekeypath']
    AWSIOT_CERTIFICATE_PATH = config['aws']['certificatepath']
    AWSIOT_HOST = config['aws']['host']
    AWSIOT_ROOT_CA_PATH = config['aws']['rootcapath']
    AWSIOT_THINGNAME = config['aws']['thingname']

    # debug flag
    debugdict = config['debug']
    DEBUG = debugdict.getboolean('debug', fallback=False)  # if debug true then additional logging to syslog is enabled
    SYSLOG = debugdict.getboolean('syslog', fallback=True)  # if syslog is false then all output to syslog is suppressed

    # setup logging at root level and set log level according to ini file
    LOGGER = logging.getLogger("ledcontroller")
    if DEBUG:
        LOGGER.setLevel(logging.DEBUG)
    elif SYSLOG:
        LOGGER.setLevel(logging.INFO)
    else:
        LOGGER.setLevel(logging.WARNING)

    # setup log handler to send messages to syslog
    sysloghandler = logging.handlers.SysLogHandler(address='/dev/log')
    sysloghandler.setLevel(DEBUG)  # set to most verbose level, handles all messages from LOGGER
    logging_formatter = logging.Formatter('[%(levelname)s] %(name)s: %(message)s')
    sysloghandler.setFormatter(logging_formatter)
    LOGGER.addHandler(sysloghandler)

    # read parameters from ini file and build params dictionary
    globs = config['settings']
    settings = {}
    settings.update({'post_temperature_interval': globs.getint('post_temperature_interval', fallback=300)})

    # create master set of keys from parameter array
    # used later to prevent injection of any other keys
    SETTINGS_KEYS = set(settings)

    # if debugging then dump params in to syslog
    LOGGER.info("Parameters loaded: %s", json.dumps(settings, indent=2))

    # connect to AWSIoT
    device = DeviceShadowHandler(
        host=AWSIOT_HOST,
        root_ca_path=AWSIOT_ROOT_CA_PATH,
        certificate_path=AWSIOT_CERTIFICATE_PATH,
        thingname=AWSIOT_THINGNAME,
        private_key_path=AWSIOT_PRIVATE_KEY_PATH)

    # Create NeoPixel object with appropriate configuration and initialise library
    strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
    strip.begin()

    # launch daemon thread to post temperature to AWSIoT at required interval
    temperaturepost_thread = threading.Thread(
        target=post_temperature,
        args=(settings.get('post_temperature_interval'),),
        daemon=True)
    temperaturepost_thread.start()

    # load in light program
    with open("program.yaml", 'r') as stream:
        try:
            programs = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    run_program = "autostart"
    lights_thread: LightEffect = LightEffect(strip)

    # main loop for running lights programs and reacting to events
    try:
        while True:

            # main loop for running a specific light program and reacting to events
            try:

                # select program
                program = programs.get(run_program)
                device.status_post(f"RUNNING PROGRAM {run_program}")
                lights_thread: LightEffect = LightEffect(strip, program = program)
                lights_thread.start()

                # react to event queue
                while True:
                    try:
                        event = device.event_queue.get_nowait()
                        if event == {"command": "STOP"}:
                            raise ExitException
                    except queue.Empty:
                        pass
                    time.sleep(0.1)

            # if program interrupted then clear lights ready for next program
            except InterruptException:
                device.status_post("STOPPING CURRENT PROGRAM")
                try:
                    lights_thread.stop()
                    lights_thread.join()
                except RuntimeError:
                    pass
                color_wipe(strip, color(0, 0, 0), 10)
                device.status_post("CURRENT PROGRAM STOPPED")

    # to exit cleanup thread and terminate
    except (KeyboardInterrupt, ExitException):
        device.status_post("STOPPING")
        try:
            lights_thread.stop()
            lights_thread.join()
        except RuntimeError:
            pass
        color_wipe(strip, color(0, 0, 0), 10)
        device.status_post("STOPPED")
