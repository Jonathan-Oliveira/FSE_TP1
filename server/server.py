import curses
import json
import socket
import threading
import time
from curses import wrapper

import globals
from models import CentralServer, Room
from utils import load_config

stdscr_global: curses.window = None


class ListenConnections(threading.Thread):
    def __init__(self, server: socket.socket) -> None:
        threading.Thread.__init__(self)
        self.server = server

    def run(self):
        connection_count = 0
        # TODO: handle the pads for each connection
        while True:
            self.server.listen(1)
            clientsock, clientAddress = self.server.accept()
            data = clientsock.recv(2048)  # the client send a json
            msg = data.decode("utf-8")
            msg = json.loads(msg)
            if msg.get("type") == "register":
                room_name = msg.get("data").get("name")
                devices = msg.get("data").get("devices")
                room = Room(
                    room_name,
                    clientAddress,
                    connection_count + 1,
                    clientsock,
                    **devices,
                )
            globals.central_server.add_room(room)
            connection_count += 1
            time.sleep(1)


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
    central = CentralServer(
        server_config.get("server_ip"), server_config.get("server_port")
    )
    globals.central_server = central
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((globals.central_server.host, globals.central_server.port))

    listen_connections = ListenConnections(server)
    listen_connections.start()
    globals.central_server.run()

    k = 0
    while k != ord("q"):
        k = globals.stdscr_global.getch()
    if k == ord("q"):
        curses.endwin()
        exit()


if __name__ == "__main__":
    wrapper(init)
