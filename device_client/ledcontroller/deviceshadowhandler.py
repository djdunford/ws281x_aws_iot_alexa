#!/usr/bin/env python3
"""Initiates connection to AWSIoT and provides helper functions

deviceshadowhandler.py

by Darren Dunford
"""

import json
import logging
import queue
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTShadowClient

LOGGER = logging.getLogger(__name__)


class DeviceShadowHandler:

    def status_post(self, status, state=None):
        """Post status message and device state to AWSIoT and LOGGER

        :param status: status string
        :param state: optional dictionary to add to shadow reported state
        :return:
        """

        # create new JSON payload to update device shadow
        new_payload = {"state": {"reported": {"status": str(status)}, "desired": None}}
        if state:
            new_payload.update({"state": {"reported": state}})

        # update shadow
        self.shadow_handler.shadowUpdate(json.dumps(new_payload), None, 20)

        # log to syslog
        LOGGER.info(status)
        LOGGER.debug(json.dumps(new_payload))

    # constructor
    def __init__(self, thingname: str, host: str, root_ca_path: str, private_key_path: str, certificate_path: str):
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

        # Create a deviceShadow with persistent subscription and register delta handler
        self.shadow_handler = self.shadow_client.createShadowHandlerWithName(thingname, True)
        self.shadow_handler.shadowRegisterDeltaCallback(self.custom_shadow_callback_delta)

        # initial status post
        self.status_post('STARTING')

        # dictionary to hold callback responses
        self._callbackresponses = {}

        # callbacks in this class post events on to this queue
        self.event_queue = queue.SimpleQueue()

        self.settings = {}

    # Custom shadow callback for delta -> remote triggering
    def custom_shadow_callback_delta(self, payload: str, response_status, token):
        """

        :param payload: JSON string ready to be parsed using json.loads(...)
        :param response_status: ignored
        :param token: ignored
        """

        # DEBUG dump payload in to syslog
        LOGGER.debug(payload)

        # create JSON dictionary from payload
        payload_dict = json.loads(payload)
        new_payload = {}

        # check for command, if received push event on to queue
        if payload_dict.get('state').get('command'):
            self.event_queue.put_nowait({"command":payload_dict.get('state').get('command')})
            new_payload.update({"state": {"desired": {"command": None}}})

        # check for settings, if received push event on to queue
        if payload_dict.get('state').get('settings'):
            self.event_queue.put_nowait({"settings":payload_dict.get('state').get('settings')})
            new_payload.update({"state": {"desired": {"settings": payload_dict.get('state').get('settings')}}})

        LOGGER.info("Shadow update: " + json.dumps(new_payload))

        # update shadow instance status
        self.shadow_handler.shadowUpdate(json.dumps(new_payload), None, 5)

    def custom_shadow_callback_get(self, payload, response_status, token):
        """Callback function records response from get shadow operation

        :param payload:
        :param response_status:
        :param token:
        :return:
        """
        self._callbackresponses.update({token: {"payload": json.loads(payload), "responseStatus": response_status}})

    def get_response(self, token):
        """Return prior get shadow operation response

        note each response is deleted when returned, i.e. can only be returned once

        :param token:
        :return:
        """
        return self._callbackresponses.pop(token)

    # post all parameters as a shadow update
    def post_param(self):
        new_payload = {"state": {"reported": {"settings": self.settings}, "desired": None}}
        self.shadow_handler.shadowUpdate(json.dumps(new_payload), None, 5)

    # post state update to device shadow and, if enabled, syslog
    def post_state(self, state):

        # create new JSON payload to update device shadow
        new_payload = {"state": {"reported": {"status": state}, "desired": None}}
        self.shadow_handler.shadowUpdate(json.dumps(new_payload), None, 20)

        # log to syslog
        LOGGER.info("New state" + json.dumps(state))

    def post_temperature(self, temp):

        # create new JSON payload to send device temperature to shadow
        new_payload = {"state": {"reported": {"cputemp": temp}}}
        self.shadow_handler.shadowUpdate(json.dumps(new_payload), None, 20)

        # log to syslog on debug only
        LOGGER.debug("New temp payload " + json.dumps(new_payload))
