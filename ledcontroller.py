#!/usr/bin/env python3
#
# ledcontroller.py
#
# Controller for WS281x LED string
# with AWSIoT integration to allow remote control
#
# originally based on strandtest.py by Tony DiCola (tony@tonydicola.com)
# see https://github.com/rpi-ws281x/rpi-ws281x-python
#
# Author: Darren Dunford (djdunford@gmail.com)
#
import json
import sys
import time
from rpi_ws281x import PixelStrip, Color
import os
import configparser
import logging
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTShadowClient

# LED strip configuration:
LED_COUNT = 50  # Number of LED pixels.
LED_PIN = 18  # GPIO pin connected to the pixels (18 uses PWM!).
# LED_PIN = 10        # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA = 10  # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
LED_INVERT = False  # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL = 0  # set to '1' for GPIOs 13, 19, 41, 45 or 53

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

# setup logging and set log level according to ini file
LOGGER = logging.getLogger("alexa")
if DEBUG:
    LOGGER.setLevel(logging.DEBUG)
elif SYSLOG:
    LOGGER.setLevel(logging.INFO)
else:
    LOGGER.setLevel(logging.WARNING)

# read parameters from ini file and build params dictionary
globs = config['settings']
settings = {}
# params.update({'persistentshadow': globs.getboolean('persistentshadow', fallback=False)})

# create master set of keys from parameter array
# used later to prevent injection of any other keys
SETTINGS_KEYS = set(settings)

# if debugging then dump params in to syslog
LOGGER.info("Parameters loaded:" + json.dumps(settings, indent=2))


#
#
# Define functions which implement AWSIoT integration
# define functions and classes
class ShadowCallbackContainer:

    # constructor
    def __init__(self, shadow_instance):
        self.deviceShadowInstance = shadow_instance
        self.callbackresponses = {}

    # Custom shadow callback for delta -> remote triggering
    def customShadowCallback_Delta(self, payload, responseStatus, token):
        # payload is a JSON string ready to be parsed using json.loads(...)

        # declare global variables updated by this procedure
        global trigger
        # global lock
        global settings

        # DEBUG dump payload in to syslog
        LOGGER.debug(payload)

        # create JSON dictionary from payload
        payloadDict = json.loads(payload)
        newPayload = {"state": {"reported": {"status": "RUNNING"}, "desired": None}}

        # check for parameter update
        new_settings = payloadDict.get('state').get('settings')

        # remove unwanted keys (avoids external injection of unwanted keys)
        unwanted_keys = set(new_settings) - SETTINGS_KEYS
        for unwanted_key in unwanted_keys:
            del payloadDict["state"]["settings"][unwanted_key]

        # update parameters
        settings.update(payloadDict.get('state').get('settings'))

        # report status back to AWSIoT
        newPayload.update({"state": {"reported": {"settings": settings}}})

        # output syslog message
        LOGGER.info("Settings updated: " + json.dumps(settings))

        # check for triggering
        newState = payloadDict.get('state').get('command')
        if newState == "TRIGGER":
            trigger = int(payloadDict.get('state').get('sequence', 0))
            newPayload.update({"state": {
                "reported": {"command": "TRIGGERED", "sequencerun": trigger, "sequence": None}}})

        LOGGER.info("Shadow update: " + json.dumps(newPayload))

        # update shadow instance status
        self.deviceShadowInstance.shadowUpdate(json.dumps(newPayload), None, 5)

    # Custom Shadow callback for GET operations
    def customShadowCallback_Get(self, payload, responseStatus, token):
        self.callbackresponses.update({token: {"payload": json.loads(payload), "responseStatus": responseStatus}})
        return

    def getResponse(self, token):
        return self.callbackresponses[token]

    # post all parameters as a shadow update
    def paramPost(self):
        newPayload = {"state": {"reported": {"settings": settings}, "desired": None}}
        self.deviceShadowInstance.shadowUpdate(json.dumps(newPayload), None, 5)

    # post status update message to device shadow and, if enabled, syslog
    def statusPost(self, status, state=None):

        # create new JSON payload to update device shadow
        newPayload = {"state": {"reported": {"command": str(status), "sequencerun": None, "sequence": None},
                                "desired": None}}
        if state:
            newPayload.update({"state": {"reported": state}})

        # update shadow
        self.deviceShadowInstance.shadowUpdate(json.dumps(newPayload), None, 20)

        # log to syslog
        LOGGER.info(status)

        return

    # post state update to device shadow and, if enabled, syslog
    def statePost(self, state):

        # create new JSON payload to update device shadow
        newPayload = {"state": {"reported": {"command": state}, "desired": None}}
        self.deviceShadowInstance.shadowUpdate(json.dumps(newPayload), None, 20)

        # log to syslog
        LOGGER.info("New state" + json.dumps(state))

        return

    def tempPost(self, temp):

        # create new JSON payload to send device temperature to shadow
        newPayload = {"state": {"reported": {"cputemp": temp}}}
        self.deviceShadowInstance.shadowUpdate(json.dumps(newPayload), None, 20)

        # log to syslog on debug only
        LOGGER.debug("New temp payload " + json.dumps(newPayload))

        return


def connect():
    """Initiate connection to AWSIoT."""
    # Init Shadow Client MQTT connection
    myAWSIoTMQTTShadowClient = AWSIoTMQTTShadowClient(AWSIOT_THINGNAME)
    myAWSIoTMQTTShadowClient.configureEndpoint(AWSIOT_HOST, 8883)
    myAWSIoTMQTTShadowClient.configureCredentials(AWSIOT_ROOT_CA_PATH, AWSIOT_PRIVATE_KEY_PATH, AWSIOT_CERTIFICATE_PATH)

    # AWSIoTMQTTShadowClient configuration
    myAWSIoTMQTTShadowClient.configureAutoReconnectBackoffTime(1, 32, 20)
    myAWSIoTMQTTShadowClient.configureConnectDisconnectTimeout(20)  # 20 sec
    myAWSIoTMQTTShadowClient.configureMQTTOperationTimeout(20)  # 20 sec

    # force shadow client to use offline publish queueing
    # overriding the default behaviour for shadow clients in the SDK
    MQTTClient = myAWSIoTMQTTShadowClient.getMQTTConnection()
    MQTTClient.configureOfflinePublishQueueing(-1)

    # Connect to AWS IoT with a 300 second keepalive
    myAWSIoTMQTTShadowClient.connect(300)

    # Create a deviceShadow with persistent subscription
    Bot = myAWSIoTMQTTShadowClient.createShadowHandlerWithName(AWSIOT_THINGNAME, True)

    # create new instance of shadowCallbackContainer class
    shadowCallbackContainer_Bot = ShadowCallbackContainer(Bot)

    # initial status post
    shadowCallbackContainer_Bot.statusPost('STARTING')


# Define functions which animate LEDs in various ways.
def colorWipe(strip, color, wait_ms=50):
    """Wipe color across display a pixel at a time."""
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
        strip.show()
        time.sleep(wait_ms / 1000.0)


def theaterChase(strip, color, wait_ms=50, iterations=10):
    """Movie theater light style chaser animation."""
    for j in range(iterations):
        for q in range(3):
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i + q, color)
            strip.show()
            time.sleep(wait_ms / 1000.0)
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i + q, 0)


def wheel(pos):
    """Generate rainbow colors across 0-255 positions."""
    if pos < 85:
        return Color(pos * 3, 255 - pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return Color(255 - pos * 3, 0, pos * 3)
    else:
        pos -= 170
        return Color(0, pos * 3, 255 - pos * 3)


def rainbow(strip, wait_ms=20, iterations=1):
    """Draw rainbow that fades across all pixels at once."""
    for j in range(256 * iterations):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, wheel((i + j) & 255))
        strip.show()
        time.sleep(wait_ms / 1000.0)


def rainbowCycle(strip, wait_ms=20, iterations=5):
    """Draw rainbow that uniformly distributes itself across all pixels."""
    for j in range(256 * iterations):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, wheel(
                (int(i * 256 / strip.numPixels()) + j) & 255))
        strip.show()
        time.sleep(wait_ms / 1000.0)


def theaterChaseRainbow(strip, wait_ms=50):
    """Rainbow movie theater light style chaser animation."""
    for j in range(256):
        for q in range(3):
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i + q, wheel((i + j) % 255))
            strip.show()
            time.sleep(wait_ms / 1000.0)
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i + q, 0)


# Main program logic follows:
if __name__ == '__main__':

    # connect to AWSIoT
    connect()

    # Create NeoPixel object with appropriate configuration.
    strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
    # Intialize the library (must be called once before other functions).
    strip.begin()

    try:

        while True:
            print('Color wipe animations.')
            colorWipe(strip, Color(255, 0, 0))  # Red wipe
            colorWipe(strip, Color(0, 255, 0))  # Blue wipe
            colorWipe(strip, Color(0, 0, 255))  # Green wipe
            print('Theater chase animations.')
            theaterChase(strip, Color(127, 127, 127))  # White theater chase
            theaterChase(strip, Color(127, 0, 0))  # Red theater chase
            theaterChase(strip, Color(0, 0, 127))  # Blue theater chase
            print('Rainbow animations.')
            rainbow(strip)
            rainbowCycle(strip)
            theaterChaseRainbow(strip)

    except KeyboardInterrupt:
        colorWipe(strip, Color(0, 0, 0), 10)
