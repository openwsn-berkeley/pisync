import logging
import logging.handlers
import multiprocessing


DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL


def start_listener(filename=None):
    queue = multiprocessing.Queue(-1)
    listener = multiprocessing.Process(target=listener_process,
                                       args=(queue, listener_configurer, filename))
    listener.start()
    return queue


def listener_configurer(filename=None):
    if filename is None:
        filename = "sync.log"
    root = logging.getLogger()
    h = logging.FileHandler(filename, mode='w')
    f = logging.Formatter('%(asctime)s %(processName)-10s %(name)s %(levelname)-8s %(message)s')
    h.setFormatter(f)
    root.addHandler(h)
    root.setLevel(DEBUG)
    root.log(msg="=====================================", level=logging.ERROR)


def listener_process(queue, configurer, filename):
    configurer(filename)
    while True:
        try:
            record = queue.get()
            if record is None:  # We send this as a sentinel to tell the listener to quit.
                break
            logger = logging.getLogger()
            logger.log(level=record["level"],
                       msg=record["message"])
        except Exception:
            import sys, traceback
            print('Whoops! Problem:',)
            traceback.print_exc(file=sys.stderr)
