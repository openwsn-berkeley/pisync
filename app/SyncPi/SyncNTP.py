#!/usr/bin/python
from __future__ import division

# ============================ adjust path =====================================

import sys
import os

# ============================ imports =========================================


import traceback
import RPi.GPIO as GPIO
import math
import time

# ============================ classes =========================================

def sleep_until(time_to_wakeup):
    MINIMUM_SLEEP_TIME = 5.8/10.**(5) # sleeping less than this amount of time is useless as the sleep-wakeup routine takes at least this amount of time

    # This function receives a network timestamp as argument and halts code execution up to that timestamp.
    # This is done by sleeping a fraction of the required time, waking up, recalculating the required sleep time and sleeping again
    # up to the point where its too close to the final wakeup time

    sleep_factor = 0.8  # this 0.8 factor doesn't really affect the performance as long as it's anything from 0.1 to 0.9
    next_sleep_duration = (time_to_wakeup - time.time()) * sleep_factor

    while next_sleep_duration > MINIMUM_SLEEP_TIME:  # this constant is the minimum time a sleep needs to execute, even with a 1 uS argument
        if next_sleep_duration > 1:
            print("sleeping {} s".format(next_sleep_duration))
        time.sleep(next_sleep_duration)
        next_sleep_duration = (time_to_wakeup - time.time()) * sleep_factor


# ============================ main ============================================

if __name__ == "__main__":
    try:
        lock = os.open("lock", os.O_CREAT | os.O_EXCL)
    except OSError:
        print "--- Script already in execution! If you think this is an error delete the file 'lock' from this folder\n\n"
        raise

    time.sleep(5)

    loop_period = 0.5

    try:
        next_loop = math.ceil(time.time())

        pin = 21
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin, GPIO.OUT)
        pin_state = int(
            next_loop / loop_period) % 2 == 0  # just a small trick to make sure both pins are in the same phase

        counter = 0
        while True:
            counter += 1
            print "Flip! " + str(counter)
            GPIO.output(pin, pin_state)
            pin_state = not pin_state

            next_loop += loop_period
            sleep_until(next_loop)

    except KeyboardInterrupt:
        GPIO.cleanup()
        os.remove("lock")
        print 'Script ended normally!'
    except:
        traceback.print_exc()
        GPIO.cleanup()
        os.remove("lock")
        print 'Script ended with an error'
