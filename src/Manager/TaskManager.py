import os, time

from ..Manager import *
from ..Config import AWSConfig, SSHConfig
from ..Connection import SSHConnection

class TaskManager(Manager):
    ## config is from config.json,
    #  taskID generally is not neccessary, it can be auto generated. 
    #  UNLESS there is a repeated taskname on AWS are running.
    #  In this case, 
    #    1. you need to specify an existing ID to continue to work on old task.
    #    2. or specify a new id, which is not existed, to start a new task.
    def __init__(self, taskName, slvNum, taskID=None, config={}):
        Manager.__init__(self)
        if self.verboseOrNot:
            print("Start task '%s'"%taskName)
        self.config = config
        self.awsConfig = AWSConfig(**config)
        self.instMngr = InstanceManager(self.awsConfig)
        self.instMngr.setTask(taskName,taskID)
        self.connMngr = SSHConnectionManager()
        self.slaveNumber = slvNum

    ## update slave number
    def setSlaveNumber(self,slvNum):
        self.slaveNumber = slvNum
        if self.verboseOrNot:
            print("Set slave number: %d"%slvNum)

    ## once slave number is determined, JAC will automatically add or remove nodes
    def setupInstances(self):
        if self.verboseOrNot:
            print("Setting up instances")
        self.instMngr.addMaster()
        diff = self.slaveNumber-len(self.instMngr.slaves)
        if diff<0 : 
            IDs = [i["InstanceId"] for i in self.instMngr.slaves[self.slaveNumber:]]
            self.instMngr.terminateInstances(IDs,self.connMngr.verboseOrNot) 
        elif diff>0:self.instMngr.addSlaves(diff);
        self.instMngr.startAll();

    ## update the test plan directory you want to upload,
    #  as well as related files like username and passwd csv
    #  parameter must to be a directory.
    def setUploadDir(self,directory):
        assert os.path.isdir(directory)
        self.UploadPath = directory

    ## upload the directory to all the nodes, master and slaves
    def uploadFiles(self,verbose=None):
        if verbose or verbose is None and self.verboseOrNot:
            print("Uploading files")
        li = [i["PublicIp"] for i in self.instMngr.listInstances() if "PublicIp" in i.keys()]
        for ip in li:
            strTuple = (self.config["pemFilePath"],self.UploadPath,self.config["username"],ip,self.instMngr.taskName)
            cmds = "scp -o 'StrictHostKeyChecking no' -i %s -r %s/. %s@%s:~/%s"%strTuple
            os.system(cmds)
            if verbose or verbose is None and self.verboseOrNot:
                print(cmds)
    
    ## repeatedly check if all node under current task is ready to connection
    #  will be time-out after 5 mins    
    def checkStatus(self):
        count=0
        while(count<30 and not self.instMngr.allInitialized()):
            time.sleep(10)
            count+=1
            if self.verboseOrNot:
                print("Some instances are still initializing")
        if self.instMngr.allInitialized(): return True
        return False

    ## start lightdm service on master
    #  the master must be lxdm image, where lightdm has installed already.
    def startRDP(self):
        if self.verboseOrNot:
            print("starting lightdm")
        self.connMngr.connectMaster()
        cmd = "sudo service lightdm start"
        self.connMngr.cmdMaster(cmd)
        self.connMngr.closeMaster()
    
    ## After instances all set, 
    #  refresh the availiable connections, and update to connection manager   
    def refreshConnections(self):
        if self.verboseOrNot:
            print("Refreshing connection list")
        self.instMngr.updateInstances()
        masterConn = SSHConnection(SSHConfig(hostname = self.instMngr.master["PublicIp"],**self.config))
        slavesConn = {i['InstanceId']:SSHConnection(SSHConfig(hostname = i["PublicIp"],**self.config)) for i in self.instMngr.slaves}
        self.connMngr.updateConnections(masterConn,slavesConn)

    ## update remote host to jmeter.properties files 
    def updateRemotehost(self):
        if self.verboseOrNot:
            print("updating master remotehost list")
        def replaceStr(slaveIPs):
            propertiesFilePath=self.config["propertiesPath"]
            ret = "awk '/^remote_hosts/{gsub(/.+/,"
            ret +='"remote_hosts='
            if len(slaveIPs)!=0: ret += slaveIPs[0]
            if len(slaveIPs)>1:
                for i in range(1,len(slaveIPs)):
                    ret += ','+slaveIPs[i]
            ret +="\")};{print}' "+propertiesFilePath
            ret +=" > "+".tmp.properties && cat .tmp.properties > " + propertiesFilePath
            return ret
        self.connMngr.connectMaster()
        cmd = replaceStr([i["PrivateIpAddress"] for i in self.instMngr.slaves])
        self.connMngr.cmdMaster(cmd)
        self.connMngr.closeMaster()
    
    ## start jmeter-server, only for running slaves    
    def startSlavesServer(self):
        if self.verboseOrNot:
            print("Starting jmeter server in slaves")
        self.connMngr.connectSlaves()
        self.connMngr.cmdSlaves("source .profile && cd %s && jmeter-server"%self.instMngr.taskName,verbose=False)
        self.connMngr.closeSlaves()

    ## stop all slaves' jmeter-server
    def stopSlavesServer(self):
        if self.verboseOrNot:
            print("Killing jmeter server in slaves")
        self.connMngr.connectSlaves()
        self.connMngr.cmdSlaves("ps aux | grep [j]meter-server | awk '{print $2}' | xargs kill")
        self.connMngr.closeSlaves()

    ## run jmeter with args 
    #  1. -t jmx, jmx file you want to run under you upload path
    #  2. -l output, the output file name
    def runTest(self,jmx,output):
        self.connMngr.connectMaster()
        self.connMngr.cmdMaster("source .profile && cd %s && jmeter -n -t %s -r -l %s"%(self.instMngr.taskName,jmx,output),verbose=True)
        self.connMngr.cmdMaster("source .profile && cd %s && cat %s"%(self.instMngr.taskName,output),verbose=True)
        self.connMngr.cmdMaster("source .profile && cd %s && cat jmeter.log"%(self.instMngr.taskName),verbose=True)
        self.connMngr.closeMaster()

    ## terminate all nodes
    def cleanup(self):
        if self.verboseOrNot:
            print("Terminating All nodes")
        self.instMngr.terminateMaster()
        self.instMngr.terminateSlaves()