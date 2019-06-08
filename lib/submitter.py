#!/usr/bin/python3

# written by sqall
# twitter: https://twitter.com/sqall01
# blog: https://h4des.org/blog
# github: https://github.com/sqall01
# 
# Licensed under the GNU Affero General Public License, version 3.

import requests
import logging
import threading
import os
import time
import binascii
import json
import ctypes
import hashlib
from Crypto.Cipher import AES

class ErrorCodes:
    NO_ERROR = 0
    DATABASE_ERROR = 1
    AUTH_ERROR = 2
    ILLEGAL_MSG_ERROR = 3
    SESSION_EXPIRED = 4

class DataSubmitter(threading.Thread):

    def __init__(self, global_data):

        threading.Thread.__init__(self)

        # Used for logging.
        self.file_name = os.path.basename(__file__)

        logging.debug("[%s]: Initializing submitter thread."
                      % self.file_name)

        self.global_data = global_data

        # Data needed for online submission.
        self.submission_interval = self.global_data.submission_interval
        self.username = self.global_data.username
        self.password = self.global_data.password
        self.server = self.global_data.server
        self.device_name = self.global_data.device_name

        # Gps data.
        self.gps_data = self.global_data.gps_data
        self.gps_lock = self.global_data.gps_lock
        self.gps_chunk = self.global_data.gps_chunk

        # Data needed for storing gps data in file.
        self.tempfile = self.global_data.tempfile
        self.sync_always = self.global_data.sync_always
        if self.sync_always:
            self.libc = ctypes.CDLL("libc.so.6")
        else:
            self.libc = None

        # Flag indicates if thread should exit.
        self.exit_flag = False

        # Create a encryption key from the secret.
        sha256 = hashlib.sha256()
        sha256.update(self.global_data.secret.encode("utf-8"))
        self.key = sha256.digest()

    # Encrypt gps data.
    def encrypt_data(self, iv, data):

        # Handle str and bytes.
        if type(data) == str:
            padded_data = data
        else:
            padded_data = data.decode("utf-8")

        # Pad data in PKCS#7.
        padding = 16 - (len(padded_data) % 16)
        for i in range(padding):
            padded_data += chr(padding)

        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return cipher.encrypt(padded_data)

    def run(self):

        logging.info("[%s]: Starting submitter thread with %s sec interval."
                     % (self.file_name, self.submission_interval))

        while True:
            # Wait submission_interval number of seconds.
            for i in range(self.submission_interval):
                time.sleep(1)

                # Should we exit thread?
                if self.exit_flag:
                    logging.info("[%s]: Exiting submitter thread."
                                 % self.file_name)
                    return

            # Check if we have any gps data to submit.
            if len(self.gps_data) == 0:
                continue

            # Submit gps data in chunks in order to prevent the connection
            # from blocking.
            iterations = int((len(self.gps_data) / self.gps_chunk) + 1)
            for _ in range(iterations):

                # Copy first X elements of global gps data.
                logging.debug("[%s]: Acquire lock." % self.file_name)
                self.gps_lock.acquire()
                local_gps_data = list(self.gps_data[:self.gps_chunk])
                logging.debug("[%s]: Release lock." % self.file_name)
                self.gps_lock.release()

                # Prepare data to be sent.
                send_gps_data = list()
                for data in local_gps_data:

                    # Get IV for encryption.
                    iv = os.urandom(16)

                    data_point = dict()
                    data_point["iv"] = binascii.hexlify(iv).decode("utf-8")
                    data_point["device_name"] = self.device_name
                    data_point["utctime"] = data["utctime"]

                    # Encrypt gps data.
                    enc_lat = self.encrypt_data(iv, data["lat"])
                    enc_lon = self.encrypt_data(iv, data["lon"])
                    enc_alt = self.encrypt_data(iv, data["alt"])
                    enc_speed = self.encrypt_data(iv, data["speed"])
                    data_point["lat"] = binascii.hexlify(enc_lat).decode(
                                                                       "utf-8")
                    data_point["lon"] = binascii.hexlify(enc_lon).decode(
                                                                       "utf-8")
                    data_point["alt"] = binascii.hexlify(enc_alt).decode(
                                                                       "utf-8")
                    data_point["speed"] = binascii.hexlify(enc_speed).decode(
                                                                       "utf-8")

                    # Sanity check.
                    skip = False
                    for key in ["iv", "lat", "lon", "alt", "speed"]:
                        if len(data_point[key]) != 32:
                            logging.error("[%s] Length error during "
                                          % self.file_name
                                          + "encryption. "
                                          + "Skipping gps position.")
                            skip = True
                            break
                    if skip:
                        continue

                    send_gps_data.append(data_point)

                # Prepare POST data.
                payload = {"user": self.username,
                           "password": self.password,
                           "gps_data": json.dumps(send_gps_data)}

                # Submit data.
                r = None
                try:
                    r = requests.post(self.server,
                                      verify=True,
                                      data=payload)
                except:
                    logging.exception("[%s] Failed to send POST request."
                                      % self.file_name)
                    break

                # Abort submission if we have a server error.
                if r.status_code != 200:
                    logging.error("[%s]: Unable to submit data. "
                                  % self.file_name
                                  + "Server status code: %d."
                                  % r.status_code)
                    break

                # Parse response.
                try:
                    request_result = r.json()
                except:
                    logging.exception("[%s] Failed to decode json response."
                                      % self.file_name)
                    logging.debug("[%s] Json response: %s"
                                  % (self.file_name, r.text))
                    break

                # When submission was successful, remove submitted data from
                # global gps data and write it to storage.
                if request_result["code"] == ErrorCodes.NO_ERROR:
                    logging.debug("[%s]: Acquire lock." % self.file_name)
                    self.gps_lock.acquire()

                    # Remove all gps positions we submitted.
                    for loc_data in local_gps_data:
                        for glob_data in self.gps_data:

                            has_time = (loc_data["utctime"]
                                       == glob_data["utctime"])
                            has_lat = (loc_data["lat"]
                                      == glob_data["lat"])
                            has_long = (loc_data["lon"]
                                       == glob_data["lon"])
                            has_alt = (loc_data["alt"]
                                      == glob_data["alt"])
                            has_speed = (loc_data["speed"]
                                      == glob_data["speed"])

                            if (has_time
                               and has_lat
                               and has_long
                               and has_alt
                               and has_speed):

                               self.gps_data.remove(glob_data)
                               break

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

                # Server has a database error.
                elif request_result["code"] == ErrorCodes.DATABASE_ERROR:
                    logging.error("[%s] Failed to submit gps data. "
                                  % self.file_name
                                  + "Server has a database error.")
                    break

                # Authentication error.
                elif request_result["code"] == ErrorCodes.AUTH_ERROR:
                    logging.error("[%s] Failed to submit gps data. "
                                  % self.file_name
                                  + "Authentication failed.")
                    break

                # Illegal message error.
                elif request_result["code"] == ErrorCodes.ILLEGAL_MSG_ERROR:
                    logging.error("[%s] Failed to submit gps data. "
                                  % self.file_name
                                  + "Message illegal.")
                    break

                # Session expired error.
                elif request_result["code"] == ErrorCodes.SESSION_EXPIRED:
                    logging.error("[%s] Failed to submit gps data. "
                                  % self.file_name
                                  + "Session expired.")
                    break

                # Unknown error.
                else:
                    logging.error("[%s] Failed to submit gps data. "
                                  % self.file_name
                                  + "Unknown error: %d."
                                  % request_result["code"])
                    break

    # Sets exit flag.
    def exit(self):
        logging.debug("[%s]: Telling submitter thread to exit."
                      % self.file_name)
        self.exit_flag = True