import argparse
import os
import traceback

import logger
from sync_clock import SyncClock
from toggler import Toggler


def main(time_source="Mote"):
    try:
        lock = os.open("lock_"+time_source, os.O_CREAT | os.O_EXCL)
    except OSError:
        print "--- Script already in execution! If you think this is an error delete the file 'lock' from this folder\n\n"
        raise


    # Options: "GPS", "NTP" or "Mote"
    pins = {
        "Mote": 21,
        "GPS": 16,
        "NTP": 12
    }

    print("Selected pin: {}".format(pins[time_source]))

    if time_source is None:
        time_source = "Mote"

    synchronization_rate = 10

    logger_queue = logger.start_listener(time_source + "_sync.log")
    # logger_queue = None

    clock = SyncClock(synchronization_rate, time_source, logger_queue=logger_queue)

    toggler = Toggler(clock, toggle_pin=pins[time_source], logger_queue=logger_queue)

    try:
        toggler.run()

    except KeyboardInterrupt:
        clock.stop()
        os.remove("lock_"+time_source)
        print 'Script ended normally!'
    except:
        traceback.print_exc()
        os.remove("lock_"+time_source)
        print 'Script ended with an error'



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source")
    try:
        args = parser.parse_args()
    except:
        print("Unknown arguments passed")
        raise Exception

    main(args.source)
