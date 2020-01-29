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
from rpi_ws281x import PixelStrip, Color
import os
import configparser
import logging
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTShadowClient
from effects import colorWipe, theaterChase, rainbow, rainbowCycle, theaterChaseRainbow

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
class DeviceShadowHandler:

    # post status update message to device shadow and, if enabled, syslog
    def status_post(self, status, state=None):
        """Post status message and device state to AWSIoT and LOGGER"""

        # create new JSON payload to update device shadow
        new_payload = {"state": {"reported": {"command": str(status), "sequencerun": None, "sequence": None},
                                "desired": None}}
        if state:
            new_payload.update({"state": {"reported": state}})

        # update shadow
        self.shadowHandler.shadowUpdate(json.dumps(new_payload), None, 20)

        # log to syslog
        LOGGER.info(status)

        return


    # constructor
    def __init__(self):
        """Initiate connection to AWSIoT.
        :rtype: object
        """

        # Init Shadow Client MQTT connection
        self.shadowClient = AWSIoTMQTTShadowClient(AWSIOT_THINGNAME)
        self.shadowClient.configureEndpoint(AWSIOT_HOST, 8883)
        self.shadowClient.configureCredentials(AWSIOT_ROOT_CA_PATH, AWSIOT_PRIVATE_KEY_PATH, AWSIOT_CERTIFICATE_PATH)

        # AWSIoTMQTTShadowClient configuration
        self.shadowClient.configureAutoReconnectBackoffTime(1, 32, 20)
        self.shadowClient.configureConnectDisconnectTimeout(20)  # 20 sec
        self.shadowClient.configureMQTTOperationTimeout(20)  # 20 sec

        # force shadow client to use offline publish queueing
        # overriding the default behaviour for shadow clients in the SDK
        mqtt_client = self.shadowClient.getMQTTConnection()
        mqtt_client.configureOfflinePublishQueueing(-1)

        # Connect to AWS IoT with a 300 second keepalive
        self.shadowClient.connect(300)

        # Create a deviceShadow with persistent subscription
        self.shadowHandler = self.shadowClient.createShadowHandlerWithName(AWSIOT_THINGNAME, True)

        # initial status post
        self.status_post('STARTING')

        # dictionary to hold callback responses
        # TODO: add logic to clear out stale entries, otherwise will become a memory leak
        self.callbackresponses = {}


    # Custom shadow callback for delta -> remote triggering
    def customShadowCallback_Delta(self, payload, responseStatus, token):
        """

        :param payload:
        :param responseStatus:
        :param token:
        """

        # payload is a JSON string ready to be parsed using json.loads(...)

        # declare global variables updated by this procedure
        global trigger
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
        self.shadowHandler.shadowUpdate(json.dumps(newPayload), None, 5)


    # Custom Shadow callback for GET operations
    def customShadowCallback_Get(self, payload, responseStatus, token):
        """

        :param payload:
        :param responseStatus:
        :param token:
        :return:
        """
        self.callbackresponses.update({token: {"payload": json.loads(payload), "responseStatus": responseStatus}})
        return

    def getResponse(self, token):
        return self.callbackresponses[token]

    # post all parameters as a shadow update
    def paramPost(self):
        newPayload = {"state": {"reported": {"settings": settings}, "desired": None}}
        self.shadowHandler.shadowUpdate(json.dumps(newPayload), None, 5)

        return

    # post state update to device shadow and, if enabled, syslog
    def statePost(self, state):

        # create new JSON payload to update device shadow
        newPayload = {"state": {"reported": {"command": state}, "desired": None}}
        self.shadowHandler.shadowUpdate(json.dumps(newPayload), None, 20)

        # log to syslog
        LOGGER.info("New state" + json.dumps(state))

        return

    def tempPost(self, temp):

        # create new JSON payload to send device temperature to shadow
        newPayload = {"state": {"reported": {"cputemp": temp}}}
        self.shadowHandler.shadowUpdate(json.dumps(newPayload), None, 20)

        # log to syslog on debug only
        LOGGER.debug("New temp payload " + json.dumps(newPayload))

        return


# Main program logic follows:
if __name__ == '__main__':

    # connect to AWSIoT
    device = DeviceShadowHandler()

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
