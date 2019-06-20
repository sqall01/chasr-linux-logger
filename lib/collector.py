#!/usr/bin/python3

# written by sqall
# twitter: https://twitter.com/sqall01
# blog: https://h4des.org/blog
# github: https://github.com/sqall01
# 
# Licensed under the GNU Affero General Public License, version 3.

import logging
import threading
import os
import time
import json
import ctypes
import datetime
import calendar
from gps3 import gps3


class DataCollector(threading.Thread):

    def __init__(self, global_data):

        threading.Thread.__init__(self)

        # Used for logging.
        self.file_name = os.path.basename(__file__)

        logging.debug("[%s]: Initializing collector thread."
                      % self.file_name)

        self.global_data = global_data

        # Data needed for collecting gps data.
        self.gpslogging_interval = self.global_data.gpslogging_interval
        self.max_failed_gps_pos = self.global_data.max_failed_gps_pos
        self.gps_collect_sleep_time = self.global_data.gps_collect_sleep_time

        # Gps data.
        self.gps_data = self.global_data.gps_data
        self.gps_lock = self.global_data.gps_lock

        # Tolerance for position change.
        self.lat_change = self.global_data.lat_change
        self.lon_change = self.global_data.lon_change
        self.alt_change = self.global_data.alt_change

        # Data needed for storing gps data in file.
        self.tempfile = self.global_data.tempfile
        self.sync_always = self.global_data.sync_always
        if self.sync_always:
            self.libc = ctypes.CDLL("libc.so.6")
        else:
            self.libc = None

        # Flag indicates if thread should exit.
        self.exit_flag = False

        # Last gps data.
        self.last_utc_time = 0
        self.last_lat = 0
        self.last_lon = 0
        self.last_alt = 0

    def run(self):

        logging.info("[%s]: Starting collector thread with %s sec interval."
                     % (self.file_name, self.gpslogging_interval))

        while True:

            # Should we exit thread?
            if self.exit_flag:
                logging.info("[%s]: Exiting collector thread."
                             % self.file_name)
                return

            logging.info("[%s]: Connect to gpsd."
                         % self.file_name)
            try:
                gps_socket = gps3.GPSDSocket()
                data_stream = gps3.DataStream()
                gps_socket.connect()
                gps_socket.watch()
            except:
                logging.exception("[%s]: Failed to establish connection "
                                  % self.file_name
                                  + "to gpsd.")
                time.sleep(1)
                continue

            failed_ctr = 0
            for new_data in gps_socket:

                # Should we exit thread?
                if self.exit_flag:
                    logging.info("[%s]: Exiting collector thread."
                                 % self.file_name)
                    return

                if failed_ctr > self.max_failed_gps_pos:
                    logging.error("[%s]: Failed %d times to collect gps data. "
                                  % (self.file_name, failed_ctr)
                                  + "Resetting connection to gpsd.")
                    gps_socket.close()
                    break

                # Check if we received data.
                if new_data:
                    try:
                        data_stream.unpack(new_data)
                    except:
                        logging.warning("[%s]: Unpacking gps data failed."
                                        % self.file_name)
                        continue

                    # Reset failed counter.
                    failed_ctr = 0

                    # Check if received data is valid.
                    is_valid = True
                    is_valid &= (type(data_stream.TPV["lat"]) == float)
                    is_valid &= (type(data_stream.TPV["lon"]) == float)
                    is_valid &= (type(data_stream.TPV["alt"]) == float)
                    is_valid &= (type(data_stream.TPV["speed"]) == float)
                    is_valid &= (type(data_stream.TPV["time"]) == str)
                    if is_valid:

                        # When time string has following form:
                        # 2018-02-01T20:01:18.500Z
                        # we have to remove the ".500Z"
                        time_str = data_stream.TPV["time"]
                        if time_str.find(".") != -1:
                            time_str = time_str[0:time_str.find(".")]

                        # Convert time string to utc timestamp.
                        dt_obj = datetime.datetime.strptime(
                                                        time_str,
                                                        "%Y-%m-%dT%H:%M:%S")
                        utc_time = calendar.timegm(dt_obj.timetuple())

                        # Check if the interval in which we would like
                        # to collect gps data is reached.
                        if ((utc_time - self.last_utc_time)
                           < self.gpslogging_interval):
                            continue

                        # Get difference of current gps data to the last data.
                        diff_lat = self.last_lat - data_stream.TPV["lat"]
                        diff_lon = self.last_lon - data_stream.TPV["lon"]
                        diff_alt = self.last_alt - data_stream.TPV["alt"]

                        # Check if we recognize the gps data as changed
                        # position.
                        no_change = True
                        no_change &= self.lat_change*(-1) <= diff_lat
                        no_change &= diff_lat <= self.lat_change
                        no_change &= self.lon_change*(-1) <= diff_lon
                        no_change &= diff_lon <= self.lon_change
                        no_change &= self.alt_change*(-1) <= diff_alt
                        no_change &= diff_alt <= self.alt_change
                        if no_change:
                            logging.debug("[%s]: Position has not changed."
                                          % self.file_name)
                            continue

                        # Allow only a precision of 14 characters for the
                        # gps data (usual precision is 12 characters).
                        lat = str(data_stream.TPV["lat"])[:14]
                        lon = str(data_stream.TPV["lon"])[:14]
                        alt = str(data_stream.TPV["alt"])[:14]
                        speed = str(data_stream.TPV["speed"])[:14]

                        logging.debug("[%s]: Lat: %s Lon: %s "
                                      % (self.file_name, lat, lon)
                                      + "Alt: %s Speed: %s Time: %s"
                                      % (alt, speed, time_str))

                        element = {"lat": lat,
                                   "lon": lon,
                                   "alt": alt,
                                   "speed": speed,
                                   "utctime": utc_time}

                        # Append new gps position to gps data.
                        logging.debug("[%s]: Acquire lock." % self.file_name)
                        self.gps_lock.acquire()
                        self.gps_data.append(element)

                        # Wirte data to storage.
                        try:
                            with open(self.tempfile, 'w') as fp:
                                fp.write(json.dumps(self.gps_data))

                            # Sync filesystem to force writing on storage
                            if self.sync_always:
                                self.libc.sync()
                        except:
                            logging.exception("[%s]: Can not write into "
                                              % self.file_name
                                              + "tempfile (%s)."
                                              % self.tempfile)

                        logging.debug("[%s]: Release lock." % self.file_name)
                        self.gps_lock.release()

                        # Set current gps data as last position we
                        # collected.
                        self.last_utc_time = utc_time
                        self.last_lat = data_stream.TPV["lat"]
                        self.last_lon = data_stream.TPV["lon"]
                        self.last_alt = data_stream.TPV["alt"]

                # We got no data from gpsd.
                else:
                    failed_ctr += 1

                # Sleep to give gpsd time to give us the next position.
                time.sleep(self.gps_collect_sleep_time)

    # Sets exit flag.
    def exit(self):
        logging.debug("[%s]: Telling collector thread to exit."
                      % self.file_name)
        self.exit_flag = True