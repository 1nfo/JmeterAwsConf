import json

from .Config import AWSConfig, SSHConfig
from .Manager import InstanceManager, SSHConnectionManager
from .Connection import SSHConnection

CONFIG  = json.load(open(__path__[0]+"/config.json"))

def _test():
	instMngr = InstanceManager(AWSConfig(**CONFIG))
	print(json.dumps({"Master":instMngr.master,"Slaves":instMngr.slaves},indent=2))
	instMngr.startAll()
	masterConn = SSHConnection(SSHConfig(hostname = instMngr.master["PublicIp"],**global_config))
	slavesConn = {i['InstanceId']:SSHConnection(SSHConfig(hostname = i["PublicIp"],**global_config)) for i in instMngr.slaves}
	connMngr = SSHConnectionManager(masterConn,slavesConn)
	