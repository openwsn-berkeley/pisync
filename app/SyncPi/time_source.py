#!/usr/bin/python
from __future__ import division


# ============================ adjust path =====================================

import sys
import os

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

import RPi.GPIO as GPIO
from SmartMeshSDK.IpMoteConnector import IpMoteConnector


# ============================ classes =========================================


class TimeSource(object):
    __metaclass__ = ABCMeta
    KILL_PROCESS = "kill_process"

    def __init__(self, synchronization_rate):
        self.synchronization_rate = synchronization_rate

        self.results_queue = multiprocessing.Queue()
        self.commands_queue = multiprocessing.Queue()
        self.data_source_process = multiprocessing.Process(target=self._data_source_loop)
        self.data_source_process.daemon = True

    def __del__(self):
        self.stop()

    def start(self):
        self.data_source_process.start()

    def stop(self):
        self.commands_queue.put(self.KILL_PROCESS)

    def get_sync_data(self, timeout=0):
        try:
            return self.results_queue.get(timeout=timeout)
        except Queue.Empty:
            return None

    def _put_sync_data(self, rpi_time, elapsed_seconds):
        self.results_queue.put({'rpi': rpi_time, 'source': elapsed_seconds})

    @abstractmethod
    def _data_source_loop(self):
        pass


class MoteSource(TimeSource):
    def __init__(self, synchronization_rate):
        super(MoteSource, self).__init__(synchronization_rate)

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

    def _data_source_loop(self):
        rpi_time = time.time()
        response = self.moteconnector.send(['getParameter', 'time'], {})
        network_time = response['utcSecs'] + response['utcUsecs']/10.**6

        self._put_sync_data(rpi_time, network_time)


class NTPSource(TimeSource):
    def _data_source_loop(self):
        pass

    def get_sync_data(self, timeout=0):
        now = time.time()
        return {
            'rpi': now,
            'source': now
        }


class GPSSource(TimeSource):
    def __init__(self, synchronization_rate, interrupt_pin=20):
        super(GPSSource, self).__init__(synchronization_rate)
        self.last_timestamp = None
        self.interrupt_pin = interrupt_pin

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.interrupt_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def _data_source_loop(self):
        GPIO.add_event_detect(self.interrupt_pin, GPIO.FALLING, callback=self.pps_callback)

        try:
            ser = serial.Serial("/dev/serial0", 9600)

            while True:
                line = str(ser.readline())
                if "GPRMC" in line:
                    line = line.split(',')
                    hour = int(line[1][0:2])
                    minute = int(line[1][2:4])
                    second = int(line[1][4:6])

                    self.last_timestamp = hour*3600 + minute*60 + second

        except KeyboardInterrupt:
            print "Communicator subprocess ended normally"
        except:
            traceback.print_exc()
            print "Communicator subprocess ended with error"
            raise

    def pps_callback(self, _):
        rpi_time = time.time()

        if self.last_timestamp is not None and self.last_timestamp % self.synchronization_rate == 0:
            self._put_sync_data(rpi_time, self.last_timestamp)