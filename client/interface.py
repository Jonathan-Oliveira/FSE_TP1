import RPi.GPIO as GPIO
import board
import adafruit_dht
from typing import Union
import json
import globals


class Device:
    def __init__(self, name, pin, tag, kind):
        self.name = name
        self.pin = pin
        self.value = 0
        self.tag = tag
        if kind == "output":
            self.kind = GPIO.OUT
        elif kind == "input":
            self.kind = GPIO.IN
        elif kind == "dth22":
            self.kind = "dth22"
            self.pin = board.D4 if pin == 4 else board.D18
            self.sensor = adafruit_dht.DHT22(self.pin, use_pulseio=False)

    def turn_off(self):
        if self.kind == "dth22":
            return
        GPIO.output(self.pin, GPIO.LOW)
        self.value = 0

    def turn_on(self):
        if self.kind == "dth22":
            return
        GPIO.output(self.pin, GPIO.HIGH)
        self.value = 1

    def turn_on_of(self):
        if self.kind == "dth22":
            return
        if self.value == 1:
            self.turn_off()
        else:
            self.turn_on()

    def get_tag(self):
        return self.tag

    def get_input(self):
        if self.kind == "dth22":
            try:
                temperature_c = self.sensor.temperature
                humidity = self.sensor.humidity
                return {
                    "temperature": temperature_c,
                    "humidity": humidity,
                }
            except RuntimeError:
                return {
                    "temperature": 0,
                    "humidity": 0,
                }
        return GPIO.input(self.pin)

    def get_value(self):
        return self.value

    def set_value(self, value):
        self.value = value

    def __repr__(self):
        return f"Device({self.name}, {self.pin}, {self.value}, {self.tag}, {self.kind})"

    def watch_change(self, callback):
        if self.kind == "dth22" or self.kind == GPIO.OUT:
            return
        GPIO.add_event_detect(
            self.pin, GPIO.BOTH, callback=self.callback, bouncetime=100
        )

    def callback(self, channel):
        self.value = GPIO.input(channel)
        print(f"callback: {self.name} {self.value}")


class ControlGPIO:
    def __init__(self, **kwargs):
        self.alarm_system = 0
        for key, value in kwargs.items():
            setattr(self, key, Device(**value))

    def get_alarm_system(self):
        return self.alarm_system

    def set_alarm_system(self, value):
        self.alarm_system = value

    def initialize(self):
        for device in self.__dict__.values():
            if type(device) != Device:
                continue
            if device.kind == "dth22":
                continue
            GPIO.setup(device.pin, device.kind)

    def turn_all_off(self):
        for device in self.__dict__.values():
            if type(device) != Device:
                continue
            if device.kind == "dth22":
                continue
            device.turn_off()

    def get_lamps_values(self):
        lamps = {}
        for device in self.__dict__.values():
            if type(device) != Device:
                continue
            if device.name.startswith("lamp"):
                lamps[device.tag] = device.get_value()
        return lamps

    def turn_all_lamp_off(self):
        for device in self.__dict__.values():
            if type(device) != Device:
                continue
            if device.name.startswith("lamp"):
                device.turn_off()

    def turn_all_lamp_on(self):
        for device in self.__dict__.values():
            if type(device) != Device:
                continue
            if device.name.startswith("lamp"):
                device.turn_on()

    def get_device(self, device: str):
        return getattr(self, device, None)

    def apply_commands(self, commands):
        devices_updates = {}
        for device, action in commands.items():
            device = device.lower()
            if device == "alarm_system":
                self.set_alarm_system(value=1 if action == "on" else 0)
                devices_updates["alarm_system"] = self.get_alarm_system()
                continue
            self.apply_command(device, action)
            devices_updates[device] = self.get_device(device).get_value()
        return devices_updates

    def apply_command(self, device, action):
        if device == "all":
            getattr(self, f"turn_all_{action}")()
        else:
            getattr(self, device).turn_on() if action == "on" else getattr(
                self, device
            ).turn_off()

    def save_state(self):
        # Save state each device in file state.json
        data_to_save = {}
        for device in self.__dict__.values():
            if type(device) != Device:
                continue
            data_to_save[device.tag] = device.get_value()
        data_to_save["alarm_system"] = self.get_alarm_system()
        data_to_save["people_count"] = globals.people_count._value
        with open("client/state.json", "w") as file:
            json.dump(data_to_save, file)

    def get_state(self):
        with open("client/state.json", "r") as file:
            json_data = file.read()
        return json.loads(json_data)

    def set_state(self, state):
        for device in self.__dict__.values():
            if device.tag in state:
                if type(state.get(device.tag)) == bool:
                    device.turn_on() if state.get(
                        device.tag
                    ) else device.turn_off()
                else:
                    device.value = state.get(device.tag)

    def print_all_devices(self):
        for device in self.__dict__.values():
            print(device)

    def get_inputs_devices(self):
        return [
            device
            for device in self.__dict__.values()
            if type(device) == Device
            and (device.kind == GPIO.IN or device.kind == "dth22")
        ]
