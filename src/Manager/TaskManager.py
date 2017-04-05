from ..Manager import *
from ..Config import AWSConfig, SSHConfig
from ..Connection import SSHConnection
from ..Util import JMX
from ..Parser import JMXParser
import os
import time
from copy import deepcopy


class TaskManager(Manager):
    #  config is from config.json,
    #  taskID generally is not neccessary for creating a new task, it can be auto generated.
    #  but it must be provided when resuming a previous task
    #  UNLESS there is at least a repeated taskname running on AWS .
    #  In this case,
    #    1. you need to specify an existing ID to continue to work on old task.
    #    2. or specify a new id, which is not existed, to start a new task.
    def __init__(self, pauseFunc=None, sid=None):
        Manager.__init__(self)
        self.verbose()
        self.sid = sid
        self.instMngr = None


    def setConfig(self, config):
        self.config = deepcopy(config)


    #  set task name to task
    def startTask(self, taskName, taskID=None):
        self.instMngr = InstanceManager(AWSConfig(**self.config))
        self.connMngr = SSHConnectionManager()
        self.print("Start task '%s'" % taskName)
        self.instMngr.setTask(taskName, taskID)

    #  set description
    def setTaskDesc(self,desc):
        self.instMngr.setTaskDesc(desc)

    #  update slave number
    def setSlaveNumber(self, slvNum):
        self.slaveNumber = slvNum
        #self.print("Set slave number: %d" % slvNum)

    #  once slave number is determined, JAC will automatically add or remove nodes
    def setupInstances(self):
        self.print("Launching instances")
        self.instMngr.addMaster()
        diff = self.slaveNumber - len(self.instMngr.slaves)
        if diff < 0:
            IDs = [i["InstanceId"] for i in self.instMngr.slaves[self.slaveNumber:]]
            self.instMngr.terminateInstances(IDs, self.connMngr.verboseOrNot)
        elif diff > 0:
            self.instMngr.addSlaves(diff)
        self.instMngr.startAll()
        self.print("Launched.")

    #  update the test plan directory you want to upload,
    #  as well as related files like username and passwd csv
    #  parameter must to be a directory.
    def setUploadDir(self, directory):
        assert os.path.isdir(directory)
        self.UploadPath = directory

    #  upload the directory to all the nodes, master and slaves
    def uploadFiles(self):
        # # make sure every jmx save output as xml
        # for jmxPath in os.listdir(self.UploadPath):
        #     if jmxPath.endswith(".jmx"):
        #         jmx = JMX("%s/%s"%(self.UploadPath,jmxPath))
        #         if not jmx.isSaveAsXML():
        #             jmx.saveXMLasTrue()
        self.print("Uploading files")
        self.connMngr.connectAll()
        self.connMngr.cmdAll("mkdir %s"%self.instMngr.taskName)
        self.connMngr.putAll(os.path.join(self.UploadPath),self.instMngr.taskName,verbose=True)
        self.connMngr.closeAll()
        self.print("Uploaded.")

    #  uploads from src to ip:~/des
    # def _uploads(self, src, ip, des):
    #     strTuple = (self.config["pemFilePath"], src, self.config["username"], ip, des)
    #     cmds = "scp -o 'StrictHostKeyChecking no' -i %s -r %s/. %s@%s:~/%s" % strTuple
    #     self.print("  --> node, IP: %s"%ip)

    #  repeatedly check if all node under current task is ready to connection
    #  will be time-out after 5 mins
    def checkStatus(self,sleepFunc):
        count = 0
        if not self.instMngr.allInitialized(): self.print("Some instances are initializing ", end="")
        while (count < 20 and not self.instMngr.allInitialized()):
            count += 1
            self.print(".",end="")
            sleepFunc(10)
        self.print("")
        if self.instMngr.allInitialized(): return True
        return False

    #  start lightdm service on master
    #  the master must be lxdm image, where lightdm has installed already.
    def startRDP(self):
        self.print("Starting lightdm")
        self.connMngr.connectMaster()
        cmd = "sudo service lightdm start"
        self.connMngr.cmdMaster(cmd)
        self.connMngr.closeMaster()

    #  After instances all set,
    #  refresh the availiable connections, and update to connection manager
    def refreshConnections(self, verbose=None):
        self.print("Refreshing connection list", verbose=verbose)
        self.instMngr.updateInstances()
        masterConn = SSHConnection(SSHConfig(hostname=self.instMngr.master["PublicIp"], **self.config))
        slavesConn = {i['InstanceId']: SSHConnection(SSHConfig(hostname=i["PublicIp"], **self.config)) for i in
                      self.instMngr.slaves}
        self.connMngr.updateConnections(masterConn, slavesConn)
        self.print("Refreshed.", verbose=verbose)

    #  update remote host to jmeter.properties files
    def updateRemotehost(self):
        self.print("Updating master remotehost list")

        def replaceStr(slaveIPs):
            propertiesFilePath = self.config["propertiesPath"]
            ret = "awk '/^remote_hosts/{gsub(/.+/,"
            ret += '"remote_hosts='
            if len(slaveIPs) != 0: ret += slaveIPs[0]
            if len(slaveIPs) > 1:
                for i in range(1, len(slaveIPs)):
                    ret += ',' + slaveIPs[i]
            ret += "\")};{print}' " + propertiesFilePath
            ret += " > " + ".tmp.properties && cat .tmp.properties > " + propertiesFilePath
            return ret

        self.connMngr.connectMaster()
        cmd = replaceStr([i["PrivateIpAddress"] for i in self.instMngr.slaves])
        self.connMngr.cmdMaster(cmd)
        self.connMngr.closeMaster()
        self.print("Updated.")

    #  start jmeter-server, only for running slaves
    def startSlavesServer(self):
        self.print("Starting jmeter server in slaves")
        self.connMngr.connectSlaves()
        self.connMngr.cmdSlaves("source .profile && cd %s && jmeter-server" % self.instMngr.taskName, verbose=False)
        self.connMngr.closeSlaves()
        # wait server all started, otherwise master may think task is done.
        time.sleep(5)
        self.print("Started.")

    #  stop master jmeter
    def stopMasterJmeter(self, verbose=None):
        self.print("Killing jmeter in Master")
        self.connMngr.connectMaster()
        self.connMngr.cmdMaster("ps aux | grep jmeter | awk '{print $2}' | xargs kill")
        self.connMngr.closeMaster()
        self.print("Master Killed.")

    #  stop all slaves' jmeter-server
    def stopSlavesServer(self, verbose=None):
        self.print("Killing jmeter server in slaves", verbose)
        self.connMngr.connectSlaves()
        self.connMngr.cmdSlaves("ps aux | grep [j]meter-server | awk '{print $2}' | xargs kill", verbose=verbose)
        self.connMngr.closeSlaves()
        self.print("Slave Killed.", verbose)

    #  run jmeter with args
    #  1. -t jmx, jmx file you want to run under you upload path
    #  2. -l output, the output file name
    def runTest(self, jmx):
        self.print("\nrunning test now ...")
        # logstash conf files
        jmxParser = JMXParser(JMX("%s/%s"%(self.UploadPath,jmx)))
        output = jmxParser.getOutputFilename()
        mergedOutput = "merged.csv"
        confFile = jmxParser.getConf("/home/ubuntu/"+mergedOutput,self.instMngr.taskID,self.config["es_IP"]);
        confCmd = 'source .profile && echo \'%s\' > .tmpConf && sudo mv .tmpConf %s/jmeterlog.conf'%(
            confFile,self.config["logstash_conf_dir"])
        runJmeterCmd = "source .profile && cd %s && echo "" > %s && jmeter -n -t %s -r " % (
            self.instMngr.taskName, output, jmx) # -l output.csv is not the result we want.
        awkCmd = '''awk -v RS='"' 'NR % 2 == 0 {{ gsub(/\\n/, "") }} {{ printf("%s%s", $0, RT) }}' {0}/{1} >> {2}'''.format(
            self.instMngr.taskName,output,mergedOutput)
        # uploadS3Cmd = "source .profile && cd %s && aws s3 cp %s s3://%s/%s/%s --profile %s" \
        #               % (self.instMngr.taskName, output, self.config["S3Bucket"],
        #                  self.instMngr.taskID, time.ctime().replace(" ", "_"), self.config["profile_name"])
        self.connMngr.connectMaster()
        self.connMngr.cmdMaster(confCmd)
        self.connMngr.cmdMaster("sudo systemctl restart logstash.service")
        self.connMngr.cmdMaster(runJmeterCmd, verbose=True)
        self.connMngr.cmdMaster(awkCmd)
        #self.print("Test done.\nUploading output csv to AWS S3")
        # s3 uploads
        # self.connMngr.cmdMaster(uploadS3Cmd, verbose=self.verboseOrNot)
        # self.print("Uploaded.")
        self.connMngr.closeMaster()

    #  terminate all nodes
    def cleanup(self):
        self.print("Terminating All nodes")
        self.instMngr.terminateMaster()
        self.instMngr.terminateSlaves()
        self.print("Terminated.")

    def esCheck(self):
        self.print("Checking elasticsearch connection")
        self.connMngr.connectMaster()
        self.connMngr.cmdMaster("nc -zv %s %s"%tuple(self.config["es_IP"].split(":")),verbose=True)
        self.connMngr.closeMaster()
