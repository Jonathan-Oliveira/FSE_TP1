import json


def load_config() -> dict:
    with open("server/config.json", "r") as file:
        json_data = file.read()
    config = json.loads(json_data)
    return config


commands_user = {
    1: "lamp1",
    2: "lamp2",
    3: "air_conditioner",
    4: "multimedia_projector",
    5: {"lamp1": "on", "lamp2": "on"},
    6: {"lamp1": "off", "lamp2": "off"},
    7: {
        "lamp1": "on",
        "lamp2": "on",
        "air_conditioner": "on",
        "multimedia_projector": "on",
    },
    8: {
        "lamp1": "off",
        "lamp2": "off",
        "air_conditioner": "off",
        "multimedia_projector": "off",
    },
    9: "alarm_system",
    10: "buzzer_alarm",
}
