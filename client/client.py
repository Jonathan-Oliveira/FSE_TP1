import RPi.GPIO as GPIO
import time


import globals
from interface import ControlGPIO
from connection import SendMessage, ReceiveMessage, ApplyCommand, SeeInputs
from utils import parse_devices_to_client, createConection


def main():
    try:
        print("Starting client")
        globals.initialize()

        name = globals.config.get("name")
        devices = globals.config.get("devices")

        interface = ControlGPIO(**parse_devices_to_client(devices))
        interface.initialize()
        interface.load_state()
        state = interface.get_state()
        state["name"] = name
        globals.queueMessages.put(state)

        connection = createConection()

        inputs_devices = interface.get_inputs_devices()
        interface.print_all_devices()
        print(inputs_devices)
        for device in inputs_devices:
            SeeInputs(device, interface).start()

            ApplyCommand(interface).start()

            ReceiveMessage(connection).start()

            SendMessage(connection).start()
    except KeyboardInterrupt:
        globals.stop_threads = True
        time.sleep(1)
        GPIO.cleanup()
        connection.close()
        print("Client stopped")


if __name__ == "__main__":

    main()
