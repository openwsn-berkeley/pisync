#!/usr/bin/python
from __future__ import division

# ============================ adjust path =====================================

import sys
import os
if __name__ == "__main__":
    here = sys.path[0]
    sys.path.insert(0, os.path.join(here, '..', '..', 'libs'))
    sys.path.insert(0, os.path.join(here, '..', '..', 'external_libs'))
    
# ============================ imports =========================================


import traceback
import threading
import multiprocessing
import Queue
import RPi.GPIO as GPIO
import math
import time
import csv
import serial
from time import strftime, localtime

from SmartMeshSDK.IpMoteConnector       import IpMoteConnector
from SmartMeshSDK.ApiException          import APIError


# ============================ classes =========================================

class Communicator(object):
    KILL_PROCESS = "kill_process"

    def __init__(self, sync_rate, interrupt_pin=20, mode="Serial"):
        self.sync_rate = sync_rate
        self.interrupt_pin = interrupt_pin
        self.tick_counter = 0
        self.results_queue = multiprocessing.Queue()
        self.mode = mode
        # Available modes: serial, poll and interrupt
        self.last_tick_time = time.time()
        self.last_received_timestamp = None

        print("Starting in mode " + mode)

        if mode == "Poll" or mode == "Serial":
            self.commands_queue = multiprocessing.Queue()
            self.process = multiprocessing.Process(target=self._loop)
            # self.process.daemon = True
        elif self.mode == "Interrupt":
            pass
        else:
            raise Exception

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.interrupt_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def __del__(self):
        self.stop()

    def start(self):
        if self.mode == "Poll" or self.mode == "Serial":
            self.process.start()

        if self.mode == "Interrupt":
            GPIO.add_event_detect(self.interrupt_pin, GPIO.FALLING, callback=self.gps_tick_callback)

    def stop(self):
        if self.mode == "Poll" or self.mode == "Serial":
            self.commands_queue.put(self.KILL_PROCESS)

    def gps_tick_callback(self, _):
        rpi_time = time.time()

        if self.mode == "Serial":
            if self.last_received_timestamp is not None and self.last_received_timestamp % self.sync_rate == 0:
                self._sync(rpi_time, self.last_received_timestamp)

        else:
            elapsed_between_ticks = time.time() - self.last_tick_time
            self.tick_counter += round(elapsed_between_ticks) # this is a protection in case the RPi misses one tick from the GPS
            self.last_tick_time = time.time()

            if round(elapsed_between_ticks) == 2:
                print("Shit! We missed 1 beat")
            elif round(elapsed_between_ticks) > 2:
                print("Shit! We missed {} beats".format(round(elapsed_between_ticks)-1))

            if self.tick_counter % self.sync_rate == 0:
                self._sync(rpi_time, self.tick_counter)

    def get(self, timeout=0):
        try:
            return self.results_queue.get(timeout=timeout)
        except Queue.Empty:
            return None

    def _loop(self):
        try:
            if self.mode == "Polling":
                print "- Polling pps pin every {}s".format(self.sync_rate)
                previous_state = False
                while True:
                    state = GPIO.input(self.interrupt_pin)
                    if state != previous_state and (state == 1):
                        self.gps_tick_callback(state)
                    previous_state = state
                    # Check it as fast as possible so that there isn't another source of delay/jitter introcuded

            if self.mode == "Serial":
                GPIO.add_event_detect(self.interrupt_pin, GPIO.FALLING, callback=self.gps_tick_callback)
                ser = serial.Serial("/dev/serial0", 9600)

                while True:
                    line = str(ser.readline())
                    if "GPRMC" in line:
                        line = line.split(',')
                        hour = int(line[1][0:2])
                        minute = int(line[1][2:4])
                        second = int(line[1][4:6])

                        self.last_received_timestamp = hour*3600 + minute*60 + second

        except KeyboardInterrupt:
            print "Communicator subprocess ended normally"
        except:
            traceback.print_exc()
            print "Communicator subprocess ended with error"

    # def _loop(self):
    #     self._init_mote()
    #     print "- Polling mote for timestamp every {}s".format(self.sync_rate)
    #
    #     try:
    #         while True:
    #             self._sync()
    #             time.sleep(self.sync_rate)
    #
    #     except KeyboardInterrupt:
    #         print "Communicator subprocess ended normally"
    #     except:
    #         traceback.print_exc()
    #         print "Communicator subprocess ended with error"
    #
    #     self.moteconnector.disconnect()

    # def _init_mote(self):
    #     print 'MoteClock from SyncPi'
    #     self.moteconnector = IpMoteConnector.IpMoteConnector()
    #
    #     # self.serialport = raw_input("Enter the serial API port of SmartMesh IP Mote (e.g. COM15): ")
    #     # On linux the port is probably this one below, so just comment the line above and uncomment the one below
    #     self.serialport = "/dev/serial/by-id/usb-Dust_Networks_Dust_Huron-if03-port0"
    #
    #     print "- connect to the mote's serial port: {}".format(self.serialport)
    #
    #     self.moteconnector.connect({'port': self.serialport})
    #
    #     while True:
    #         res = self.moteconnector.dn_getParameter_moteStatus()
    #         print "   current mote state: {0}".format(res.state)
    #
    #         if res.state == 1:
    #             res = self.moteconnector.dn_join()
    #         elif res.state == 5:
    #             break
    #         time.sleep(1)

    def _sync(self, rpi_time, elapsed_seconds):
        self.results_queue.put({'rpi': rpi_time, 'gps': elapsed_seconds})


class MoteClock(object):
    DISABLE_SYNC = False

    MINIMUM_SLEEP_TIME = 5.8/10.**(5) # sleeping less than this amount of time is useless as the sleep-wakeup routine takes at least this amount of time
    # TARGET_DRIFT_LOOKBACK = 60*5 # time in seconds to look back to calculate the drift coefficient
    # MINIMUM_DRIFT_LOOKBACK = 30 # time in seconds to look back to calculate the drift coefficient
    EMA_ALPHA = 0.3
    EMA_BETA = 0.25

    def __init__(self, sync_rate): # sync_rate is the rate at which the Raspberry Pi asks the mote the current network timestamp
        self.sync_rate = sync_rate
        self.ema_drift_coefficient = 1
        self.drift_coefficient = 1
        self.reference = None
        self.communicator = Communicator(sync_rate)

        flags = {"kill": False,
                 "did_first_sync": False}
        self.comm_receive_thread = threading.Thread(target=self._comm_loop, args=(flags,))
        self.comm_receive_thread.flags = flags

        self._init_drift_file()

    def __del__(self):
        self.stop()

    def _comm_loop(self, flags):
        print "Start comm_loop"

        try:
            while not flags['kill']:
                return_from_comm = self.communicator.get(timeout=0.1)

                if return_from_comm is not None:
                    gps_time = return_from_comm['gps']
                    rpi_time = return_from_comm['rpi']

                    if self.reference is not None:
                        self._calculate_drift_coefficient(gps_time=gps_time, rpi_time=rpi_time)
                    self.reference = return_from_comm

                    flags['did_first_sync'] = True

                    if self.DISABLE_SYNC:
                        flags['kill'] = True

                time.sleep(0.1)

        except KeyboardInterrupt:
            print "Comm thread ended normally"
        except:
            traceback.print_exc()
            print "Comm thread ended with error"

        print "---- comm_receive_thread ended"

    def _calculate_drift_coefficient(self, gps_time, rpi_time):
        if gps_time - self.reference["gps"] > 5:
            print("gps_time: {} gps_reference: {}".format(gps_time, self.reference["gps"]))

        instant_drift_coefficient = (rpi_time - self.reference["rpi"]) / (gps_time - self.reference["gps"])

        self.ema_drift_coefficient = self.ema_drift_coefficient * (1 - self.EMA_ALPHA) + instant_drift_coefficient * self.EMA_ALPHA
        self.drift_coefficient     = self.ema_drift_coefficient * (1 - self.EMA_BETA)  + instant_drift_coefficient * self.EMA_BETA
        # print "new_d_coef: {:.1f}, ema: {:.1f}, d_coef: {:.1f}".format((1-instant_drift_coefficient) * 10 ** 6, (1 - self.ema_drift_coefficient) * 10 ** 6, (1 - self.drift_coefficient) * 10 ** 6)

        self._write_drift_data(gps_time=gps_time, instant_drift_coefficient=instant_drift_coefficient, rpi_time=rpi_time)
        # print([gps_time, rpi_time, self.reference["gps"], self.reference["rpi"], instant_drift_coefficient, self.ema_drift_coefficient, self.drift_coefficient])

    def _write_drift_data(self, gps_time, rpi_time, instant_drift_coefficient):
        with open(self.filename, "a") as drift_file:
            writer = csv.writer(drift_file)
            writer.writerow([gps_time, rpi_time, self.reference['gps'], self.reference['rpi'], instant_drift_coefficient, self.ema_drift_coefficient, self.drift_coefficient])

    def _init_drift_file(self):
        self.filename = "data/drift_output_{}.csv".format(
                                   strftime('%Y-%m-%d %H:%M:%S', localtime(time.time())).replace(' ', '_'))
        with open(self.filename, "w") as drift_file:
            writer = csv.writer(drift_file)
            writer.writerow(["gps_time", "rpi_time", "gps_reference", "rpi_reference", "instant_drift_coefficient", "ema_drift_coefficient", "drift_coefficient"])

    def start(self):
        self.comm_receive_thread.start()
        self.communicator.start()

        while not self.comm_receive_thread.flags["did_first_sync"]:
            print("Waiting for first sync...")
            time.sleep(1)

    def stop(self):
        self.comm_receive_thread.flags['kill'] = True
        self.communicator.stop()
        print '-  closed everything'

    def time(self):
        return (time.time() - self.reference['rpi']) / self.drift_coefficient + self.reference['gps']

    def sleep(self, seconds):
        time.sleep(seconds)

    def sleep_until(self, time_to_wakeup):
        # This function receives a gps timestamp as argument and halts code execution up to that timestamp.
        # This is done by sleeping a fraction of the required time, waking up, recalculating the required sleep time and sleeping again
        # up to the point where its too close to the final wakeup time

        sleep_factor = 0.8 # this 0.8 factor doesn't really affect the performance as long as it's anything from 0.1 to 0.9
        next_sleep_duration = (time_to_wakeup - self.time())*sleep_factor

        while next_sleep_duration > self.MINIMUM_SLEEP_TIME: # this constant is the minimum time a sleep needs to execute, even with a 1 uS argument
            if next_sleep_duration > 1:
                print("sleeping {} s".format(next_sleep_duration))
            time.sleep(next_sleep_duration)
            next_sleep_duration = (time_to_wakeup - self.time())*sleep_factor



# ============================ main ============================================

if __name__ == "__main__":
    try:
        lock = os.open("lock", os.O_CREAT | os.O_EXCL)
    except OSError:
        print "--- Script already in execution! If you think this is an error delete the file 'lock' from this folder\n\n"
        raise

    time.sleep(5)

    clock = MoteClock(sync_rate=5)
    loop_period = 0.5

    try:
        clock.start()
        next_loop = math.ceil(clock.time())

        pin = 21
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin, GPIO.OUT)
        pin_state = int(next_loop/loop_period) % 2 == 0  # just a small trick to make sure both pins are in the same phase

        while True:
            GPIO.output(pin, pin_state)
            pin_state = not pin_state

            next_loop += loop_period
            clock.sleep_until(next_loop)

    except KeyboardInterrupt:
        clock.stop()
        GPIO.cleanup()
        os.remove("lock")
        print 'Script ended normally!'
    except:
        traceback.print_exc()
        GPIO.cleanup()
        os.remove("lock")
        print 'Script ended with an error'
