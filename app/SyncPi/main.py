from sync_clock import SyncClock
from sync_clock import SyncClock
from toggler import Toggler
import os
import RPi.GPIO as GPIO
import traceback


try:
    lock = os.open("lock", os.O_CREAT | os.O_EXCL)
except OSError:
    print "--- Script already in execution! If you think this is an error delete the file 'lock' from this folder\n\n"
    raise


# Options: "GPS", "NTP" or "Mote"
current_test = "GPS"
synchronization_rate = 10

clock = SyncClock(synchronization_rate, current_test)

toggler = Toggler(clock)

try:
    toggler.run()

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

