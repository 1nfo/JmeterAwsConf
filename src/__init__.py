import json, os

from .Config import AWSConfig, SSHConfig
from .Manager import InstanceManager, SSHConnectionManager, Client, DupClusterException
from .Connection import SSHConnection
from .Util import Redirector

CONFIG = json.load(open(__path__[0] + "/config.json"))
CONFIG["pemFilePath"] = CONFIG["pemFilePath"].replace("~", os.path.expanduser('~'))
