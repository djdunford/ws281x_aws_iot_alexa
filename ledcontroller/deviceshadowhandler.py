#!/usr/bin/env python3
"""Initiates connection to AWSIoT and provides helper functions
"""

# deviceshadowhandler.py
#
# by Darren Dunford

import json
import logging

from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTShadowClient

LOGGER = logging.getLogger(__name__)

#
#
# Define functions which implement AWSIoT integration

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
        self.shadow_handler.shadowUpdate(json.dumps(new_payload), None, 20)

        # log to syslog
        LOGGER.info(status)

    # constructor
    def __init__(self, thingname, host, root_ca_path, private_key_path, certificate_path):
        """Initiate AWS IoT connection

        :param thingname: AWSIoT thing name
        :param host: AWSIoT endpoint FQDN
        :param root_ca_path: local file path to Amazon root certificate
        :param private_key_path: local file path to device private key
        :param certificate_path: local file path to device certificate
        """

        # Init Shadow Client MQTT connection
        self.shadow_client = AWSIoTMQTTShadowClient(thingname)
        self.shadow_client.configureEndpoint(host, 8883)
        self.shadow_client.configureCredentials(root_ca_path, private_key_path, certificate_path)

        # AWSIoTMQTTShadowClient configuration
        self.shadow_client.configureAutoReconnectBackoffTime(1, 32, 20)
        self.shadow_client.configureConnectDisconnectTimeout(20)  # 20 sec
        self.shadow_client.configureMQTTOperationTimeout(20)  # 20 sec

        # force shadow client to use offline publish queueing
        # overriding the default behaviour for shadow clients in the SDK
        mqtt_client = self.shadow_client.getMQTTConnection()
        mqtt_client.configureOfflinePublishQueueing(-1)

        # Connect to AWS IoT with a 300 second keepalive
        self.shadow_client.connect(300)

        # Create a deviceShadow with persistent subscription
        self.shadow_handler = self.shadow_client.createShadowHandlerWithName(thingname, True)

        # initial status post
        self.status_post('STARTING')

        # dictionary to hold callback responses
        # TODO: add logic to clear out stale entries, otherwise will become a memory leak
        self._callbackresponses = {}

        # callbacks in this class update this public instance variable with trigger commands received
        self.trigger = 0

        self.settings = None

    # Custom shadow callback for delta -> remote triggering
    def customShadowCallback_Delta(self, payload, responseStatus, token):
        """

        :param payload: JSON string ready to be parsed using json.loads(...)
        :param responseStatus:
        :param token:
        """

        # DEBUG dump payload in to syslog
        LOGGER.debug(payload)

        # create JSON dictionary from payload
        payloadDict = json.loads(payload)
        newPayload = {"state": {"reported": {"status": "RUNNING"}, "desired": None}}

        # check for parameter update
        new_settings = payloadDict.get('state').get('settings')

        # remove unwanted keys (avoids external injection of unwanted keys)
        # TODO handle unwanted_keys correctly, move settings to a separate module
        # unwanted_keys = set(new_settings) - SETTINGS_KEYS
        unwanted_keys = None
        for unwanted_key in unwanted_keys:
            del payloadDict["state"]["settings"][unwanted_key]

        # update parameters
        self.settings.update(payloadDict.get('state').get('settings'))

        # report status back to AWSIoT
        newPayload.update({"state": {"reported": {"settings": self.settings}}})

        # output syslog message
        LOGGER.info("Settings updated: " + json.dumps(self.settings))

        # check for triggering
        newState = payloadDict.get('state').get('command')
        if newState == "TRIGGER":
            self.trigger = int(payloadDict.get('state').get('sequence', 0))
            newPayload.update({"state": {
                "reported": {"command": "TRIGGERED", "sequencerun": self.trigger, "sequence": None}}})

        LOGGER.info("Shadow update: " + json.dumps(newPayload))

        # update shadow instance status
        self.shadow_handler.shadowUpdate(json.dumps(newPayload), None, 5)

    # Custom Shadow callback for GET operations
    def customShadowCallback_Get(self, payload, responseStatus, token):
        """

        :param payload:
        :param responseStatus:
        :param token:
        :return:
        """
        self._callbackresponses.update({token: {"payload": json.loads(payload), "responseStatus": responseStatus}})

    def getResponse(self, token):
        return self._callbackresponses[token]

    # post all parameters as a shadow update
    def paramPost(self):
        newPayload = {"state": {"reported": {"settings": self.settings}, "desired": None}}
        self.shadow_handler.shadowUpdate(json.dumps(newPayload), None, 5)

    # post state update to device shadow and, if enabled, syslog
    def statePost(self, state):

        # create new JSON payload to update device shadow
        newPayload = {"state": {"reported": {"command": state}, "desired": None}}
        self.shadow_handler.shadowUpdate(json.dumps(newPayload), None, 20)

        # log to syslog
        LOGGER.info("New state" + json.dumps(state))

    def tempPost(self, temp):

        # create new JSON payload to send device temperature to shadow
        newPayload = {"state": {"reported": {"cputemp": temp}}}
        self.shadow_handler.shadowUpdate(json.dumps(newPayload), None, 20)

        # log to syslog on debug only
        LOGGER.debug("New temp payload " + json.dumps(newPayload))
