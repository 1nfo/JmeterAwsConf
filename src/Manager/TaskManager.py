from ..Manager import *
from ..Config import AWSConfig, SSHConfig
from ..Connection import SSHConnection

class TaskManager(Manager):
    def __init__(self, taskName, slvNum=0, config={}):
        Manager.__init__(self)
        self.config = config
        self.awsConfig = AWSConfig(**config)
        self.instMngr = InstanceManager(self._genID(taskName), self.awsConfig)
        self.connMngr = SSHConnectionManager()
        self.setSlaveNumber(slvNum)
    
    def _genID(self,name):
        import os,time
        return name
        ## future feature: more tags on nodes
        return"%s-%s@%s-%s"%(name,os.getlogin(),os.uname()[1],time.ctime().replace(" ","-"))
    
    def setupInstances(self):
        if self.verboseOrNot:self.instMngr.addMaster()
        diff = self.slaveNumber-len(self.instMngr.slaves)
        if diff<0 : 
            IDs = [i["InstanceId"] for i in self.instMngr.slaves[self.slaveNumber:]]
            self.instMngr.terminateInstances(IDs,self.verboseOrNot) 
        elif diff>0:self.instMngr.addSlaves(diff);
        self.instMngr.startAll();
    
    def setSlaveNumber(self,slvNum):
        self.slaveNumber = slvNum
        
    def startRDP(self):
        elf.connMngr.connectMaster()
        cmd = "sudo service lightdm start"
        self.connMngr.cmdMaster(cmd)
        self.connMngr.closeMaster()
        
    def refreshConnections(self):
        self.instMngr.updateInstances()
        masterConn = SSHConnection(SSHConfig(hostname = self.instMngr.master["PublicIp"],**self.config))
        slavesConn = {i['InstanceId']:SSHConnection(SSHConfig(hostname = i["PublicIp"],**self.config)) for i in self.instMngr.slaves}
        self.connMngr.updateConnections(masterConn,slavesConn)

    def updateRemotehost(self):
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
        
    def startSlavesServer(self):
        self.connMngr.connectSlaves()
        self.connMngr.cmdSlaves("source .profile && jmeter-server",verbose=False)
        self.connMngr.closeSlaves()