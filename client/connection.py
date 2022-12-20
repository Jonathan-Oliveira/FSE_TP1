import json
import threading
import time


class ReceiveMessage(threading.Thread):
    def __init__(self, client):
        threading.Thread.__init__(self)
        self.client = client

    def run(self):
        while True:
            in_data = self.client.recv(1024)
            if in_data:
                print("From Server :", in_data.decode("utf-8"))
                globals.queueCommands.put(json.loads(in_data.decode("utf-8")))
            time.sleep(0.20)


class ApplyCommand(threading.Thread):
    def __init__(self, interface):
        threading.Thread.__init__(self)
        self.interface = interface

    def run(self):
        while True:
            if not globals.queueCommands.empty():
                command = globals.queueCommands.get().get("data")
                try:
                    devices_updates = self.interface.apply_commands(command)
                except Exception as e:
                    globals.queueMessages.put(
                        {
                            "type": "response",
                            "data": {},
                            "message": str(e),
                            "status": "error",
                        }
                    )
                else:
                    globals.queueMessages.put(
                        {
                            "type": "response",
                            "data": devices_updates,
                            "message": "Command applied",
                            "status": "accepted",
                        }
                    )
            time.sleep(0.20)


class SeeInputs(threading.Thread):
    def __init__(self, device, interface):
        threading.Thread.__init__(self)
        self.device = device
        self.interface = interface

    def run(self):
        print(
            f"Starting thread for {self.interface.__dict__.get(self.device.tag).name }..."
        )

        while True:
            # Check if a person is detected
            if (
                self.interface.__dict__.get(self.device.tag).get_tag()
                == "people_counting_sensor_exit"
                or self.interface.__dict__.get(self.device.tag).get_tag()
                == "people_counting_sensor_entry"
            ):
                if (
                    self.interface.__dict__.get(self.device.tag).get_input()
                    == 1
                    and self.interface.__dict__.get(
                        self.device.tag
                    ).get_value()
                    == 0
                ):
                    # If a person is detected, send a message to the server and increment
                    # count of people in the room
                    with globals.people_count:
                        if (
                            self.interface.__dict__.get(
                                self.device.tag
                            ).get_tag()
                            == "people_counting_sensor_exit"
                        ):
                            globals.people_count._value -= 1
                        elif (
                            self.interface.__dict__.get(
                                self.device.tag
                            ).get_tag()
                            == "people_counting_sensor_entry"
                        ):
                            globals.people_count._value += 1
                    globals.queueMessages.put(
                        {
                            "type": "push",
                            "message": "ok",
                            "data": {
                                "people_count": globals.people_count._value,
                            },
                        }
                    )
                    self.interface.__dict__.get(self.device.tag).set_value(1)
                elif (
                    self.interface.__dict__.get(self.device.tag).get_input()
                    == 0
                    and self.interface.__dict__.get(
                        self.device.tag
                    ).get_value()
                    == 1
                ):
                    self.interface.__dict__.get(self.device.tag).set_value(0)
            else:
                value = self.interface.__dict__.get(
                    self.device.tag
                ).get_input()
                if (
                    value
                    is not self.interface.__dict__.get(
                        self.device.tag
                    ).get_value()
                ):
                    self.interface.__dict__.get(self.device.tag).set_value(
                        value
                    )
                    self.interface.save_state()

                    if (
                        self.interface.__dict__.get(self.device.tag).tag
                        == "presence_sensor"
                    ):
                        if (
                            value == 1
                            and self.interface.get_alarm_system() == 0
                        ):
                            self.interface.turn_all_lamp_on()
                            globals.queueMessages.put(
                                {
                                    "type": "push",
                                    "message": "ok",
                                    "data": self.interface.get_lamps_status(),
                                }
                            )
                            time.sleep(15)
                            self.interface.turn_all_lamp_off()
                            globals.queueMessages.put(
                                {
                                    "type": "push",
                                    "message": "ok",
                                    "data": self.interface.get_lamps_status(),
                                }
                            )
                            continue

                    if (
                        self.interface.__dict__.get(self.device.tag).kind
                        == "dth22"
                    ):
                        if (
                            value.get("temperature") == 0
                            and value.get("humidity") == 0
                        ):
                            continue
                    globals.queueMessages.put(
                        {
                            "type": "push",
                            "message": "ok",
                            "data": {
                                self.interface.__dict__.get(
                                    self.device.tag
                                ).get_tag(): value,
                            },
                        }
                    )

            if self.interface.__dict__.get(self.device.tag).kind == "dth22":
                time.sleep(1.8)
            else:
                time.sleep(0.25)


class SendMessage(threading.Thread):
    def __init__(self, client):
        threading.Thread.__init__(self)
        self.client = client

    def run(self):
        while True:
            if not globals.queueMessages.empty():
                message = globals.queueMessages.get()
                self.client.sendall(
                    bytes(json.dumps(message), encoding="utf-8")
                )
            time.sleep(0.20)
