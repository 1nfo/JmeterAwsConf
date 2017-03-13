import json,os

from .Config import AWSConfig, SSHConfig
from .Manager import InstanceManager, SSHConnectionManager, TaskManager, DupTaskException
from .Connection import SSHConnection
from .Util import Redirector

CONFIG  = json.load(open(__path__[0]+"/config.json"))
CONFIG["pemFilePath"] = CONFIG["pemFilePath"].replace("~",os.path.expanduser('~'))

# def insttest():
# 	instMngr = InstanceManager(AWSConfig(**CONFIG))
# 	print(json.dumps({"Master":instMngr.master,"Slaves":instMngr.slaves},indent=2))
# 	instMngr.startAll()
# 	masterConn = SSHConnection(SSHConfig(hostname = instMngr.master["PublicIp"],**CONFIG))
# 	slavesConn = {i['InstanceId']:SSHConnection(SSHConfig(hostname = i["PublicIp"],**CONFIG)) for i in instMngr.slaves}
# 	connMngr = SSHConnectionManager(masterConn,slavesConn)

def source(arg):
	from inspect import getsource
	print(getsource(arg))

def demo(path=None):
	with Redirector() as re:
		print(source(demo));
		print('')

		TaskName = "dummy"
		NumberOfSalves = 2
		UploadPath = path or "/Users/shilzhao/Desktop/PARS/MonthlyBenchmark_SmokeTest"
		taskMngr = TaskManager(config=CONFIG)
		try:
			taskMngr.startTask(TaskName)
		except Exception as exception:
			print(exception.args[0])
			print("Resuming first one: "+exception.args[1][0])
			taskMngr.startTask(TaskName,taskID=exception.args[1][0])
		taskMngr.instMngr.mute()
		taskMngr.connMngr.mute()
		taskMngr.setSlaveNumber(NumberOfSalves)
		taskMngr.setUploadDir(UploadPath)
		taskMngr.setupInstances()
		if taskMngr.checkStatus():    
		    taskMngr.refreshConnections()
		    taskMngr.uploadFiles()
		    taskMngr.updateRemotehost()
		    taskMngr.startSlavesServer()
		    taskMngr.startRDP()
		    taskMngr.runTest("smoke.jmx","ttt.csv")
		    taskMngr.stopSlavesServer()							

def cleanup():
	with Redirector() as re:
		print(source(cleanup));
		print('')

		
		TaskName = "dummy"
		NumberOfSalves = 2
		UploadPath = path or "/Users/shilzhao/Desktop/PARS/MonthlyBenchmark_SmokeTest"
		taskMngr = TaskManager(config=CONFIG)
		try:
			taskMngr.startTask(TaskName)
		except Exception as exception:
			print(exception.args[0])
			print("Resuming first one: "+exception.args[1][0])
			taskMngr.startTask(TaskName,taskID=exception.args[1][0])
		taskMngr.instMngr.mute()
		taskMngr.cleanup()