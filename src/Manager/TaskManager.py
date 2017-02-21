from ..Manager import *
from ..Config import AWSConfig, SSHConfig
from ..Connection import SSHConnection

class TaskManager(Manager):
    def __init__(self, taskName, slvNum, config, taskID=None):
        Manager.__init__(self)
        self.config = config
        self.awsConfig = AWSConfig(**config)
        self.instMngr = InstanceManager(self.awsConfig)
        self.instMngr.setTask(taskName,taskID)
        self.connMngr = SSHConnectionManager()
        self.slaveNumber = slvNum
    
    def setupInstances(self):
        if self.verboseOrNot:
            print("Setting up instances")
        self.instMngr.addMaster()
        diff = self.slaveNumber-len(self.instMngr.slaves)
        if diff<0 : 
            IDs = [i["InstanceId"] for i in self.instMngr.slaves[self.slaveNumber:]]
            self.instMngr.terminateInstances(IDs,self.verboseOrNot) 
        elif diff>0:self.instMngr.addSlaves(diff);
        self.instMngr.startAll();
    
    def setSlaveNumber(self,slvNum):
        self.slaveNumber = slvNum
        if self.verboseOrNot:
            print("Set slave number: %d"%slvNum)
        
    def checkStatus(self):
        import time
        count=0
        while(count<30 and not self.instMngr.allInitialized()):
            time.sleep(10)
            count+=1
            if self.verboseOrNot:
                print("Some instances are still initializing")
        if self.instMngr.allInitialized(): return True
        return False

    def startRDP(self):
        if self.verboseOrNot:
            print("starting lightdm")
        self.connMngr.connectMaster()
        cmd = "sudo service lightdm start"
        self.connMngr.cmdMaster(cmd)
        self.connMngr.closeMaster()
        
    def refreshConnections(self):
        if self.verboseOrNot:
            print("Refreshing connection list")
        self.instMngr.updateInstances()
        masterConn = SSHConnection(SSHConfig(hostname = self.instMngr.master["PublicIp"],**self.config))
        slavesConn = {i['InstanceId']:SSHConnection(SSHConfig(hostname = i["PublicIp"],**self.config)) for i in self.instMngr.slaves}
        self.connMngr.updateConnections(masterConn,slavesConn)

    def updateRemotehost(self):
        if self.verboseOrNot:
            print("updating master remotehost list")
        def replaceStr(slaveIPs,propertiesFilePath="/usr/local/apache-jmeter-2.13/bin/jmeter.properties"):
            ret = "awk '/^remote_hosts/{gsub(/.+/,"
            ret +='"remote_hosts='
            if len(slaveIPs)!=0: ret += slaveIPs[0]
            if len(slaveIPs)>1:
                for i in range(1,len(slaveIPs)):
                    ret += ','+slaveIPs[i]
            ret +="\")};{print}' "+propertiesFilePath
            ret +=" > "+"tmp.properties && cat tmp.properties > " + propertiesFilePath
            return ret
        self.connMngr.connectMaster()
        cmd = replaceStr([i["PrivateIpAddress"] for i in self.instMngr.slaves])
        self.connMngr.cmdMaster(cmd)
        self.connMngr.closeMaster()
    
    ## start only running slaves    
    def startSlavesServer(self):
        if self.verboseOrNot:
            print("Starting jmeter server in slaves")
        self.connMngr.connectSlaves()
        self.connMngr.cmdSlaves("source .profile && jmeter-server",verbose=False)
        self.connMngr.closeSlaves()

    def runTest(self,path,output):
        def parseCmd(path,output):
            li = path.split("/")
            return "source .profile && cd "+" && cd ".join(li[:-1]),"jmeter -n -t "+li[-1]+" -r"
        self.connMngr.connectMaster()
        cmds = parseCmd(path,output)
        self.connMngr.cmdMaster(" && ".join(cmds),verbose=True)
        self.connMngr.cmdMaster(" && ".join([cmds[0],"cat "+output]),verbose=True)
        self.connMngr.cmdMaster(" && ".join([cmds[0],"cat "+"jmeter.log"]),verbose=True)
        self.connMngr.closeMaster()

    def cleanup(self):
        if self.verboseOrNot:
            print("Terminating All nodes")
        self.instMngr.terminateMaster()
        self.instMngr.terminateSlaves()