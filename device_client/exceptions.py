#!/usr/bin/env python3
"""Defines exceptions for ws281x_aws_iot_alexa_remote
"""

# exceptions.py
#
# by Darren Dunford


class InterruptException(Exception):
    """Custom exception for interrupting a sequence

    """
    pass


# define custom exception for exiting
class ExitException(Exception):
    """Custom exception to terminate the program

    """
    pass
