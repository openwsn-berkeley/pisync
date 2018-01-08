#!/usr/bin/python
from __future__ import division

import threading

from time_source import *


# ============================ imports =========================================

# ============================ classes =========================================


class SyncClock(object):
    DISABLE_SYNC = False

    # sleeping less than this amount of time is useless as the sleep-wakeup routine takes at least this amount of time
    MINIMUM_SLEEP_TIME = 5.8/10.**5
    EMA_ALPHA = 2 / (6+1)
    EMA_BETA = 0.2

    def __init__(self, synchronization_rate, time_source, max_sleep=0, logger_queue=None): # synchronization_rate is the rate at which the Raspberry Pi synchronizes with the external time source
        self.synchronization_rate = synchronization_rate
        self.ema_drift_coefficient = 1
        self.drift_coefficient = 1
        self.last_sync_data = None
        self.max_sleep = max_sleep
        self.logger_queue = logger_queue

        # self.log("TIME SOURCE: {}".format(time_source))
        print(" =========== TIME SOURCE: {} ===========".format(time_source))

        if time_source == "NTP":
            self.time_source = NTPSource(synchronization_rate, logger_queue)
        elif time_source == "Mote":
            self.time_source = MoteSource(synchronization_rate, logger_queue)
        elif time_source == "GPS":
            self.time_source = GPSSource(synchronization_rate, logger_queue)

        flags = {"kill": False,
                 "did_first_sync": False}
        self.get_sync_data_thread = threading.Thread(target=self._get_sync_data_loop, args=(flags,))
        self.get_sync_data_thread.flags = flags

    def __del__(self):
        self.stop()

    def _get_sync_data_loop(self, flags):
        print "Start comm_loop"

        last_sync_timestamp = time.time()

        try:
            while not flags['kill']:
                sync_data = self.time_source.get_sync_data(timeout=1)

                if sync_data is not None:
                    # self.log("Got sync data! {}".format(sync_data))

                    source_time = sync_data['source']
                    rpi_time = sync_data['rpi']

                    if self.last_sync_data is not None:
                        self._calculate_drift_coefficient(source_time=source_time, rpi_time=rpi_time)
                    self.last_sync_data = sync_data

                    # Print something if the interval between two synchronizations is more than 10% off
                    if (time.time() - last_sync_timestamp) > self.synchronization_rate*1.1 or \
                                            time.time() - last_sync_timestamp < self.synchronization_rate*0.9:
                        print("Sync out of time! Last sync was {} seconds ago. Sync_rate: {}".format(time.time()-last_sync_timestamp, self.synchronization_rate))
                        self.log("Sync out of time! Last sync was {} seconds ago".format(time.time() - last_sync_timestamp), logger.WARNING)
                    last_sync_timestamp = rpi_time

                    flags['did_first_sync'] = True

                    if self.DISABLE_SYNC:
                        flags['kill'] = True

                # time.sleep(0.1)

        except KeyboardInterrupt:
            self.log("Registered keyboard interrupt", logger.WARNING)
            print "Comm thread ended normally"
            raise
        except:
            traceback.print_exc()
            self.log("Unexpected error!\n" + traceback.format_exc(), logger.ERROR)
            print "Comm thread ended with error"
            raise

        print "---- get_sync_data_thread ended"

    def _calculate_drift_coefficient(self, source_time, rpi_time):
        # self.log("Going to calculate new drift coef"
        #          ". rpi_time: {}"
        #          ", last_sync_rpi: {}"
        #          ", diff_rpi: {}"
        #          ", source_time: {}"
        #          ", last_sync_source: {}"
        #          ", diff_source: {}".format(
        #             rpi_time,
        #             self.last_sync_data["rpi"],
        #             rpi_time - self.last_sync_data["rpi"],
        #             source_time,
        #             self.last_sync_data["source"],
        #             source_time - self.last_sync_data["source"]
        #         ), logger.DEBUG)
        try:
            instant_drift_coefficient = (rpi_time - self.last_sync_data["rpi"]) / (source_time - self.last_sync_data["source"])
            # print("New drift: {}".format((1-instant_drift_coefficient)*10**6))
            self.ema_drift_coefficient = self.ema_drift_coefficient * (1 - self.EMA_ALPHA) + instant_drift_coefficient * self.EMA_ALPHA
            self.drift_coefficient = self.ema_drift_coefficient * (1 - self.EMA_BETA) + instant_drift_coefficient * self.EMA_BETA

            # self.log("drift_coefficient: {}, ema_drift_coefficient: {}, instant_drift_coefficient: {}".format(
            #     self.drift_coefficient, self.ema_drift_coefficient, instant_drift_coefficient
            # ))

        except ZeroDivisionError:
            self.log("Zero division error!", logger.WARNING)
            pass

    def start(self):
        # self.log("Starting clock...")
        self.get_sync_data_thread.start()
        self.time_source.start()

        while not self.get_sync_data_thread.flags["did_first_sync"]:
            print("Waiting for first sync...")
            time.sleep(1)
            # self.log("Waiting for first sync")

        # self.log("Clock started and first sync done!")

    def stop(self):
        self.log("Clock closing!", logger.WARNING)
        self.logger_queue.put(None)
        self.get_sync_data_thread.flags['kill'] = True
        self.time_source.stop()
        print '-  closed everything'

    def time(self):
        network_time = (time.time() - self.last_sync_data['rpi']) / self.drift_coefficient + self.last_sync_data['source']
        # self.log("Network time queried: {:.6f}".format(network_time))
        return network_time

    def sleep(self, seconds):
        time.sleep(seconds)

    def sleep_until(self, time_to_wakeup):
        # This function receives a source timestamp as argument and halts code execution up to that timestamp.
        # This is done by sleeping a fraction of the required time, waking up, recalculating the required sleep time
        # and sleeping again up to the point where its too close to the final wakeup time

        sleep_factor = 0.9  # this factor doesn't really affect the performance as long as it's anything from 0.1 to 0.9
        next_sleep_duration = (time_to_wakeup - self.time())*sleep_factor

        while next_sleep_duration > self.MINIMUM_SLEEP_TIME: # this constant is the minimum time a sleep needs to execute, even with a 1 uS argument
            if next_sleep_duration > 1:
                print("Going to sleep {} s".format(next_sleep_duration))
            if self.max_sleep != 0 and next_sleep_duration > self.max_sleep:
                self.log("Sleep duration greater than max_sleep", logger.ERROR)
                raise Exception("Sleep duration is too long! {}s".format(next_sleep_duration))

            # self.log("Going to sleep {} seconds".format(next_sleep_duration))
            time.sleep(next_sleep_duration)
            # self.log("Woke up from sleep")
            next_sleep_duration = (time_to_wakeup - self.time())*sleep_factor

    def log(self, message, level=logger.DEBUG):
        name = "CLOCK"
        if self.logger_queue is None:
            print("{} - {} - {} - {}".format(time.asctime(), name, level, message))
        else:
            item = {
                "name": name,
                "level": level,
                "message": "[" + name + "] " + message
            }
            self.logger_queue.put(item)