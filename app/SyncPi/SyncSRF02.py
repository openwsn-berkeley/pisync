from __future__ import division

# ============================ adjust path =====================================

import sys
import os

if __name__ == "__main__":
    here = sys.path[0]
    sys.path.insert(0, os.path.join(here, '..', '..', 'libs'))
    sys.path.insert(0, os.path.join(here, '..', '..', 'external_libs'))

# ============================ imports =========================================

from SyncPi import MoteClock
import traceback
import math
import smbus
import time
import os

# ============================ main ============================================


class SRF02(object):
    SOUND_SPEED  = 340.0
    INCHES       = 0
    CENTIMETERS  = 1
    MICROSECONDS = 2

    def __init__(self, address, mode=MICROSECONDS):
        self.i2c = smbus.SMBus(1)
        self.mode = mode
        self.last_used_mode = mode

        # The address in hex, look it up in i2cdetect -y 1 if you're unsure
        self.address = address

    def __str__(self):
        return str(hex(self.address))

    def _send_command(self, command):
        self.i2c.write_byte_data(self.address, 0, command)

    def send(self):
        self._send_command(92)

    def receive(self, mode=None):
        if mode is None:
            mode = self.mode
        self.last_used_mode = mode
        command = 86 + mode
        self._send_command(command)

    def send_and_receive(self, mode=None):
        if mode is None:
            mode = self.mode
        self.last_used_mode = mode
        command = 80 + mode
        self._send_command(command)

    def read_result_from_buffer(self):
        high = (self.i2c.read_word_data(self.address, 2)) & 0xFF
        low = self.i2c.read_word_data(self.address, 3)
        result = (high << 8) + low

        return result

    def print_result(self, result=None):
        if result is None:
            result = self.read_result_from_buffer()

        if self.last_used_mode == self.INCHES:
            print("result: {} inches".format(result))
        elif self.last_used_mode == self.CENTIMETERS:
            print("result: {} centimeters".format(result))
        else:
            print("result: {} us -> 1-way: {:.2f} cm, 2-way: {:.2f}".format(result, result*self.SOUND_SPEED/10**4, result*self.SOUND_SPEED/10**4/2))


    def change_address(self, new_address):
        self._send_command(0xA0)
        time.sleep(0.005)

        self._send_command(0xAA)
        time.sleep(0.005)

        self._send_command(0xA5)
        time.sleep(0.005)

        self._send_command(new_address<<1)
        self.address = new_address

    def wait_for_result(self):
        time.sleep(0.08)

    def calibrate(self):
        accumulated_time_us = 0
        accumulated_distance_cm = 0

        for i in range(10):
            self.send_and_receive(mode=self.MICROSECONDS)
            self.wait_for_result()
            accumulated_time_us += self.read_result_from_buffer()

            time.sleep(0.5)

            self.send_and_receive(mode=self.CENTIMETERS)
            self.wait_for_result()
            accumulated_distance_cm += self.read_result_from_buffer()

            time.sleep(0.5)

        self.SOUND_SPEED = 2 * 10**4 * accumulated_distance_cm / accumulated_time_us


if __name__ == "__main__":
    loop_period = 0.5

    srf = SRF02(0x70)
    clock = MoteClock(sync_rate=2.123)
    role = os.environ['SONAR_ROLE']
    print("---> SONAR_ROLE: {}".format(role))

    try:
        clock.start()
        next_loop = math.ceil(clock.time())

        while True:

            if role == "sender":
                srf.send()
                print "-  signal sent"

            elif role == "receiver":
                srf.receive()
                srf.wait_for_result()
                srf.print_result()

            next_loop += loop_period
            clock.sleep_until(next_loop)

    except KeyboardInterrupt:
        clock.stop()
        print 'Script ended normally.'

    except:
        traceback.print_exc()
        print 'Script ended with an error'
