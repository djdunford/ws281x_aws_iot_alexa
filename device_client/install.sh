#!/usr/bin/env bash
#
# install.sh
#
# install the LedController service on Raspbian / Raspberry Pi OS
#
# by Darren Dunford
#

# script control variables
appdir="/opt/ledcontroller"

# install required modules
apt-get install -y python3-pip
pip3 install -r requirements.txt

# create directory structure for app
mkdir -p $appdir
chgrp -R pi $appdir

# copy webapp and wsgi files
cp ledcontroller.py $appdir
cp ledcontroller.ini $appdir

# install service file
cp ledcontroller.service /lib/systemd/system
chmod 644 /lib/systemd/system/ledcontroller.service

# restart xmastrain service
systemctl daemon-reload
systemctl restart ledcontroller
