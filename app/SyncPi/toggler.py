import math
import traceback
import RPi.GPIO as GPIO


class Toggler(object):
    def __init__(self, clock, toggle_pin=21):
        self.clock = clock
        self.toggle_period = 0.5
        self.toggle_pin = toggle_pin

    def run(self):
        self.clock.start()
        next_loop = math.ceil(self.clock.time())

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.toggle_pin, GPIO.OUT)
        pin_state = int(next_loop / self.toggle_period) % 2 == 0  # make sure both pins are in the same phase

        while True:
            GPIO.output(self.toggle_pin, pin_state)
            pin_state = not pin_state

            next_loop += self.toggle_period
            self.clock.sleep_until(next_loop)
