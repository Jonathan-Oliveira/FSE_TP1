import json
import random
import socket
import time
import globals


def read_config():
    number = ""
    while number not in ["1", "2", "3", "4"]:
        number = input("Which config do you want to use? (1, 2, 3 or 4)\n")
        number = number.strip()
    number = int(number)
    print(f"Using config {number}")
    if number in [1, 3]:
        file_name = "client/config_1_3.json"
    elif number in [2, 4]:
        file_name = "client/config_2_4.json"

    with open(file_name, "r") as file:
        config = json.load(file)
    config.update(get_host_ip(number))
    return config


def get_host_ip(num):

    if num == 1:
        return {
            "client_ip": "164.41.98.29",
            "client_port": 10501,
            "name": "room_1",
        }
    elif num == 2:
        return {
            "client_ip": "164.41.98.26",
            "client_port": 10502,
            "name": "room_2",
        }
    elif num == 3:
        return {
            "client_ip": "164.41.98.28",
            "client_port": 10503,
            "name": "room_3",
        }
    elif num == 4:
        return {
            "client_ip": "164.41.98.15",
            "client_port": 10505,
            "name": "room_4",
        }


def createConection():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.bind(
        (
            globals.config.get("client_ip"),
            globals.config.get("client_port"),
        )
    )
    print("Waiting for connection...")
    connected = False
    while not connected:
        try:
            client.connect(
                (
                    globals.config.get("server_ip"),
                    globals.config.get("server_port"),
                )
            )
            connected = True
        except ConnectionRefusedError:
            time.sleep(1)
    print("Connected to server!")

    print("Sending data to server...")
    client.sendall(
        bytes(
            json.dumps(
                {
                    "type": "register",
                    "data": {
                        "name": globals.config.get("name"),
                        "devices": parse_devices_to_server(
                            globals.config.get("devices")
                        ),
                    },
                }
            ),
            "UTF-8",
        )
    )
    data = client.recv(1024)
    print("Received from server: ", data.decode())
    return client


def parse_devices_to_server(devices):
    parsed_devices = {}
    for device, values in devices.items():
        if device in [
            "people_counting_sensor_entry",
            "people_counting_sensor_exit",
        ]:
            continue

        parsed_devices.update(
            {
                device: {
                    "tag": str(values.get("tag")),
                    "name": str(values.get("name")),
                    "kind": str(values.get("type")),
                }
            }
        )
    parsed_devices.update(
        {
            "people_count": {
                "tag": "people_count",
                "name": "Contagem de pessoas",
                "kind": "input",
            },
            "alarm_system": {
                "tag": "alarm_system",
                "name": "Sistema de alarme",
                "kind": "output",
            },
        }
    )
    return parsed_devices


def parse_devices_to_client(devices):
    parsed_devices = {}
    for device, values in devices.items():
        parsed_devices.update(
            {
                device: {
                    "tag": str(values.get("tag")),
                    "name": str(values.get("name")),
                    "kind": str(values.get("type")),
                    "pin": int(values.get("gpio")),
                }
            }
        )
    return parsed_devices


def mock_sensor():
    while True:
        globals.queueMessages.put(
            {
                "type": "push",
                "message": "ok",
                "data": {
                    "temperature_humidity_sensor": {
                        "temperature": random.randint(15, 30),
                        "humidity": random.randint(0, 100),
                    },
                    # "lamp1": random.randint(0, 1),
                    # "lamp2": random.randint(0, 1),
                    "multimedia_projector": random.randint(0, 1),
                    "air_conditioner": random.randint(0, 1),
                },
            }
        )
        time.sleep(2)
