import curses
import json
import socket
import threading
import time
from datetime import datetime
from multiprocessing import Queue
from curses.textpad import Textbox
from utils import commands_user

import globals


class Device:
    def __init__(self, name, tag, kind):
        self.name = name
        self.tag = tag
        if kind == "dth22":
            self.value = {"temperature": 0, "humidity": 0}
        else:
            self.value = 0
        self.kind = kind

    def __repr__(self):
        return f"Device({self.name}, {self.tag}, {self.value}, {self.kind})"

    def turn_off(self):
        self.value = 0

    def turn_on(self):
        self.value = 1

    def get_value(self):
        return self.value

    def set_value(self, value):
        self.value = value

    def turn_on_off(self):
        if self.value:
            self.turn_off()
        else:
            self.turn_on()

    def show_in_screen(self) -> list[str]:
        if self.kind == "dth22":
            return [
                f"Temperatura : {self.value['temperature']} °C",
                f"Umidade : {self.value['humidity']} %",
            ]
        if self.tag == "people_count":
            value = self.value
        else:
            value = "on" if self.value else "off"
        return [f"{self.name} : {value}"]


class Room:
    def __init__(
        self,
        name,
        address,
        connection,
        **kwargs,
    ):
        self.name = name
        self.number = int(name.split("_")[1])
        self.address = f"{address[0]}:{address[1]}"
        self.pad = self.creat_new_pad()
        self.connected = True
        self.connection = connection
        self.queueUpdates = Queue()
        self.queueResponse = Queue()
        for key, value in kwargs.items():
            setattr(self, key, Device(**value))

    def __repr__(self):
        return f"Room({self.name}, {self.number}, {self.address})"

    def creat_new_pad(self):
        _, _, rows_mid, cols_mid = self.get_screen_size()
        return curses.newpad(rows_mid, cols_mid)

    def get_screen_size(self) -> tuple[int, int, int, int]:
        height, width = globals.stdscr_global.getmaxyx()  # type: ignore
        cols_mid = int(0.5 * width)
        rows_mid = int((1 / 3) * height)
        return (height, width, rows_mid, cols_mid)

    def get_pad_position(self) -> tuple[int, int, int, int]:
        height, width, rows_mid, cols_mid = self.get_screen_size()
        if self.number == 1:
            return (rows_mid, 0, height - 1, cols_mid)
        elif self.number == 2:
            return (rows_mid, cols_mid, height - 1, width - 1)
        elif self.number == 3:
            return (rows_mid * 2, 0, height - 1, cols_mid * 2)
        else:
            return (rows_mid * 2, cols_mid, height - 1, width - 1)

    def show_in_screen(self):
        self.pad.clear()
        rows, cols = self.pad.getmaxyx()
        number = self.name.split("_")[1]
        message = f"Room {number} - Address {self.address}"
        self.pad.addstr(1, int(cols / 2) - int(len(message) / 2), message)
        self.pad.addstr(2, 0, "-" * cols)
        # Get all devices messages
        messages = []
        for key, value in self.__dict__.items():
            if isinstance(value, Device):
                messages.extend(value.show_in_screen())

        row_message = 3
        cols_message = 2
        biggest_message = max(messages, key=len)

        for message in messages:
            if (
                row_message >= rows - 1
                and cols_message + len(biggest_message) >= cols
            ):
                break
            elif (
                row_message >= rows - 1
                and cols_message + len(biggest_message) < cols
            ):
                cols_message += len(biggest_message) + 1
                row_message = 3
            self.pad.addstr(row_message, cols_message, message)
            row_message += 1
        self.pad.border("|", "|", "-", "-", "+", "+", "+", "+")
        self.refresh()

    def refresh(self):
        self.pad.refresh(0, 0, *self.get_pad_position())
        globals.stdscr_global.noutrefresh()
        curses.doupdate()

    def apply_action(self, action=None):
        if type(action) == dict:
            data = action
        else:
            data = {
                action: "on"
                if self.__dict__[action].get_value() == 0
                else "of"
            }
        response = self.send_command(data)

        if response.get("status") == "accepted":
            body = response.get("data")
            for key, value in body.items():
                self.__dict__[key].set_value(value)
            self.show_in_screen()
            return True, data, response.get("message")
        else:
            return False, data, response.get("message")

    def run(self):
        thread = threading.Thread(target=self.lister_client)
        thread.start()
        thread2 = threading.Thread(target=self.apply_client_updates)
        thread2.start()

    def lister_client(self):
        try:
            self.connection.send(
                bytes(json.dumps(["Connected with the server"]), "utf-8")
            )
            while True:
                if globals.stop_threads:
                    break
                data = self.connection.recv(2048)
                if not data:
                    time.sleep(0.4)
                data = json.loads(data.decode("utf-8"))
                if data.get("type") == "push":
                    self.queueUpdates.put(data.get("data"))
                elif data.get("type") == "response":
                    self.queueResponse.put(data)
        except socket.error:
            pass
            # self.connected = False
            # self.connection.close()
        except Exception:
            time.sleep(0.4)
            # print(f"Erro when listen the client {str(e)}")

    def apply_client_updates(self):
        while True:
            if globals.stop_threads:
                break
            if not self.queueUpdates.empty():
                devices_values = self.queueUpdates.get()
                for key, value in devices_values.items():
                    self.__dict__[key].set_value(value)
                self.show_in_screen()
            time.sleep(0.4)

    def send_command(self, data):
        if self.connected:
            body = {"type": "post", "data": data}
            self.connection.send(bytes(json.dumps(body), "utf-8"))
            try:
                response = self.queueResponse.get()
                return response
            except Exception as e:
                return {"status": "error", "message": str(e)}


class CentralServer:
    def __init__(self, server):
        self.people_count = 0
        self.rooms_conneteds = 0
        self.alarm_system = 0
        self.server = server
        self.buzzer = 0
        self.pad_dashboard = None

    def add_room(self, room: Room):
        setattr(self, room.name, room)
        self.__dict__[room.name].run()
        self.show_dashboard()
        self.show_instructions()

    def turn_on_off_alarm_system(self):
        command_applyed = {}
        if self.alarm_system == 0:
            triggers_dont_off = []
            trigger_sensors = [
                "presence_sensor",
                "window_sensor",
                "door_sensor",
            ]
            for sensor in trigger_sensors:
                for key, value in self.__dict__.items():
                    if isinstance(value, Room):
                        if value.__dict__[sensor].value == 1:
                            triggers_dont_off.append(sensor)

            if triggers_dont_off:
                return False, triggers_dont_off, {"alarm_system": "off"}
            self.alarm_system = 1
            command_applyed = {"alarm_system": "on"}
        else:
            self.alarm_system = 0
            command_applyed = {"alarm_system": "off"}

        for key, value in self.__dict__.items():
            if isinstance(value, Room):
                value.apply_action(action=command_applyed)
        self.show_dashboard()
        return True, None, command_applyed

    def __repr__(self):
        return f"Central({self.__dict__})"

    def refresh(self):
        for key, value in self.__dict__.items():
            if isinstance(value, Room):
                value.refresh()

    def create_screen_feedbacks_system(self):
        height, width, rows_mid, cols_mid = self.get_screen_size()
        self.pad_feedbacks_system = curses.newpad(int(rows_mid / 2), cols_mid)
        self.pad_feedbacks_system.clear()
        self.pad_feedbacks_system.border(
            "|", "|", "-", "-", "+", "+", "+", "+"
        )
        self.pad_feedbacks_system_position = (
            int(rows_mid / 2),
            int(cols_mid * 3),
            height - 1,
            width - 1,
        )

    def update_rooms_info(self):
        while True:
            if globals.stop_threads:
                break
            self.rooms_conneteds = 0
            self.people_count = 0
            for key, value in self.__dict__.items():
                if isinstance(value, Room):
                    self.rooms_conneteds += 1
                    if hasattr(value, "people_count"):
                        self.people_count += value.__dict__.get(
                            "people_count"
                        ).get_value()
            self.show_dashboard()
            time.sleep(0.4)

    def get_screen_size(self):
        height, width = globals.stdscr_global.getmaxyx()
        cols_mid = int(0.25 * width)
        rows_mid = int((1 / 3) * height)
        return (height, width, rows_mid, cols_mid)

    def show_dashboard(self):
        height, width, rows_mid, cols_mid = self.get_screen_size()
        # Create pad dashboard
        self.pad_dashboard = curses.newpad(rows_mid, cols_mid)
        self.pad_dashboard.clear()
        self.pad_dashboard_position = (0, 0, rows_mid, cols_mid)
        self.pad_dashboard.border("|", "|", "-", "-", "+", "+", "+", "+")
        self.pad_dashboard.addstr(1, 1, "System Dashboard", curses.A_BOLD)
        rows, cols = self.pad_dashboard.getmaxyx()
        self.pad_dashboard.addstr(2, 1, "-" * (cols - 2))
        self.pad_dashboard.addstr(
            3, 1, f"Rooms connected: {self.rooms_conneteds}"
        )
        self.pad_dashboard.addstr(
            4, 1, f"Number of people: {self.people_count}"
        )
        self.pad_dashboard.addstr(
            5, 1, f"Buzzer: {'ON' if self.buzzer else 'OFF'}"
        )
        self.pad_dashboard.addstr(
            6, 1, f"Alarm system: {'ON' if self.alarm_system else 'OFF'}"
        )
        self.show_rooms()
        self.pad_dashboard.refresh(0, 0, *self.pad_dashboard_position)
        globals.stdscr_global.noutrefresh()
        curses.doupdate()

    def show_rooms(self):
        for key, value in self.__dict__.items():
            if isinstance(value, Room):
                value.show_in_screen()

    def get_rooms_conneteds(self):
        return [
            key.split("_")[1]
            for key, value in self.__dict__.items()
            if isinstance(value, Room)
        ]

    def show_instructions(self):
        height, width, rows_mid, cols_mid = self.get_screen_size()
        self.pad_instructions = curses.newpad(rows_mid, cols_mid * 2)
        self.pad_instructions.clear()
        self.pad_instructions_position = (0, cols_mid, rows_mid * 2, width - 1)
        self.pad_instructions.border("|", "|", "-", "-", "+", "+", "+", "+")
        self.pad_instructions.addstr(
            1,
            1,
            "Instructions: Write the number of the room and the number of the device to turn on/off",
            curses.A_BOLD,
        )
        rows, cols = self.pad_instructions.getmaxyx()
        self.pad_instructions.addstr(2, 1, "-" * (cols - 2))
        self.pad_instructions.addstr(3, 1, "1 - Turn on/off lamp1")
        self.pad_instructions.addstr(4, 1, "2 - Turn on/off lamp2")
        self.pad_instructions.addstr(5, 1, "3 - Turn on/off  Air conditioner")
        self.pad_instructions.addstr(
            6, 1, "4 - Turn on/off  Multimedia Projector"
        )
        self.pad_instructions.addstr(7, 1, "5 - Turn on all lamps")

        self.pad_instructions.addstr(3, cols_mid + 1, "6 - Turn off all lamps")
        self.pad_instructions.addstr(
            4, cols_mid + 1, "7 - Turn on all devices"
        )
        self.pad_instructions.addstr(
            5, cols_mid + 1, "8 - Turn off all devices"
        )
        self.pad_instructions.addstr(
            6, cols_mid + 1, "9 - Turn on/off systen alarm"
        )
        self.pad_instructions.addstr(
            7, cols_mid + 1, "10 - Turn on/off buzzer alarm"
        )

        # Notes
        rooms = self.get_rooms_conneteds()
        if rooms:
            if len(rooms) > 1:
                number_of_roomns = "{} and {}".format(
                    ", ".join(str(x) for x in rooms[:-1]), rooms[-1]
                )
            else:
                number_of_roomns = rooms[0]
            note = f"Note 1: You can turn on/off the devices of the room {number_of_roomns}"
            self.pad_instructions.addstr(11, 1, note, curses.A_BOLD)
        else:
            note = "Note 1: There are no rooms connected"
            self.pad_instructions.addstr(
                11, 1, note, curses.A_BOLD | curses.A_BLINK
            )

        self.pad_instructions.addstr(
            12,
            1,
            "Note 2: All devices is [lamp1, lamp2, air conditioner, multimedia projector]",
            curses.A_BOLD,
        )
        self.pad_instructions.addstr(
            13,
            1,
            "Note 3: To apply a command to all rooms, write the number 0",
            curses.A_BOLD,
        )
        self.pad_instructions.addstr(
            14,
            1,
            "Note 4: To send a command to all devices, just write the number of action",
            curses.A_BOLD,
        )

        self.pad_instructions.addstr(
            9, cols_mid + 1, "Examples: 1 1", curses.A_REVERSE
        )

        self.pad_instructions.refresh(0, 0, *self.pad_instructions_position)
        globals.stdscr_global.noutrefresh()
        curses.doupdate()

    def show_text_box(self):
        while True:
            if globals.stop_threads:
                break
            height, width, rows_mid, cols_mid = self.get_screen_size()
            nlines = int(rows_mid / 2)
            ncols = cols_mid
            begin_y = 0
            begin_x = cols_mid * 3
            win = curses.newwin(nlines, ncols, begin_y, begin_x)
            win.clear()
            win.border("|", "|", "-", "-", "+", "+", "+", "+")
            win.addstr(1, 1, "Write a Command", curses.A_BOLD)
            win.addstr(2, 1, "-" * (ncols - 2))
            win.refresh()
            sub = win.derwin(1, ncols - 2, 3, 1)
            sub.clear()
            self.box = Textbox(sub, insert_mode=True)
            self.box.edit(enter_is_terminate)
            command = self.box.gather()
            if self.valid_inputs(command):
                self.apply_command(command)
            globals.stdscr_global.noutrefresh()
            curses.doupdate()
            time.sleep(0.4)

    def parse_user_input(self, user_input):
        user_input = user_input.strip().split()
        if len(user_input) == 2:
            room = int(user_input[0])
            device = int(user_input[1])
            return room, commands_user.get(device), device
        if len(user_input) == 1:
            device = int(user_input[0])
            return 0, commands_user.get(device), device

    def apply_command(self, command):
        room, action, id_command = self.parse_user_input(command)
        if room == 0:
            if id_command == 9:
                (
                    status,
                    message,
                    command_applyed,
                ) = self.turn_on_off_alarm_system()

                if status:
                    self.show_feedbacks_system(
                        ["Command applied successfully"]
                    )
                else:
                    if len(message) == 1:
                        message_devices = message[0]
                    else:
                        message_devices = "{} and {}".format(
                            ", ".join(str(x) for x in message[:-1]),
                            message[-1],
                        )
                    self.log_command(
                        {
                            "local": 0,
                            "action": command_applyed,
                        }
                    )
                    self.show_feedbacks_system(
                        [
                            "Command not applied,"
                            f"The devices {message_devices} ",
                            "are on and the alarm system",
                            " can't be turned on",
                        ]
                    )
            elif id_command == 10:
                if self.turn_on_off_buzzer():
                    self.show_feedbacks_system(
                        ["Command applied successfully"]
                    )
                else:
                    self.show_feedbacks_system(
                        [
                            "Command not applied",
                        ]
                    )
            else:
                for num_room in self.get_rooms_conneteds():
                    self.__dict__[f"room_{num_room}"].apply_action(
                        action=action
                    )
                self.log_command({"local": 0, "action": action})
        else:
            accept, command_applyed, message = self.__dict__[
                f"room_{room}"
            ].apply_action(action=action)
            messages = ["Valid command, applying..."]
            messages.append(message)
            self.show_feedbacks_system(messages)
            if accept:
                self.log_command(
                    {
                        "local": room,
                        "action": command_applyed,
                    }
                )

    def log_command(self, log_command):
        local = log_command.get("local")
        place = "Central" if local == 0 else f"Room {local}"
        actions = " ".join(
            [
                f"{key} {value}"
                for key, value in log_command.get("action").items()
            ]
        )
        log_message = f"{place}, {actions}, {datetime.now().time()}\n"
        with open("server/logs.csv", "a") as f:
            f.write(log_message)

    def valid_inputs(self, command):
        command = command.strip().split()
        try:
            if len(command) == 1 and int(command[0]) in range(1, 11):
                return True
            elif len(command) == 1:
                self.show_feedbacks_system(["Command not found"])
                return False

            if len(command) == 2:
                room = command[0]
                action = command[1]
                if room.isdigit() and action.isdigit():
                    if self.rooms_conneteds == 0:
                        self.show_feedbacks_system(["No rooms connected"])
                        return False
                    if self.__dict__.get(f"room_{room}"):
                        if int(action) in range(1, 10):
                            self.show_feedbacks_system(
                                ["Valid command, applying..."]
                            )
                            return True
                        else:
                            self.show_feedbacks_system(
                                ["Invalid action, try again"]
                            )
                    else:
                        self.show_feedbacks_system(
                            ["Invalid room number, try again"]
                        )

        except ValueError:
            self.show_feedbacks_system(
                ["Invalid command, try again", "Writer only numbers"]
            )
        else:
            self.show_feedbacks_system(["Invalid command, try again"])
        return False

    def turn_on_buzzer(self):
        if not self.buzzer:
            self.buzzer = 1
            for num_room in self.get_rooms_conneteds():
                self.__dict__[f"room_{num_room}"].apply_action(
                    action={"alarm_bell": "on"}
                )
        self.show_dashboard()
        return

    def turn_on_off_buzzer(self):
        action = {}
        if self.buzzer:
            action = {"alarm_bell": "off"}
            self.buzzer = 0
        else:
            self.buzzer = 1
            action = {"alarm_bell": "on"}
        for num_room in self.get_rooms_conneteds():
            self.__dict__[f"room_{num_room}"].apply_action(action)
        return True

    def watch_alarm_trigger(self):
        trigger_sensors = [
            "presence_sensor",
            "window_sensor",
            "door_sensor",
        ]
        while True:
            if globals.stop_threads:
                break
            if self.alarm_system:
                for num_room in self.get_rooms_conneteds():
                    for trigger_sensor in trigger_sensors:
                        if (
                            self.__dict__[f"room_{num_room}"]
                            .__dict__[trigger_sensor]
                            .get_value()
                            and self.alarm_system
                        ):
                            self.turn_on_buzzer()
                            self.log_command(
                                {
                                    "local": num_room,
                                    "action": {
                                        "buzzer": "on",
                                        trigger_sensor: "on",
                                    },
                                }
                            )
                            self.show_feedbacks_system(
                                [
                                    "Alarm triggered by",
                                    f"{trigger_sensor} in room {num_room}",
                                ]
                            )
            else:
                for num_room in self.get_rooms_conneteds():
                    if (
                        self.__dict__[f"room_{num_room}"]
                        .__dict__["smoke_sensor"]
                        .get_value()
                    ):
                        self.turn_on_buzzer()
                        self.log_command(
                            {
                                "local": num_room,
                                "action": {
                                    "buzzer": "on",
                                    "smoke_sensor": "on",
                                },
                            }
                        )
                        self.show_feedbacks_system(
                            [
                                "Alarm triggered by",
                                f"smoke_sensor in room {num_room}",
                            ]
                        )
            time.sleep(1)

    def show_feedbacks_system(self, messages=None) -> None:
        self.create_screen_feedbacks_system()
        self.pad_feedbacks_system.addstr(1, 1, "System messages")
        rows, cols = self.pad_feedbacks_system.getmaxyx()
        self.pad_feedbacks_system.addstr(2, 1, "-" * (cols - 2))
        # TODO: messages in the box scroll up when the number of messages is
        # greater than the number of rows
        if messages:
            for i, message in enumerate(messages):
                if i < rows - 3:
                    self.pad_feedbacks_system.addstr(i + 3, 1, message)
                else:
                    self.pad_feedbacks_system.addstr(3, 1, "...")

        self.pad_feedbacks_system.refresh(
            0, 0, *self.pad_feedbacks_system_position
        )
        globals.stdscr_global.noutrefresh()
        curses.doupdate()

    def listen_connections(self):
        while True:
            if globals.stop_threads:
                break
            self.server.listen(socket.INADDR_ANY)
            try:
                client_socket, client_address = self.server.accept()
                self.show_feedbacks_system(
                    [
                        "New room connected",
                        "Waiting for configuration...",
                    ]
                )
                time.sleep(1)
            except OSError:
                pass
                # break
            else:
                self.rooms_conneteds += 1

                while True:
                    data = client_socket.recv(2048)  # the client send a json
                    if data:
                        break
                configure_file = json.loads(data.decode("utf-8"))
                room_name = configure_file.get("data").get("name")
                devices = configure_file.get("data").get("devices")
                room = Room(
                    room_name,
                    client_address,
                    client_socket,
                    **devices,
                )
                self.add_room(room)
            if self.rooms_conneteds == 4:
                break
            time.sleep(3)

    def run(self):
        globals.stdscr_global.clear()
        globals.stdscr_global.refresh()
        listen_connections_thread = threading.Thread(
            target=self.listen_connections
        )
        text_box_thread = threading.Thread(target=self.show_text_box)
        dashboard_thread = threading.Thread(target=self.update_rooms_info)
        watch_alarm_trigger_thread = threading.Thread(
            target=self.watch_alarm_trigger
        )
        listen_connections_thread.start()
        text_box_thread.start()
        dashboard_thread.start()
        watch_alarm_trigger_thread.start()
        self.show_dashboard()
        self.show_instructions()
        self.show_feedbacks_system()
        globals.stdscr_global.refresh()
        text_box_thread.join()


def enter_is_terminate(x):
    # fucntion to suport the text box
    if x == 10:
        return 7
    return x


def load_commands():
    with open("commands.json", "r") as file:
        commands = json.load(file)

    return commands
