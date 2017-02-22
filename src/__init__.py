import json

from .Config import AWSConfig, SSHConfig
from .Manager import InstanceManager, SSHConnectionManager, TaskManager
from .Connection import SSHConnection

CONFIG  = json.load(open(__path__[0]+"/config.json"))

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

def demo():
	print(source(demo));
	print('')


	TaskName = "dummy"
	NumberOfSalves = 2
	UploadPath = "/Users/shilzhao/Desktop/PARS/MonthlyBenchmark_SmokeTest"
	try:
		taskMngr = TaskManager(TaskName,NumberOfSalves,config=CONFIG)
	except Exception as exception:
		print(exception.args[0])
		print("Resuming first one: "+exception.args[1][0])
		taskMngr = TaskManager(TaskName,NumberOfSalves,taskID=exception.args[1][0] ,config=CONFIG)
	taskMngr.instMngr.mute()
	taskMngr.connMngr.mute()
	taskMngr.setUploadDir(UploadPath)
	#taskMngr.setSlaveNumber(3)
	taskMngr.setupInstances()
	if taskMngr.checkStatus():    
	    taskMngr.refreshConnections()
	    taskMngr.uploadFiles()
	    taskMngr.updateRemotehost()
	    taskMngr.startSlavesServer()
	    taskMngr.startRDP()
	    taskMngr.runTest("MonthlyBenchmark_SmokeTest.jmx","ttt.csv")
	    taskMngr.stopSlavesServer()

def cleanup():
	print(source(cleanup));
	print('')

	
	TaskName = "dummy"
	NumberOfSalves = 2
	UploadPath = "/Users/shilzhao/Desktop/PARS/MonthlyBenchmark_SmokeTest"
	taskMngr = TaskManager(TaskName,NumberOfSalves,config=CONFIG)
	taskMngr.instMngr.mute()
	taskMngr.cleanup()