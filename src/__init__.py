import json, os

from .Config import AWSConfig, SSHConfig
from .Manager import InstanceManager, SSHConnectionManager, ClusterManager, DupClusterException
from .Connection import SSHConnection
from .Util import Redirector

CONFIG = json.load(open(__path__[0] + "/config.json"))
CONFIG["pemFilePath"] = os.path.join(os.path.expanduser('~'),CONFIG["pemFilePath"])
