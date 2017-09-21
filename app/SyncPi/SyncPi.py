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


# ============================ main ============================================

class MoteClock(object):
    UDP_PORT_NUMBER = 60000
    MINIMUM_SLEEP_TIME = 5.8/10.**(5)

    def __init__(self, sync_rate):
        self.sync_rate = sync_rate
        self.offset = 0
        self.keep_thread_alive = False

        print 'MoteClock from SyncPi'

        self.moteconnector = IpMoteConnector.IpMoteConnector()
        # self.serialport = raw_input("Enter the serial API port of SmartMesh IP Mote (e.g. COM15): ")

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

        try:
            # open a socket
            res = self.moteconnector.dn_openSocket(0)
            self.socketId = res.socketId

            # bind socket to a UDP port
            self.moteconnector.dn_bindSocket(self.socketId, self.UDP_PORT_NUMBER)
        except APIError:
            print "APIError when opening and binding socket. Try resetting the mote"
            raise

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
        res = self.moteconnector.dn_closeSocket(self.socketId)
        self.moteconnector.disconnect()
        self.keep_thread_alive = False

        print '-  closed everything'

    def time(self):
        return time.time() + self.offset

    def sleep(self, seconds):
        time.sleep(seconds)

    def sleep_until(self, time_to_wakeup):
        while time_to_wakeup - self.time() > self.MINIMUM_SLEEP_TIME: # this constant is the minumum time a sleep needs to execute, even with a 1 uS argument
            time.sleep((time_to_wakeup-self.time())*0.8)


if __name__ == "__main__":
    clock = MoteClock(sync_rate=2.123)
    loop_period = 0.5

    try:
        clock.start()
        next_loop = math.ceil(clock.time())

        pin = 21
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin, GPIO.OUT)
        pin_state = int(clock.time()) % 2 == 0

        while True:
            print "-  Pint toggled at instant {:.6f}".format(clock.time())
            GPIO.output(pin, pin_state)
            pin_state = not pin_state

            next_loop += loop_period
            clock.sleep_until(next_loop)

    except KeyboardInterrupt:
        clock.stop()
        print 'Script ended normally.'

    except:
        traceback.print_exc()
        print 'Script ended with an error'
