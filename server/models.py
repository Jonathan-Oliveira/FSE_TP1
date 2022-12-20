import curses
import json
import socket
import threading
import time
from datetime import datetime
from multiprocessing import Queue

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
        number,
        connection,
        **kwargs,
    ):
        self.name = name
        self.number = number
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
        message = f"Room {self.number} - Addres {self.address}"
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

    def turn_all_lamp_off(self):
        for key, value in self.__dict__.items():
            if isinstance(value, Device) and value.tag.startswith("lamp"):
                value.turn_off()

    def turn_all_lamp_on(self):
        for key, value in self.__dict__.items():
            if isinstance(value, Device) and value.tag.startswith("lamp"):
                value.turn_on()

    def apply_action(self, command):
        data = {}
        if command == 1:
            data = (
                {"lamp1": "on"}
                if self.lamp1.get_value() == 0
                else {"lamp1": "of"}
            )
        elif command == 2:
            data = (
                {"lamp2": "on"}
                if self.lamp2.get_value() == 0
                else {"lamp2": "of"}
            )
        elif command == 3:
            data = (
                {"air_conditioner": "on"}
                if self.air_conditioner.get_value() == 0
                else {"air_conditioner": "of"}
            )
        elif command == 4:
            data = (
                {"multimedia_projector": "on"}
                if self.multimedia_projector.get_value() == 0
                else {"multimedia_projector": "of"}
            )
        elif command == 5:
            data = {"lamp1": "on", "lamp2": "on"}
        elif command == 6:
            data = {"lamp1": "of", "lamp2": "of"}
        elif command == 7:
            data = {
                "air_conditioner": "on",
                "multimedia_projector": "on",
                "lamp1": "on",
                "lamp2": "on",
            }
        elif command == 8:
            data = {
                "air_conditioner": "of",
                "multimedia_projector": "of",
                "lamp1": "of",
                "lamp2": "of",
            }
        elif command == 9:
            data = {"allarm_bell": "on"}
        elif command == 10:
            data = {"allarm_bell": "of"}
        elif command == 11:
            data = {"alarm_system": "on"}
        elif command == 12:
            data = {"alarm_system": "of"}

        response = self.send_command(data)

        if response.get("status") == "accepted":
            body = response.get("data")
            for key, value in body.items():
                if key == "alarm_system":
                    continue
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
        # thread.join()
        # thread2.join()

    def lister_client(self):
        try:
            self.connection.send(
                bytes(json.dumps(["Connected with the server"]), "utf-8")
            )
            while True:
                data = self.connection.recv(2048)
                if not data:
                    time.sleep(0.3)
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
            time.sleep(0.3)
            # print(f"Erro when listen the client {str(e)}")

    def apply_client_updates(self):
        while True:
            if not self.queueUpdates.empty():
                devices_values = self.queueUpdates.get()
                for key, value in devices_values.items():
                    self.__dict__[key].set_value(value)
                self.show_in_screen()
            time.sleep(0.3)
            # self.queueUpdates.task_done()

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
    def __init__(self, host, port):
        self.people_count = 0
        self.rooms_conneteds = 0
        self.system_alarms = 0
        self.host = host
        self.port = port
        self.pad_dashboard = None

    def add_room(self, room: Room):
        rooms_config = self.load_rooms_config()
        if hasattr(room, "address"):
            if rooms_config.get(room.address):
                room.name = rooms_config.get(room.address).get("name")
                room.number = rooms_config.get(room.address).get("number")
            else:
                room.number = len(rooms_config) + 1
                room.name = f"room_{room.number}"
        setattr(self, room.name, room)
        self.__dict__[room.name].run()
        self.log_rooms_config()
        self.show_dashboard()
        self.show_instructions()

    def load_rooms_config(self):
        with open("server/rooms_config.json", "r") as file:
            rooms_config = json.load(file)
        return rooms_config

    def log_rooms_config(self):
        rooms_config = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Room):
                rooms_config.update(
                    {
                        value.address: {
                            "name": value.name,
                            "number": value.number,
                        }
                    }
                )
        with open("server/rooms_config.json", "w") as file:
            file.write(json.dumps(rooms_config, indent=4))

    def turn_on_off_alarm_system(self):
        command_applyed = {}
        if self.system_alarms == 0:
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
                return False, triggers_dont_off
            self.system_alarms = 1
            command_applyed = {"alarm_system": "on"}
        else:
            self.system_alarms = 0
            command_applyed = {"alarm_system": "off"}

        for key, value in self.__dict__.items():
            if isinstance(value, Room):
                if value.connected:
                    value.apply_action(
                        command=12  # "turn_off_alarm_system"
                        if self.system_alarms == 0
                        else 11  # "turn_on_alarm_system"
                    )
        self.show_dashboard()
        return True, None, command_applyed

    def __repr__(self):
        return f"Central({self.__dict__})"

    def show_in_screen(self):
        for key, value in self.__dict__.items():
            if isinstance(value, Room):
                value.show_in_screen()

    def refresh(self):
        for key, value in self.__dict__.items():
            if isinstance(value, Room):
                value.refresh()

    def turn_all_lamp_off(self):
        for key, value in self.__dict__.items():
            if isinstance(value, Room):
                value.turn_all_lamp_off()

    def turn_all_lamp_on(self):
        for key, value in self.__dict__.items():
            if isinstance(value, Room):
                value.turn_all_lamp_on()

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

    def refresh_pads(self):
        self.pad_dashboard.refresh(0, 0, *self.pad_dashboard_position)
        self.pad_instructions.refresh(0, 0, *self.pad_instructions_position)
        self.pad_feedbacks_system.refresh(
            0, 0, *self.pad_feedbacks_system_position
        )
        # globals.stdscr_global.noutrefresh()
        # curses.doupdate()

    def update_rooms_info(self):
        self.rooms_conneteds = 0
        self.people_count = 0
        for key, value in self.__dict__.items():
            if isinstance(value, Room):
                if value.connected:
                    self.rooms_conneteds += 1
            if hasattr(value, "people_count"):
                self.people_count += value.__dict__.get(
                    "people_count"
                ).get_value()

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
        self.pad_dashboard.addstr(1, 1, "Dashboard", curses.A_BOLD)
        rows, cols = self.pad_dashboard.getmaxyx()
        self.pad_dashboard.addstr(2, 1, "-" * (cols - 2))
        self.update_rooms_info()
        self.pad_dashboard.addstr(
            3, 1, f"Rooms connected : {self.rooms_conneteds}"
        )
        self.pad_dashboard.addstr(
            4, 1, f"Number of people : {self.people_count}"
        )
        self.pad_dashboard.addstr(
            5, 1, f"Alarm system : {'ON' if self.system_alarms else 'OFF'}"
        )
        self.show_rooms()
        self.pad_dashboard.refresh(0, 0, *self.pad_dashboard_position)

    def show_rooms(self):
        # pass by to all attributes of the class room and call the method show_in_screen
        for key, value in self.__dict__.items():
            if isinstance(value, Room):
                value.show_in_screen()

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
        self.pad_instructions.addstr(8, 1, "6 - Turn off all lamps")
        self.pad_instructions.addstr(9, 1, "7 - Turn on all devices")
        self.pad_instructions.addstr(10, 1, "8 - Turn off all devices")

        if self.rooms_conneteds > 0:
            rooms = list(range(1, self.rooms_conneteds + 1))
            if len(rooms) > 1:
                number_of_roomns = "{} and {}".format(
                    ", ".join(str(x) for x in rooms[:-1]), rooms[-1]
                )
            else:
                number_of_roomns = rooms[0]
            note = f"Note 1: You can turn on/off the devices of the room {number_of_roomns}"
            self.pad_instructions.addstr(13, 1, note, curses.A_BOLD)
        else:
            note = "Note 1: There are no rooms connected"
            self.pad_instructions.addstr(
                13, 1, note, curses.A_BOLD | curses.A_BLINK
            )

        self.pad_instructions.addstr(
            14,
            1,
            "Note 2: All devices is [lamp1, lamp2, air conditioner, multimedia projector]",
            curses.A_BOLD,
        )
        self.pad_instructions.addstr(
            15,
            1,
            "Note 3: To apply a command to all rooms, write the number 0",
            curses.A_BOLD,
        )
        # collum 2
        self.pad_instructions.addstr(
            4, cols_mid + 1, "9 - Turn on/off systen alarm"
        )
        self.pad_instructions.addstr(
            5, cols_mid + 1, "10 - Turn on buzzer alarm"
        )
        self.pad_instructions.addstr(
            6, cols_mid + 1, "11 - Turn of buzzer alarm"
        )
        self.pad_instructions.addstr(
            8,
            cols_mid + 1,
            "Note 4: To turn on/off the system alarm, write 9",
            curses.A_BOLD,
        )
        self.pad_instructions.addstr(
            10, cols_mid + 1, "Examples: 1 1", curses.A_REVERSE
        )

        self.pad_instructions.refresh(0, 0, *self.pad_instructions_position)

    def show_text_box(self):
        while True:
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
            self.box = curses.textpad.Textbox(sub, insert_mode=True)
            self.box.edit(enter_is_terminate)
            command = self.box.gather()
            if self.valid_inputs(command):
                self.apply_command(command)
            # globals.stdscr_global.noutrefresh()
            # curses.doupdate()
            globals.stdscr_global.refresh()

            time.sleep(0.3)

    def apply_command(self, command):
        command = command.strip().split()

        if len(command) == 1:
            action = int(command[0])
            if action == 9:
                (
                    status,
                    message,
                    command_applyed,
                ) = self.turn_on_off_alarm_system()
                self.log_command(
                    {
                        "local": 0,
                        "action": command_applyed,
                    }
                )
                if status:
                    self.show_feedbacks_system(
                        ["Command applied successfully"]
                    )
                else:
                    message_devices = "{} and {}".format(
                        ", ".join(str(x) for x in message[:-1]), message[-1]
                    )
                    self.show_feedbacks_system(
                        [
                            "Command not applied,"
                            f"The devices {message_devices} are on",
                            " and the alarm system can't be turned on",
                        ]
                    )
        elif len(command) == 2:
            room = int(command[0])
            action = int(command[0])

            if room == 0:
                for num_room in range(1, self.rooms_conneteds + 1):
                    self.__dict__[f"room_{num_room}"].apply_action(action)
            else:
                accept, command_applyed, message = self.__dict__[
                    f"room_{room}"
                ].apply_action(int(action))
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
            if len(command) == 1 and int(command[0]) in [9, 10]:
                return True
            elif len(command) == 1:
                return False

            if len(command) == 2:
                room = command[0]
                action = command[1]
                if room.isdigit() and action.isdigit():
                    if self.rooms_conneteds == 0:
                        self.show_feedbacks_system(["No rooms connected"])
                        return False
                    if self.__dict__.get(f"room_{room}"):
                        if int(action) in range(1, 9):
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
        for num_room in range(1, self.rooms_conneteds + 1):
            self.__dict__[f"room_{num_room}"].apply_action(11)

    def turn_off_buzzer(self):
        for num_room in range(1, self.rooms_conneteds + 1):
            self.__dict__[f"room_{num_room}"].apply_action(12)

    def watch_alarm_trigger(self):
        trigger_sensors = [
            "presence_sensor",
            "window_sensor",
            "door_sensor",
        ]
        while True:
            if self.alarm_system:
                for num_room in range(1, self.rooms_conneteds + 1):
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
                for num_room in range(1, self.rooms_conneteds + 1):
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
            time.sleep(0.5)

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
        globals.stdscr_global.refresh()

    def run(self):
        globals.stdscr_global.clear()
        globals.stdscr_global.refresh()
        text_box_thread = threading.Thread(target=self.show_text_box)
        text_box_thread.start()
        watch_alarm_trigger_thread = threading.Thread(
            target=self.watch_alarm_trigger
        )
        watch_alarm_trigger_thread.start()
        self.show_dashboard()
        self.show_instructions()
        self.show_feedbacks_system()
        globals.stdscr_global.refresh()
        # globals.stdscr_global.noutrefresh()
        # curses.doupdate()
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
