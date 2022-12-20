import json


def load_config() -> dict:
    with open("server/config.json", "r") as file:
        json_data = file.read()
    config = json.loads(json_data)
    return config
