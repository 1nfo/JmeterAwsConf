import os, time

from ..Manager import *
from ..Config import AWSConfig, SSHConfig
from ..Connection import SSHConnection

class TaskManager(Manager):
    ## config is from config.json,
    #  if no task name when initializing, task name need to be set later;
    #  taskID generally is not neccessary, it can be auto generated. 
    #  UNLESS there is at least a repeated taskname running on AWS .
    #  In this case, 
    #    1. you need to specify an existing ID to continue to work on old task.
    #    2. or specify a new id, which is not existed, to start a new task.
    def __init__(self, config={}):
        Manager.__init__(self)
        self.config = config
        self.awsConfig = AWSConfig(**config)
        self.instMngr = InstanceManager(self.awsConfig)
        self.connMngr = SSHConnectionManager()

    ## set task name to task
    def startTask(self,taskName,taskID=None):
        self.instMngr.setTask(taskName,taskID)
        self.print("Start task '%s'"%taskName)

    ## update slave number
    def setSlaveNumber(self,slvNum):
        self.slaveNumber = slvNum
        self.print("Set slave number: %d"%slvNum)

    ## once slave number is determined, JAC will automatically add or remove nodes
    def setupInstances(self):
        self.print("Launching instances")
        self.instMngr.addMaster()
        diff = self.slaveNumber-len(self.instMngr.slaves)
        if diff<0 : 
            IDs = [i["InstanceId"] for i in self.instMngr.slaves[self.slaveNumber:]]
            self.instMngr.terminateInstances(IDs,self.connMngr.verboseOrNot) 
        elif diff>0:self.instMngr.addSlaves(diff);
        self.instMngr.startAll();
        self.print("Launched.")

    ## update the test plan directory you want to upload,
    #  as well as related files like username and passwd csv
    #  parameter must to be a directory.
    def setUploadDir(self,directory):
        assert os.path.isdir(directory)
        self.UploadPath = directory

    ## upload the directory to all the nodes, master and slaves
    def uploadFiles(self):
        self.print("Uploading files")
        li = [i["PublicIp"] for i in self.instMngr.listInstances() if "PublicIp" in i.keys()]
        for ip in li:
            self._uploads(self.UploadPath,ip,self.instMngr.taskName)
        self.print("Uploaded.")
            
    ## uploads from src to ip:~/des
    def _uploads(self,src,ip,des):
        strTuple = (self.config["pemFilePath"],src,self.config["username"],ip,des)
        cmds = "scp -o 'StrictHostKeyChecking no' -i %s -r %s/. %s@%s:~/%s"%strTuple
        self.print("%s >>> %s:%s"%(src,ip,des))
        os.system(cmds)
        

    ## repeatedly check if all node under current task is ready to connection
    #  will be time-out after 5 mins    
    def checkStatus(self):
        count=0
        while(count<20 and not self.instMngr.allInitialized()):
            count+=1
            self.print("Some instances are still initializing")
            time.sleep(15)
        if self.instMngr.allInitialized(): return True
        return False

    ## start lightdm service on master
    #  the master must be lxdm image, where lightdm has installed already.
    def startRDP(self):
        self.print("Starting lightdm")
        self.connMngr.connectMaster()
        cmd = "sudo service lightdm start"
        self.connMngr.cmdMaster(cmd)
        self.connMngr.closeMaster()
    
    ## After instances all set, 
    #  refresh the availiable connections, and update to connection manager   
    def refreshConnections(self):
        self.print("Refreshing connection list")
        self.instMngr.updateInstances()
        masterConn = SSHConnection(SSHConfig(hostname = self.instMngr.master["PublicIp"],**self.config))
        slavesConn = {i['InstanceId']:SSHConnection(SSHConfig(hostname = i["PublicIp"],**self.config)) for i in self.instMngr.slaves}
        self.connMngr.updateConnections(masterConn,slavesConn)
        self.print("Refreshed.")

    ## update remote host to jmeter.properties files 
    def updateRemotehost(self):
        self.print("Updating master remotehost list")
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
        self.print("Updated.")
    
    ## start jmeter-server, only for running slaves    
    def startSlavesServer(self):
        self.print("Starting jmeter server in slaves")
        self.connMngr.connectSlaves()
        self.connMngr.cmdSlaves("source .profile && cd %s && jmeter-server"%self.instMngr.taskName,verbose=False)
        self.connMngr.closeSlaves()
        # wait server all started, otherwise master may think task is done.
        time.sleep(5)
        self.print("Started.")

    ## stop all slaves' jmeter-server
    def stopSlavesServer(self):
        self.print("Killing jmeter server in slaves")
        self.connMngr.connectSlaves()
        self.connMngr.cmdSlaves("ps aux | grep [j]meter-server | awk '{print $2}' | xargs kill")
        self.connMngr.closeSlaves()
        self.print("Slave Servers down.")

    ## run jmeter with args 
    #  1. -t jmx, jmx file you want to run under you upload path
    #  2. -l output, the output file name
    def runTest(self,jmx,output):
        self.print("running test now ...")
        runJmeterCmd = "source .profile && cd %s && jmeter -n -t %s -r -l %s"%(self.instMngr.taskName,jmx,output)
        uploadS3Cmd = "source .profile && cd %s && aws s3 cp %s s3://%s/%s/%s --profile %s"\
                        %(self.instMngr.taskName,output,self.config["S3Bucket"],
                          self.instMngr.taskID,time.ctime().replace(" ","_"), self.config["profile_name"])
        self.connMngr.connectMaster()
        self.connMngr.cmdMaster(runJmeterCmd,verbose=True)
        self._uploads(self.config[".awsPath"],self.instMngr.master["PublicIp"],".aws")
        self.print("Done.\nUploading output csv to AWS S3")
        self.connMngr.cmdMaster(uploadS3Cmd,verbose=self.verboseOrNot)
        # self.connMngr.cmdMaster("source .profile && cd %s && cat %s"%(self.instMngr.taskName,output),verbose=True)
        # self.connMngr.cmdMaster("source .profile && cd %s && cat jmeter.log"%(self.instMngr.taskName),verbose=True)
        self.connMngr.closeMaster()
        self.print("Uploaded.")

    ## terminate all nodes
    def cleanup(self):
        self.print("Terminating All nodes")
        self.instMngr.terminateMaster()
        self.instMngr.terminateSlaves()
        self.print("Terminated.")