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
import smbus
import time
import os

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


class Sonar:
    def __init__(self, address):
        self.i2c = smbus.SMBus(1)
        # The address in hex, look it up in i2cdetect -y 1 if you're unsure
        self.address = address

    def __str__(self):
        return str(hex(self.address))

    def send_signal(self):
        self.i2c.write_byte_data(self.address, 0, 92)

    def receive_signal_us(self):
        self.i2c.write_byte_data(self.address, 0, 88)

    def send_and_receive_signal_us(self):
        self.i2c.write_byte_data(self.address, 0, 82)
        time.sleep(0.08)
        result = self.read_result_from_buffer()


    def read_result_from_buffer(self):
        high = (self.i2c.read_word_data(self.address, 2)) & 0xFF
        low = self.i2c.read_word_data(self.address, 3)
        result = (high<<8) + low
        print("result: {} us -> {:.2f} cm".format(result, (result/10.**4)*340.))

        return result

    def change_address(self, new_address):
        self.i2c.write_byte_data(self.address, 0, 0xA0)
        time.sleep(0.005)
        self.i2c.write_byte_data(self.address, 0, 0xAA)
        time.sleep(0.005)
        self.i2c.write_byte_data(self.address, 0, 0xA5)
        time.sleep(0.005)
        self.i2c.write_byte_data(self.address, 0, new_address<<1)
        self.address = new_address




if __name__ == "__main__":
    clock = MoteClock(sync_rate=2.123)

    if False:
        try:
            clock.start()

            pin = 21
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(pin, GPIO.OUT)
            pin_state = int(clock.time()) % 2 == 0

            sonar = Sonar(0x70)
            role = os.environ['SONAR_ROLE']
            print("---> SONAR_ROLE: {}".format(role))

            while True:
                print "-  Pint toggled at instant {:.6f}".format(clock.time())
                GPIO.output(pin, pin_state)
                pin_state = not pin_state
                clock.sleep_until(math.ceil(clock.time()))

                if role == "sender":
                    sonar.send_and_receive_signal_us()
                elif role == "receiver":
                    sonar.receive_signal_us()
                    time.sleep(0.08)
                    sonar.read_result_from_buffer()

        except KeyboardInterrupt:
            clock.stop()
            print 'Script ended normally.'

        except:
            traceback.print_exc()
            print 'Script ended with an error'


    def test_sleep_functions():
        iterations = 20
        sleep_time = 1

        clock.stop()

        time_accumulated = 0
        for i in range(iterations):
            initial_time = clock.time()
            time_accumulated -= time.time()
            time.sleep(0.2)
            clock.sleep_until(initial_time+sleep_time)
            time_accumulated += time.time()

        print("time avg: {} s, deviation: {} uS".format(time_accumulated/iterations, (time_accumulated/iterations-1)*10**6))


        time_accumulated = 0
        for i in range(iterations):
            initial_time = clock.time()
            time_accumulated -= time.time()
            time.sleep(0.2)
            time.sleep(initial_time + sleep_time - clock.time())
            time_accumulated += time.time()
            print "."

        print("time avg: {} s, deviation: {} uS".format(time_accumulated/iterations, (time_accumulated/iterations-1)*10**6))
