import curses
import json
import socket
import threading
import time
from curses import wrapper

import globals
from models import CentralServer
from utils import load_config


def init(stdscr: curses.window) -> None:
    globals.initialize()

    if curses.can_change_color():
        curses.init_color(0, 0, 0, 0)

    stdscr.keypad(True)
    curses.cbreak()
    curses.noecho()
    globals.stdscr_global = stdscr
    globals.stdscr_global.clear()
    globals.stdscr_global.addstr(
        0, 0, "[STARTED] Server started", curses.A_BOLD
    )

    globals.stdscr_global.addstr(
        1, 0, "[WAITING] Waiting for connections...", curses.A_BOLD
    )
    globals.stdscr_global.refresh()
    time.sleep(1)

    server_config = load_config()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(
        (server_config.get("server_ip"), server_config.get("server_port"))
    )
    central = CentralServer(server)
    central.run()

    k = 0
    while k != ord("q"):
        k = globals.stdscr_global.getch()
    if k == ord("q"):
        curses.endwin()
        exit()


if __name__ == "__main__":
    wrapper(init)
