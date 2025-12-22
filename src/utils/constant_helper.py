from functools import lru_cache
import sys
import os
import json

USE_AVAILABLE_PORT=True

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))

CONFIG_PATH = os.path.join(BASE_DIR, "plugin.json")

if USE_AVAILABLE_PORT:
    from plotune_sdk.utils import AVAILABLE_PORT

@lru_cache(maxsize=1)
def get_config() -> dict:
    conf = json.load(open(CONFIG_PATH, "r"))
    conf["connection"]["port"] = AVAILABLE_PORT
    return conf

@lru_cache(maxsize=1)
def get_custom_config():
    conf = get_config()
    return conf["configuration"]