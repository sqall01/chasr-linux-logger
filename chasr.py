#!/usr/bin/python3

# written by sqall
# twitter: https://twitter.com/sqall01
# blog: https://h4des.org/blog
# github: https://github.com/sqall01
# 
# Licensed under the GNU Affero General Public License, version 3.

import configparser
import logging
import os
import sys
import json
import time
import re
import signal
from lib import GlobalData
from lib import DataSubmitter
from lib import DataCollector

submitter = None
collector = None

# Function creates a path location for the given user input.
def make_path(input_location):
    # Do nothing if the given location is an absolute path.
    if input_location[0] == "/":
        return input_location
    # Replace ~ with the home directory.
    elif input_location[0] == "~":
        return os.environ["HOME"] + input_location[1:]
    # Assume we have a given relative path.
    return os.path.dirname(os.path.abspath(__file__)) + "/" + input_location

# Function parses the gps data and stores it.
def parse_gps(global_data, data):
    if not data:
        return
    gps_data = json.loads(data)

    file_name = os.path.basename(__file__)

    to_remove = list()
    for data in gps_data:
        if type(data["utctime"]) != int:
            logging.error("[%s] Stored position corrupt. Removing it."
                          % file_name)
            to_remove.append(data)
            continue
        skip = False
        for key in ["lat", "lon", "alt", "speed"]:
            if type(data[key]) != str:
                logging.error("[%s] Stored position corrupt. Removing it."
                              % file_name)
                to_remove.append(data)
                skip = True
                break
            if len(data[key]) > 14:
                logging.error("[%s] Stored position corrupt. Removing it."
                              % file_name)
                to_remove.append(data)
                skip = True
                break
            if not bool(re.match(r'^[0-9.]+$', data[key])):
                logging.error("[%s] Stored position corrupt. Removing it."
                              % file_name)
                to_remove.append(data)
                skip = True
                break
            if sum(c == "." for c in data[key]) > 1:
                logging.error("[%s] Stored position corrupt. Removing it."
                              % file_name)
                to_remove.append(data)
                skip = True
                break
        if skip:
            continue

    # Remove corrupt data.
    for data in to_remove:
        gps_data.remove(data)

    global_data.gps_lock.acquire()
    global_data.gps_data = gps_data
    global_data.gps_lock.release()

# Signal handler to gracefully shutdown the client.
def sigterm_handler(signum, frame):
    global collector, submitter
    if collector:
        collector.exit()

    if submitter:
        submitter.exit()

if __name__ == '__main__':

    # Parse logging settings from config file.
    config = None
    file_name = os.path.basename(__file__)
    global_data = GlobalData()
    global_data.tempfile = make_path(global_data.tempfile)
    try:
        config = configparser.RawConfigParser(allow_no_value=False)
        config.read([make_path("config/config.conf")])

        # Parse logging settings.
        logfile = make_path(config.get("general", "logfile"))
        
        if config.get("general", "loglevel").upper() == "DEBUG":
            loglevel = logging.DEBUG
        elif config.get("general", "loglevel").upper() == "INFO":
            loglevel = logging.INFO
        elif config.get("general", "loglevel").upper() == "WARNING":
            loglevel = logging.WARNING
        elif config.get("general", "loglevel").upper() == "ERROR":
            loglevel = logging.ERROR
        elif config.get("general", "loglevel").upper() == "CRITICAL":
            loglevel = logging.CRITICAL
        else:
            raise ValueError("No valid log level in config file.")

        # Initialize logging.
        logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', 
            datefmt='%m/%d/%Y %H:%M:%S', filename=logfile, level=loglevel)

    except Exception as e:
        print("Could not parse configuration file.")
        print(e)
        sys.exit(1)

    # Parse settings from config file.
    try:
        global_data.username = config.get("server", "username")
        global_data.password = config.get("server", "password")
        global_data.secret = config.get("server", "secret")
        global_data.device_name = config.get("gps", "name")
        global_data.submission_interval = config.getint("gps",
                                                        "submissioninterval")
        global_data.gpslogging_interval = config.getint("gps",
                                                        "gpslogginginterval")
        global_data.sync_always = config.getboolean("gps", "syncalways")
    except:
        logging.exception("[%s] Failed parsing config file" % file_name)

    # Check temp file exists.
    if not os.path.exists(global_data.tempfile):
        # Create new file if not exists.
        try:
            with open(global_data.tempfile, 'w') as fp:
                pass
        except:
            logging.exception("[%s]: Can not create tempfile (%s)"
                              % (file_name, global_data.tempfile))
            sys.exit(1)

    # Parse stored gps data.
    else:
        try:
            with open(global_data.tempfile, 'r') as fp:
                parse_gps(global_data, fp.read())
        except:
            logging.exception("[%s]: Can not parse tempfile (%s)"
                              % (file_name, global_data.tempfile))
            sys.exit(1)

    submitter = DataSubmitter(global_data)
    # set thread to daemon
    # => threads terminates when main thread terminates
    submitter.daemon = True
    submitter.start()
    
    collector = DataCollector(global_data)
    # set thread to daemon
    # => threads terminates when main thread terminates
    collector.daemon = True
    collector.start()

    # Register sigterm handler to gracefully shutdown the server.
    signal.signal(signal.SIGTERM, sigterm_handler)

    # We never come back from this call.
    submitter.join()
    collector.join()
    logging.info("[%s] Exiting." % file_name)