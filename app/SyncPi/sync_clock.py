#!/usr/bin/python
from __future__ import division

# ============================ imports =========================================

import traceback
import threading
import time

from time_source import *

# ============================ classes =========================================


class SyncClock(object):
    DISABLE_SYNC = False

    # sleeping less than this amount of time is useless as the sleep-wakeup routine takes at least this amount of time
    MINIMUM_SLEEP_TIME = 5.8/10.**5
    EMA_ALPHA = 2 / (6+1)
    EMA_BETA = 0.2

    def __init__(self, synchronization_rate, time_source): # synchronization_rate is the rate at which the Raspberry Pi synchronizes with the external time source
        self.synchronization_rate = synchronization_rate
        self.ema_drift_coefficient = 1
        self.drift_coefficient = 1
        self.last_sync_data = None
        self.time_source = time_source

        if time_source == "NTP":
            self.communicator = NTPSource(synchronization_rate)
        elif time_source == "Mote":
            self.communicator = MoteSource(synchronization_rate)
        elif time_source == "GPS":
            self.communicator = GPSSource(synchronization_rate)

        flags = {"kill": False,
                 "did_first_sync": False}
        self.get_sync_data_thread = threading.Thread(target=self._get_sync_data_loop, args=(flags,))
        self.get_sync_data_thread.flags = flags

    def __del__(self):
        self.stop()

    def _get_sync_data_loop(self, flags):
        print "Start comm_loop"

        try:
            while not flags['kill']:
                sync_data = self.communicator.get_sync_data(timeout=0.1)

                if sync_data is not None:
                    source_time = sync_data['source']
                    rpi_time = sync_data['rpi']

                    if self.last_sync_data is not None:
                        self._calculate_drift_coefficient(source_time=source_time, rpi_time=rpi_time)
                    self.last_sync_data = sync_data

                    flags['did_first_sync'] = True

                    if self.DISABLE_SYNC:
                        flags['kill'] = True

                # time.sleep(0.1)

        except KeyboardInterrupt:
            print "Comm thread ended normally"
        except:
            traceback.print_exc()
            print "Comm thread ended with error"

        print "---- get_sync_data_thread ended"

    def _calculate_drift_coefficient(self, source_time, rpi_time):
        try:
            instant_drift_coefficient = (rpi_time - self.last_sync_data["rpi"]) / (source_time - self.last_sync_data["source"])
            # print("New drift: {}".format((1-instant_drift_coefficient)*10**6))
            self.ema_drift_coefficient = self.ema_drift_coefficient * (1 - self.EMA_ALPHA) + instant_drift_coefficient * self.EMA_ALPHA
            self.drift_coefficient = self.ema_drift_coefficient * (1 - self.EMA_BETA) + instant_drift_coefficient * self.EMA_BETA

        except ZeroDivisionError:
            pass

    def start(self):
        self.get_sync_data_thread.start()
        self.communicator.start()

        while not self.get_sync_data_thread.flags["did_first_sync"]:
            print("Waiting for first sync...")
            time.sleep(1)

    def stop(self):
        self.get_sync_data_thread.flags['kill'] = True
        self.communicator.stop()
        print '-  closed everything'

    def time(self):
        return (time.time() - self.last_sync_data['rpi']) / self.drift_coefficient + self.last_sync_data['source']

    def sleep(self, seconds):
        time.sleep(seconds)

    def sleep_until(self, time_to_wakeup):
        # This function receives a source timestamp as argument and halts code execution up to that timestamp.
        # This is done by sleeping a fraction of the required time, waking up, recalculating the required sleep time
        # and sleeping again up to the point where its too close to the final wakeup time

        sleep_factor = 0.8  # this factor doesn't really affect the performance as long as it's anything from 0.1 to 0.9
        next_sleep_duration = (time_to_wakeup - self.time())*sleep_factor

        while next_sleep_duration > self.MINIMUM_SLEEP_TIME: # this constant is the minimum time a sleep needs to execute, even with a 1 uS argument
            if next_sleep_duration > 1:
                print("sleeping {} s".format(next_sleep_duration))
            time.sleep(next_sleep_duration)
            next_sleep_duration = (time_to_wakeup - self.time())*sleep_factor