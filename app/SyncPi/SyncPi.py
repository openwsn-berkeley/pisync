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
import RPi.GPIO as GPIO
import math
import time

from SmartMeshSDK.IpMoteConnector       import IpMoteConnector
from SmartMeshSDK.ApiException          import APIError


# ============================ classes =========================================

class MoteClock(object):
    MINIMUM_SLEEP_TIME = 5.8/10.**(5) # sleeping less than this amount of time is useless as the sleep-wakeup routine takes at least this amount of time

    def __init__(self, sync_rate): # sync_rate is the rate at which the Raspberry Pi asks the mote the current network timestamp
        self.sync_rate = sync_rate
        self.offset = 0
        self.keep_thread_alive = False

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
                res = self.moteconnector.dn_join()
            elif res.state == 5:
                break
            time.sleep(1)

    def __del__(self):
        self.stop()

    def _loop(self):
        print "- Polling mote for timestamp every {}s".format(self.sync_rate)
        while self.keep_thread_alive:
            self._sync()

            # wait a bit before next sync
            time.sleep(self.sync_rate)

    def _sync(self):
        # get network timestamp
        res = self.moteconnector.send(['getParameter', 'time'], {})
        network_time = res['utcSecs'] + res['utcUsecs']/10.**6

        # set network timestamp offset in relation to RPi clock
        self.offset = network_time - time.time()

    def start(self):
        self.thread = threading.Thread(target=self._loop)
        self.thread.daemon = True

        # Waits for first sync to complete before continuing execution.
        self.keep_thread_alive = True
        self._sync()
        self.thread.start()

    def stop(self):
        self.moteconnector.disconnect()
        self.keep_thread_alive = False

        print '-  closed everything'

    def time(self):
        return time.time() + self.offset

    def sleep(self, seconds):
        time.sleep(seconds)

    def sleep_until(self, time_to_wakeup):
        # This function receives a network timestamp as argument and halts code execution up to that timestamp.
        # This is done by sleeping a fraction of the required time, waking up, recalculating the required sleep time and sleeping again
        # up to the point where its too close to the final wakeup time

        sleep_factor = 0.8 # this 0.8 factor doesn't really affect the performance as long as it's anything from 0.1 to 0.9
        next_sleep_duration = (time_to_wakeup - self.time())*sleep_factor

        while next_sleep_duration > self.MINIMUM_SLEEP_TIME: # this constant is the minimum time a sleep needs to execute, even with a 1 uS argument
            time.sleep(next_sleep_duration)
            next_sleep_duration = (time_to_wakeup - self.time())*sleep_factor




# ============================ main ============================================

if __name__ == "__main__":
    try:
        lock = os.open("lock", os.O_CREAT | os.O_EXCL)
    except OSError:
        print "--- Script already in execution! If you think this is an error delete the file 'lock' from this folder\n\n"
        raise

    clock = MoteClock(sync_rate=30)
    loop_period = 0.5

    try:
        clock.start()
        next_loop = math.ceil(clock.time()) + 0.25 # just a offset, doesn't change much

        pin = 21
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin, GPIO.OUT)
        pin_state = int(next_loop) % 2 == 0 # just a small trick to make sure both pins are in the same phase

        while True:
            # print "-  Pint {} at instant {:.6f}".format(['HIGH', 'LOW '][pin_state], clock.time())
            print "{}, {:.6f}".format(['HIGH', 'LOW '][pin_state], clock.time())
            GPIO.output(pin, pin_state)
            pin_state = not pin_state

            next_loop += loop_period
            clock.sleep_until(next_loop)

    except KeyboardInterrupt:
        clock.stop()
        GPIO.cleanup()
        os.remove("lock")
        print 'Script ended normally.'
    except:
        traceback.print_exc()
        GPIO.cleanup()
        os.remove("lock")
        print 'Script ended with an error'
