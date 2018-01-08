#!/usr/bin/python
from __future__ import division

import os
import sys

# ============================ adjust path =====================================

here = sys.path[0]
sys.path.insert(0, os.path.join(here, '..', '..', 'libs'))
sys.path.insert(0, os.path.join(here, '..', '..', 'external_libs'))


# ============================ imports =========================================

from abc import ABCMeta
from abc import abstractmethod

import multiprocessing
import Queue
import time
import serial
import traceback
import logger
import datetime

import RPi.GPIO as GPIO
from SmartMeshSDK.IpMoteConnector import IpMoteConnector


# ============================ classes =========================================


class TimeSource(object):
    __metaclass__ = ABCMeta
    KILL_PROCESS = "kill_process"

    def __init__(self, synchronization_rate, logger_queue=None):
        self.synchronization_rate = synchronization_rate

        self.results_queue = multiprocessing.Queue()
        self.commands_queue = multiprocessing.Queue()
        self.data_source_process = multiprocessing.Process(target=self._data_source_loop)
        self.data_source_process.daemon = True
        self.logger_queue = logger_queue

    def __del__(self):
        self.stop()

    def start(self):
        # self.log("Starting TimeSource object")
        self.data_source_process.start()

    def stop(self):
        self.log("Stopping TimeSource object", logger.WARNING)
        self.commands_queue.put(self.KILL_PROCESS)

    def get_sync_data(self, timeout=0):
        try:
            sync_data = self.results_queue.get(timeout=timeout)
            # self.log("Got from sync_data_queue: {}".format(sync_data))
            return sync_data
        except Queue.Empty:
            return None

    def _put_sync_data(self, rpi_time, elapsed_seconds):
        sync_data = {'rpi': rpi_time, 'source': elapsed_seconds}
        # self.log("Putting sync data on queue: {}".format(sync_data))
        self.results_queue.put(sync_data)

    @abstractmethod
    def _data_source_loop(self):
        pass

    def log(self, message, level=logger.DEBUG):
        name = "TIME_SOURCE"
        if self.logger_queue is None:
            print("{} - {} - {} - {}".format(time.asctime(), name, level, message))
        else:
            item = {
                "name": name,
                "level": level,
                "message": "[" + name + "] " + message
            }
            self.logger_queue.put(item)


class MoteSource(TimeSource):
    def __init__(self, synchronization_rate, logger_queue=None):
        super(MoteSource, self).__init__(synchronization_rate, logger_queue)

    def _init_mote(self):
        print 'MoteClock from SyncPi'
        self.moteconnector = IpMoteConnector.IpMoteConnector()

        # self.serialport = raw_input("Enter the serial API port of SmartMesh IP Mote (e.g. COM15): ")
        # On linux the port is probably this one below, so just comment the line above and uncomment the one below
        self.serialport = "/dev/serial/by-id/usb-Dust_Networks_Dust_Huron-if03-port0"

        print "- connect to the mote's serial port: {}".format(self.serialport)

        self.moteconnector.connect({'port': self.serialport})

        while True:
            res = self.moteconnector.dn_getParameter_moteStatus()
            print "   current mote state: {0}".format(res.state)

            if res.state == 1:
                self.moteconnector.dn_join()
            elif res.state == 5:
                break
            time.sleep(1)

        # self.log("Mote successfully connected")

    def _query_mote(self):
        # self.log("Querying mote...")

        rpi_time = time.time()
        response = self.moteconnector.send(['getParameter', 'time'], {})
        network_time = response['utcSecs'] + response['utcUsecs'] / 10. ** 6

        # self.log("Mote response: networktime: {}. rpi_time: {}".format(network_time, rpi_time))
        self._put_sync_data(rpi_time, network_time)

    def _data_source_loop(self):
        self._init_mote()
        print "- Polling mote for timestamp every {}s".format(self.synchronization_rate)

        try:
            while True:
                self._query_mote()
                # self.log("Sleeping {} s before next sync".format(self.synchronization_rate))
                time.sleep(self.synchronization_rate)

        except KeyboardInterrupt:
            self.log("Registered keyboard interrupt", logger.WARNING)
            print "Communicator subprocess ended normally"
            raise
        except:
            traceback.print_exc()
            self.log("Unexpected error!\n" + traceback.format_exc(), logger.ERROR)
            print "Communicator subprocess ended with error"
            raise

        self.moteconnector.disconnect()
        # self.log("Mote disconnected")


class NTPSource(TimeSource):
    def _data_source_loop(self):
        while True:
            time.sleep(self.synchronization_rate)
            now = time.time()
            self._put_sync_data(now, now)
            # self.log("_put_sync_data: {}".format(now))


class GPSSource(TimeSource):
    def __init__(self, synchronization_rate, logger_queue=None, pps_mirror_pin=26, pps_only=True):
        super(GPSSource, self).__init__(synchronization_rate, logger_queue=logger_queue)
        self.last_timestamp_received = None
        self.last_sync = 0
        self.interrupt_pin = 20
        self.last_pps = None
        self.pps_mirror_pin = pps_mirror_pin
        self.pps_only = pps_only

        GPIO.setmode(GPIO.BCM)

        GPIO.setup(self.interrupt_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        if isinstance(self.pps_mirror_pin, int):
            GPIO.setup(self.pps_mirror_pin, GPIO.OUT)

    def _data_source_loop(self):
        GPIO.add_event_detect(self.interrupt_pin, GPIO.FALLING, callback=self.pps_callback)

        try:
            ser = serial.Serial("/dev/serial0", 9600)

            while True:
                if self.pps_only:
                    time.sleep(0.1)  # Do nothing, but don't let the process die either.

                else:
                    line = str(ser.readline())
                    if "GPRMC" in line:
                        # self.log("Got GPRMC line from gps: {}".format(line.split("\n")[0]))

                        # TODO: string manipulation in python is super slow! Try to get the timestamp only with the pps

                        line = line.split(',')
                        day = int(line[9][0:2])
                        month = int(line[9][2:4])
                        year = 2000 + int(line[9][4:6])

                        hour = int(line[1][0:2])
                        minute = int(line[1][2:4])
                        second = int(line[1][4:6])

                        epoch = int(datetime.datetime(year, month, day, hour, minute, second).strftime("%s"))

                        self.last_timestamp_received = epoch
                        # self.log("GPS line converted to timestamp {}".format(self.last_timestamp_received))

        except KeyboardInterrupt:
            self.log("Registered keyboard interrupt", logger.WARNING)
            print "Communicator subprocess ended normally"
            raise
        except:
            traceback.print_exc()
            self.log("Unexpected error!\n" + traceback.format_exc(), logger.ERROR)
            print "Communicator subprocess ended with error"
            raise

    def pps_callback(self, _):
        if self.pps_mirror_pin is not None:
            GPIO.output(self.pps_mirror_pin, 1)

        rpi_time = time.time()
        # self.log("PPS calback. rpi_time: {}".format(rpi_time))

        if self.last_pps is not None and rpi_time - self.last_pps > 1.5:
            self.log("Shit, we missed a PPS! Tdiff: {}".format(rpi_time-self.last_pps), logger.WARNING)

        self.last_pps = rpi_time

        if self.last_timestamp_received is not None and\
                                self.last_sync is not None and\
                                self.last_timestamp_received - self.last_sync >= self.synchronization_rate:
            # self.log("Sync time! last_ts_received: {}, last_sync: {}, sync_rate: {}".format(
            #     self.last_timestamp_received, self.last_sync, self.synchronization_rate
            # ))
            self.last_sync = self.last_timestamp_received
            self._put_sync_data(rpi_time, self.last_timestamp_received)


        if self.pps_mirror_pin is not None:
            GPIO.output(self.pps_mirror_pin, 0)