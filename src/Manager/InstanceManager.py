import json
from boto3 import Session
from ..Parser import DescribeInstancesParser
from .Manager import Manager
    
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
