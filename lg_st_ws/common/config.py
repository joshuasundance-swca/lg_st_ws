from os import environ

BOT_NAME = environ["BOT_NAME"]
WS_HOST = environ["WS_HOST"]
WS_PORT = environ["WS_PORT"]
WS_URL = f"ws://{WS_HOST}:{WS_PORT}/thread" + "/{thread_id}/ws"
CUSTOM_INSTRUCTIONS = environ.get("CUSTOM_INSTRUCTIONS", "")
MODEL_NAME = environ.get("MODEL_NAME")
STRFTIME_FORMAT = "%Y-%m-%d %I:%M:%S %p %Z"
