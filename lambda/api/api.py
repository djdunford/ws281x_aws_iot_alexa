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
    LOGGER.info("Executing command: OFF")

    # obtain thingname from query parameter
    try:
        thingname = event['queryStringParameters']['thingname']
    except:
        LOGGER.error("Error getting query string parameter")
        raise Exception("Error getting query string parameter") # TODO: check CORS headers on error responses

    # publish event to AWSIoT MQTT
    payload = {"state": {"desired": {"command": {"action": "OFF"}}}}
    response = IOTCLIENT.update_thing_shadow(thingName=thingname, payload=json.dumps(payload))

    # TODO interpret response from update_thing_shadow
    streaming_body = response["payload"]
    json_state = json.loads(streaming_body.read())
    headers = {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}
    response = {'statusCode': 200, 'body': json.dumps(json_state), 'headers': headers}
    LOGGER.debug("Sending response: " + json.dumps(response, indent=2))
    return response

