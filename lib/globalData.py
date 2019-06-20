#!/usr/bin/python3

# written by sqall
# twitter: https://twitter.com/sqall01
# blog: https://h4des.org/blog
# github: https://github.com/sqall01
# 
# Licensed under the GNU Affero General Public License, version 3.

import threading


class GlobalData(object):

    def __init__(self):

        # Settings for ChasR server.
        self.username = None
        self.password = None
        self.server = "https://alertr.de/chasr/submit.php"

        # Secret for gps data encryption.
        self.secret = None

        # Device name
        self.device_name = None

        self.submission_interval = None
        self.gpslogging_interval = None
        self.sync_always = None

        self.gps_data = list()
        self.gps_lock = threading.Semaphore(1)

        # Max number of gps positions transfered simultaneously to the server.
        self.gps_chunk = 100

        # Tempfile for gps data.
        self.tempfile = "config/gps.json"

        # Number of failed gps collection attempts before resetting connection
        # to gpsd.
        self.max_failed_gps_pos = 20

        # Time to sleep after collecting a gps position.
        self.gps_collect_sleep_time = 0.5

        # Tolerance we have to exceed in order to have recognize it
        # as a new position.
        self.lat_change = 0.0002
        self.lon_change = 0.0002
        self.alt_change = 9.0