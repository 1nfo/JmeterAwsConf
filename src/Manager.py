import json
from boto3 import Session
from .Parser import DescribeInstancesParser

class Manager(object):
    def __init__(self):
        self.verboseOrNot = True

    def mute(self):
        self.verboseOrNot = False
    
    def verbose(self):
        # once set to be verbose, always it is.
        self.verboseOrNot = True
    
class InstanceManager(Manager):
    def __init__(self,config):
        Manager.__init__(self)
        self.descParser = None
        self.config = config
        self.client = Session(profile_name=config.profile_name,region_name=config.region).client('ec2')
        self.descParser = DescribeInstancesParser(sg=config.securityGroups)
        self.master = None
        self.slaves = []
        self.updateInstances()
        
    def updateInstances(self):
        self.descParser.setResponse(self.client.describe_instances())
        details = self.descParser.listDetails();
        master = [i for i in details if i["Tags"][0]["Value"]=="Master"]
        self.master = master[0] if master else None
        self.slaves = [i for i in details if i["Tags"][0]["Value"]=="Slave"]
    
    def listInstances(self):
        return self.descParser.listDetails()
    
    def startInstances(self,IDs,verbose):
        res = self.client.start_instances(InstanceIds=IDs) if IDs else "No instance in the list"
        self.updateInstances()
        if verbose or verbose is None and self.verboseOrNot:
            print(json.dumps(res,indent=2))
        return res
        
    def stopInstances(self,IDs,verbose):
        res = self.client.stop_instances(InstanceIds=IDs) if IDs else "No instance in the list"
        self.updateInstances()
        if verbose or verbose is None and self.verboseOrNot:
            print(json.dumps(res,indent=2))
        return res
    
    def terminateInstances(self,IDs,verbose):
        res = self.client.terminate_instances(InstanceIds=IDs) if IDs else "No instance in the list"
        self.updateInstances()
        if verbose or verbose is None and self.verboseOrNot:
            print(json.dumps(res,indent=2))
        return res
    
    def creatInstances(self,ImageID,num,InstanceType,SecurityGroups,area,verbose):
        res = self.client.run_instances(ImageId=ImageID,MinCount=num,MaxCount=num,\
                                        InstanceType=InstanceType,SecurityGroups=SecurityGroups, \
                                        Placement = {"AvailabilityZone":area})
        if verbose or verbose is None and self.verboseOrNot:
            print(res)
        return res
        
    def startMaster(self,verbose=None):
        if(self.master):
            self.startInstances([self.master['InstanceId']],verbose)
    
    def stopMaster(self,verbose=None):
        if(self.master):
            self.stopInstances([self.master['InstanceId']],verbose)
    
    def startSlaves(self,verbose=None):
        self.startInstances([i['InstanceId'] for i in self.slaves],verbose)
        
    def stopSlaves(self,verbose=None):
        self.stopInstances([i['InstanceId'] for i in self.slaves],verbose)
        
    def startAll(self,verbose=None):
        self.startInstances([self.master['InstanceId']],verbose)
        self.startInstances([i['InstanceId'] for i in self.slaves],verbose )
    
    def stopAll(self,verbose=None):
        self.stopInstances([self.master['InstanceId']],verbose)
        self.stopInstances([i['InstanceId'] for i in self.slaves],verbose)
    
    def terminateMaster(self,verbose=None):
        if(self.master):
            return self.terminateInstances([self.master["InstanceId"]],verbose)
        else: return "No master running"
    
    def terminateSlaves(self,verbose=None):
        return self.terminateInstances([i["InstanceId"] for i in self.slaves],verbose)
    
    def addMaster(self,LXDM=True,instType=None,verbose=None):
        if not self.master:
            imageID = self.config.ami["LXDM"] if LXDM else self.config.ami["basic"]
            instType = self.config.instType["master"] if not instType else instType
            res = self.creatInstances(imageID,1,instType,self.config.securityGroups,self.config.zone,verbose)
            ID = res['Instances'][0]["InstanceId"]
            self.client.create_tags(Resources = [ID], Tags = [{'Key': 'Name', 'Value': 'Master'}])  
            self.updateInstances()
            return ID
        else :return "Running Master, Terminate it before lanuch a new one"
      
    def addSlaves(self,num,LXDM=False,iType=None,verbose=None):
        imageID = self.config.ami["LXDM"] if LXDM else self.config.ami["basic"]
        instType = self.config.instType["slave"] if not iType else iType
        res = self.creatInstances(imageID,num,instType,self.config.securityGroups,self.config.zone,verbose)
        IDs = [i["InstanceId"] for i in res['Instances']]
        self.client.create_tags(Resources = IDs, Tags = [{'Key': 'Name', 'Value': 'Slave'}]) 
        self.updateInstances()
        return IDs
        
class SSHConnectionManager(Manager):
    def __init__(self,masterConn=None,slavesConn={}):
        self.updateConnections(masterConn,slavesConn)
        self.verboseOrNot = True
    
    def updateConnections(self,masterConn,slavesConn):
        self.masterConn = masterConn
        self.slavesConn = slavesConn

    def connectMaster(self):
        self.masterConn.connect()
        
    def closeMaster(self):
        self.masterConn.close()
        
    def connectSlaves(self,IDs=[]):
        if not IDs: IDs = list(self.slavesConn.keys())
        for ID in IDs:
            self.slavesConn[ID].connect()
    
    def closeSlaves(self,IDs=[]):
        if not IDs: IDs = list(self.slavesConn.keys())
        for ID in IDs:
            self.slavesConn[ID].close()
            
    def cmdMaster(self,cmd,verbose=None):
        transport = self.masterConn.ssh.get_transport()
        if not transport or not transport.is_active(): print("Not active connection")
        else: self.masterConn.cmd(cmd, verbose if verbose is not None else self.verboseOrNot)
    
    def cmdSlaves(self,cmd,IDs=[],verbose=None):
        verbose = verbose if verbose is not None else self.verboseOrNot
        transport = self.masterConn.ssh.get_transport()
        if not IDs: IDs = [k for k in self.slavesConn if transport and transport.is_active()]
        # if cmd is list, cmd are mapped to different slaves
        if type(cmd)==list:
            n = len(cmd) if len(cmd)<len(IDs) else len(IDs)
            for i in range(n):
                self.slavesConn[IDs[i]].cmd(cmd[i],verbose)
        # if dict, mapping according to instance's id
        if type(cmd)==dict:
            if not IDs: print("parameter 'IDs' is specified but ignored since cmd included it")
            for ID in cmd:
                if not ID in self.slavesConn.keys(): print('%s is not found in SSH connection manager'%ID)
                else:
                    self.slavesConn[ID].cmd(cmd[ID],verbose)
        # if str, all slaves exec the same one
        if type(cmd)==str:
            if not IDs: print("No active connection")
            else:
                for ID in IDs:
                    self.slavesConn[ID].cmd(cmd,verbose)