from boto3 import Session
from paramiko import SSHClient, AutoAddPolicy 
from .Parser import DescribeInstancesParser

class Manager(object):
    pass
    
class InstanceManager(Manager):
    def __init__(self,awsConfig):
        self.descParser = None;
        self.config = awsConfig
        self.client = Session(profile_name=awsConfig.profile_name,region_name=awsConfig.region).client('ec2')
        self.descParser = DescribeInstancesParser(sg=awsConfig.securityGroups)
        self.master = None
        self.slaves = []
        self.updateInstances()
        self.verboseOrNot = True;
        
    def mute(self):
        self.verboseOrNot = False
    
    def verbose(self):
        # once set to be verbose, always it is.
        self.verboseOrNot = True
        
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
        if verbose:print(json.dumps(res,indent=2))
        return res
        
    def stopInstances(self,IDs,verbose):
        res = self.client.stop_instances(InstanceIds=IDs) if IDs else "No instance in the list"
        self.updateInstances()
        if verbose:print(json.dumps(res,indent=2))
        return res
    
    def terminateInstances(self,IDs,verbose):
        res = self.client.terminate_instances(InstanceIds=IDs) if IDs else "No instance in the list"
        self.updateInstances()
        if verbose:print(json.dumps(res,indent=2))
        return res
    
    def creatInstances(self,ImageID,num,InstanceType,SecurityGroups,area,verbose):
        res = self.client.run_instances(ImageId=ImageID,MinCount=num,MaxCount=num,\
                                        InstanceType=InstanceType,SecurityGroups=SecurityGroups, \
                                        Placement = {"AvailabilityZone":area})
        if verbose:print(res)
        return res
        
    def startMaster(self,verbose=None):
        if(self.master):
            self.startInstances([self.master['InstanceId']],verbose or self.verboseOrNot)
    
    def stopMaster(self,verbose=None):
        if(self.master):
            self.stopInstances([self.master['InstanceId']],verbose or self.verboseOrNot)
    
    def startSlaves(self,verbose=None):
        self.startInstances([i['InstanceId'] for i in self.slaves],verbose or self.verboseOrNot)
        
    def stopSlaves(self,verbose=None):
        self.stopInstances([i['InstanceId'] for i in self.slaves],verbose or self.verboseOrNot)
        
    def startAll(self,verbose=None):
        self.startInstances([self.master['InstanceId']],verbose)
        self.startInstances([i['InstanceId'] for i in self.slaves],verbose or self.verboseOrNot)
    
    def stopAll(self,verbose=None):
        self.stopInstances([self.master['InstanceId']],verbose)
        self.stopInstances([i['InstanceId'] for i in self.slaves],verbose or self.verboseOrNot)
    
    def terminateMaster(self,verbose=None):
        if(self.master):
            return self.terminateInstances([self.master["InstanceId"]],verbose or self.verboseOrNot)
        else: return "No master running"
    
    def terminateSlaves(self,verbose=None):
        return self.terminateInstances([i["InstanceId"] for i in self.slaves],verbose or self.verboseOrNot)
    
    ## untested
    def addMaster(self,LXDM=False,verbose=None):
        if not self.master:
            imageID = self.config.ami["LXDM"] if LXDM else self.config.ami["basic"]
            res = self.creatInstances(imageID,1,self.config.InstType["master"],self.config.securityGroups,self.config.zone,verbose or self.verboseOrNot)
            ID = res['Instances'][0]["InstanceId"]
            self.client.create_tags(Resources = [ID], Tags = [{'Key': 'Name', 'Value': 'Master'}])  
            self.updateInstances()
            return ID
        else :return "Running Master, Terminate it before lanuch a new one"
    ## untested   
    def addSlaves(self,num,LXDM=False,verbose=None):
        imageID = self.config.ami["LXDM"] if LXDM else self.config.ami["basic"]
        res = self.creatInstances(imageID,num,self.config.InstType["slave"],self.config.securityGroups,self.config.zone,verbose or self.verboseOrNot)
        IDs = [i["InstanceId"] for i in res['Instances']]
        self.client.create_tags(Resources = IDs, Tags = [{'Key': 'Name', 'Value': 'Slave'}]) 
        self.updateInstances()
        return IDs
        