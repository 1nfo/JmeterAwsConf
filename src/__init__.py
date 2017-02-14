import json

from .Config import AWSConfig
from .Manager import InstanceManager

global_config  = json.load(open(__path__[0]+"/config.json"))
