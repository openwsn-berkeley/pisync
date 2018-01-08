import math
import time
import traceback

import RPi.GPIO as GPIO

import logger


class Toggler(object):
    def __init__(self, clock, toggle_pin=21, logger_queue=None):
        self.clock = clock
        self.toggle_period = 0.5
        self.toggle_pin = toggle_pin
        self.logger_queue = logger_queue

    def log(self, message, level=logger.DEBUG):
        name = "TOGGLER"
        if self.logger_queue is None:
            print("{} - {} - {} - {}".format(time.asctime(), name, level, message))
        else:
            item = {
                "name": name,
                "level": level,
                "message": "[" + name + "] " + message
            }
            self.logger_queue.put(item)

    def run(self):
        # self.log("Starting run()")
        self.clock.start()
        next_loop = math.ceil(self.clock.time())

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.toggle_pin, GPIO.OUT)
        pin_state = int(next_loop / self.toggle_period) % 2 == 0  # make sure both pins are in the same phase

        # self.log("Starting while True")
        try:
            while True:
                GPIO.output(self.toggle_pin, pin_state)
                pin_state = not pin_state

                next_loop += self.toggle_period
                # self.log("Pin toggles and going to sleep! Pin state: {}, next_loop: {}".format(not pin_state, next_loop))
                try:
                    self.clock.sleep_until(next_loop)
                    # self.log("Woke up from sleep")
                except Exception:
                    self.log("Error while sleeping!\n" + traceback.format_exc(), level=logger.ERROR)
                    # We don't raise anything here because we want the code to keep running.
                    # The error will be dealt with later during log inspection
                    next_loop = math.ceil(self.clock.time())
                    pin_state = int(next_loop/self.toggle_period) % 2 == 0
                    # self.log("Toggle loop reset. Next_loop: {}, next_pin_state: {}".format(next_loop, pin_state))

        except KeyboardInterrupt:
            self.log("Registered keyboard interrupt", logger.WARNING)
            print "Comm thread ended normally"
            raise
        except:
            traceback.print_exc()
            self.log("Unexpected error!\n" + traceback.format_exc(), logger.ERROR)
            print "Comm thread ended with error"
            raise

        GPIO.cleanup()