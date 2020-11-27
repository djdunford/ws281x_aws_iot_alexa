#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""api.py - ws281x api

API for controller for WS281x LED string
uses AWSIoT integration for remote control

Author: Darren Dunford (djdunford@gmail.com)
"""

import json
import boto3
import logging

# set up logger
ERROR_QUERY_STRING_PARAMETER = "Error getting query string parameter"
LOGGER = logging.getLogger("api")
LOGGER.setLevel(logging.DEBUG)

# set up IOT Client
IOT_CLIENT = boto3.client('iot-data', region_name='eu-west-1')  # TODO remove hardcode reference to region


# custom exceptions for error conditions
class MissingQueryStringParameterException(Exception):
    pass


class MissingPathParameterException(Exception):
    pass


def off(event, context):
    LOGGER.info("Executing command: OFF")
    LOGGER.debug("Received event: " + json.dumps(event, indent=2))

    # obtain thing_name from query parameter
    try:
        thing_name = event['queryStringParameters']['thing_name']
    except ValueError:
        LOGGER.error(ERROR_QUERY_STRING_PARAMETER)
        raise MissingQueryStringParameterException(ERROR_QUERY_STRING_PARAMETER)  # TODO: check CORS headers on error responses

    # publish event to AWSIoT MQTT
    payload = {"state": {"desired": {"command": {"action": "OFF"}}}}
    response = IOT_CLIENT.update_thing_shadow(thingName=thing_name, payload=json.dumps(payload))

    # TODO interpret response from update_thing_shadow
    streaming_body = response["payload"]
    json_state = json.loads(streaming_body.read())
    headers = {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}
    response = {'statusCode': 200, 'body': json.dumps(json_state), 'headers': headers}
    LOGGER.debug("Sending response: " + json.dumps(response, indent=2))
    return response


def effect(event, context):
    LOGGER.info("Executing command: EVENT")
    LOGGER.debug("Received event: " + json.dumps(event, indent=2))

    # obtain thing_name from query parameter
    try:
        thing_name = event['queryStringParameters']['thing_name']
    except ValueError:
        LOGGER.error(ERROR_QUERY_STRING_PARAMETER)
        raise MissingQueryStringParameterException(ERROR_QUERY_STRING_PARAMETER)  # TODO: check CORS headers on error responses

    # obtain effect number from path parameter
    try:
        effect_name = event['pathParameters']['effect']
    except ValueError:
        raise MissingPathParameterException("Invalid sequence parameter - must be a non-zero integer")

    LOGGER.debug(f"Received thing_name {thing_name} to show effect {effect_name}")

    # publish event to AWSIoT MQTT
    payload = {"state": {"desired": {"command": {"action": "EFFECT", "effect": effect_name}}}}
    response = IOT_CLIENT.update_thing_shadow(thingName=thing_name, payload=json.dumps(payload))

    # TODO interpret response from update_thing_shadow
    streaming_body = response["payload"]
    json_state = json.loads(streaming_body.read())
    headers = {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}
    response = {'statusCode': 200, 'body': json.dumps(json_state), 'headers': headers}
    LOGGER.debug("Sending response: " + json.dumps(response, indent=2))
    return response
