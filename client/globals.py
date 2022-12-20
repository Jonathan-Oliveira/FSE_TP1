from multiprocessing import Queue
from threading import Semaphore

queueCommand = None
queueMessages = None
people_count = None


def initialize() -> None:
    global queueCommands
    global queueMessages
    global people_count
    queueCommands = Queue()
    queueMessages = Queue()
    people_count = Semaphore(2)
