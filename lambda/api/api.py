#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""api.py - ws281x api

API for controller for WS281x LED string
uses AWSIoT integration for remote control

Author: Darren Dunford (djdunford@gmail.com)
"""

# import dependencies
import json
import boto3
import logging

# set up logger
LOGGER = logging.getLogger("api")
LOGGER.setLevel(logging.DEBUG)

# set up IOT Client
IOTCLIENT = boto3.client('iot-data', region_name='eu-west-1')  # TODO remove hardcode reference to region


def off(event, context):
    LOGGER.debug("api.off invoked")
    LOGGER.debug("Received event: " + json.dumps(event, indent=2))
    LOGGER.info("Executing command: OFF")
    payload = {"state": {"desired": {"command": {"action": "OFF"}}}}
    # TODO remove hardcoded reference to thingName in next line
    response = IOTCLIENT.update_thing_shadow(thingName="DunfordXmasCastle", payload=json.dumps(payload))
    streaming_body = response["payload"]
    json_state = json.loads(streaming_body.read())
    LOGGER.info(json_state)
    headers = {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}
    response = {'statusCode': 200, 'body': json.dumps(json_state), 'headers': headers}
    LOGGER.debug("Sending response: " + json.dumps(response, indent=2))
    return response

