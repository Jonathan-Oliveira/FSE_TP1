import json
import random
import socket
import time


def read_config():
    config = input("Digite o numero do ambiente:")
    if config == "1" or config == "3":
        name_file = "client/config_1_3.json"
    elif config == "2" or config == "4":
        name_file = "client/config_2_4.json"

    with open(name_file, "r") as file:
        json_data = file.read()
    return json.loads(json_data)


def createConection():
    config = read_config()
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.bind(
        (
            config.get("ip_servidor_distribuido"),
            config.get("porta_servidor_distribuido"),
        )
    )
    print("Waiting for connection...")
    connected = False
    while not connected:
        try:
            client.connect(
                (
                    config.get("ip_servidor_central"),
                    config.get("porta_servidor_central"),
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
                        "name": config.get("nome"),
                        "devices": parse_devices_to_server(
                            config.get("dispositivos")
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
