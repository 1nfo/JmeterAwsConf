import json

from .Config import AWSConfig, SSHConfig
from .Manager import InstanceManager, SSHConnectionManager, TaskManager
from .Connection import SSHConnection

CONFIG  = json.load(open(__path__[0]+"/config.json"))

def _insttest():
	instMngr = InstanceManager(AWSConfig(**CONFIG))
	print(json.dumps({"Master":instMngr.master,"Slaves":instMngr.slaves},indent=2))
	instMngr.startAll()
	masterConn = SSHConnection(SSHConfig(hostname = instMngr.master["PublicIp"],**CONFIG))
	slavesConn = {i['InstanceId']:SSHConnection(SSHConfig(hostname = i["PublicIp"],**CONFIG)) for i in instMngr.slaves}
	connMngr = SSHConnectionManager(masterConn,slavesConn)

def _tasktest():
	taskMngr = TaskManager("dummy",2,CONFIG)
	taskMngr.setSlaveNumber(3)
	taskMngr.setupInstances()
	taskMngr.refreshConnections()
	taskMngr.updateRemotehost()
	taskMngr.startSlavesServer()
	