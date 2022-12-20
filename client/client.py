import json
import socket
import threading
import time

import globals
from interface import ControlGPIO
from connection import SendMessage, ReceiveMessage, ApplyCommand, SeeInputs
from utils import read_config, parse_devices_to_client, createConection


def main():
    print("Starting client")
    globals.initialize()

    config = read_config()

    name = config.get("nome")
    devices = config.get("dispositivos")

    interface = ControlGPIO(**parse_devices_to_client(devices))
    interface.initialize()

    state = interface.get_state()
    state["name"] = name
    globals.queueMessages.put(state)

    client = createConection()

    inputs_devices = interface.get_inputs_devices()
    interface.print_all_devices()
    print(inputs_devices)
    for device in inputs_devices:
        see_input = SeeInputs(device, interface)
        see_input.start()

    ApplyCommand(interface).start()

    ReceiveMessage(client).start()

    SendMessage(client).start()


if __name__ == "__main__":
    main()
