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



# def worker_process(queue, configurer):
#     configurer(queue)
#     name = multiprocessing.current_process().name
#     print('Worker started: %s' % name)
#     for i in range(10):
#         time.sleep(random())
#         logger = logging.getLogger(choice(LOGGERS))
#         level = choice(LEVELS)
#         message = choice(MESSAGES)
#         log(message, level, logger)
#     print('Worker finished: %s' % name)
#
#
#
#
# def main():
#     queue = start_listener()
#     workers = []
#     for i in range(10):
#         worker = multiprocessing.Process(target=worker_process,
#                                          args=(queue, worker_configurer))
#         workers.append(worker)
#         worker.start()
#     for w in workers:
#         w.join()
#     queue.put_nowait(None)
#     # listener.join()
#
#
# if __name__ == '__main__':
#     main()