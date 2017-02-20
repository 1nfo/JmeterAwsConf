import json
from boto3 import Session
from ..Parser import DescribeInstancesParser
from .Manager import Manager
    
## instance manager is responsible to provide wrapped API from SDK
#  to control master and slaves' lifecycle
class InstanceManager(Manager):
    ## init with AWSConfig class
    def __init__(self,taskID,config):
        Manager.__init__(self)
        self.taskID = taskID
        self.descParser = None
        self.config = config
        self.client = Session(profile_name=config.profile_name,region_name=config.region).client('ec2')
        self.descParser = DescribeInstancesParser()
        self.master = None
        self.slaves = []
        self.updateInstances()
    
    ## requests describe instances and updates master/slaves information    
    def updateInstances(self):
        filter_cond = [{"Name":"tag:TaskID","Values":[self.taskID]}]
        self.descParser.setResponse(self.client.describe_instances(Filters = filter_cond))
        details = self.descParser.listDetails();
        master = [i for i in details if i["Role"]=="Master"]
        self.master = master[0] if master else None
        self.slaves = [i for i in details if i["Role"]=="Slave"]
    
    ## list master/ slaves info
    def listInstances(self):
        return self.descParser.listDetails()
    
    ## internal use, start instances with given ID list.
    def startInstances(self,IDs,verbose):
        res = self.client.start_instances(InstanceIds=IDs) if IDs else "No instance in the list"
        self.updateInstances()
        if verbose or verbose is None and self.verboseOrNot:
            print(json.dumps(res,indent=2))
        return res
    
    ## internal use, stop a list of intances    
    def stopInstances(self,IDs,verbose):
        res = self.client.stop_instances(InstanceIds=IDs) if IDs else "No instance in the list"
        self.updateInstances()
        if verbose or verbose is None and self.verboseOrNot:
            print(json.dumps(res,indent=2))
        return res
    
    ## internal use, stop a list of instances
    def terminateInstances(self,IDs,verbose):
        res = self.client.terminate_instances(InstanceIds=IDs) if IDs else "No instance in the list"
        self.updateInstances()
        if verbose or verbose is None and self.verboseOrNot:
            print(json.dumps(res,indent=2))
        return res
    
    ## internal use, lanuch a number of instances, with the same image ID, instance type, security groups and area
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
        if(self.master):
            self.startInstances([self.master['InstanceId']if self.master else None],verbose)
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
    
    ## create a master node if don't have one.
    #  by default image with lightdm which allows instance be accessed by remote desktop
    #  then tag this node with "name":"Master"
    def addMaster(self,LXDM=True,instType=None,verbose=None):
        if not self.master:
            imageID = self.config.ami["LXDM"] if LXDM else self.config.ami["basic"]
            instType = self.config.instType["master"] if not instType else instType
            res = self.creatInstances(imageID,1,instType,self.config.securityGroups,self.config.zone,verbose)
            ID = res['Instances'][0]["InstanceId"]
            self.client.create_tags(Resources = [ID], Tags = [{'Key': 'Name', 'Value': 'Master'},{'Key':"TaskID","Value":self.taskID}])  
            self.updateInstances()
            return ID
        else :return "Running Master, Terminate it before lanuch a new one"
    
    ## create a number of slaves 
    #  by default image is basic which only have jmeter and java installed
    #  then tag this node with "name":"Slave" 
    def addSlaves(self,num,LXDM=False,instType=None,verbose=None):
        imageID = self.config.ami["LXDM"] if LXDM else self.config.ami["basic"]
        instType = self.config.instType["slave"] if not instType else instType
        res = self.creatInstances(imageID,num,instType,self.config.securityGroups,self.config.zone,verbose)
        IDs = [i["InstanceId"] for i in res['Instances']]
        self.client.create_tags(Resources = IDs, Tags = [{'Key': 'Name', 'Value': 'Slave'},{'Key':"TaskID","Value":self.taskID}]) 
        self.updateInstances()
        return IDs
