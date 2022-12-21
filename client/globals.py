from multiprocessing import Queue
from threading import Semaphore
from utils import read_config

queueCommand = None
queueMessages = None
people_count = None
config = None
stop_threads = False


def initialize():
    global queueCommands
    global queueMessages
    global people_count
    global config
    global stop_threads
    queueCommands = Queue()
    queueMessages = Queue()
    people_count = Semaphore(2)
    config = read_config()
    stop_threads = False
