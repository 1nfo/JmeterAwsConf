import json
from boto3 import Session
from ..Parser import *
from .Manager import Manager


# instance manager is responsible to provide wrapped API from SDK
#  to control master and slaves' lifecycle
class InstanceManager(Manager):
    # init with AWSConfig class
    def __init__(self, config):
        Manager.__init__(self)
        self.config = config
        self.descParser = DescribeInstancesParser()
        self.taskName = ""
        self.taskID = ""
        self.taskDesc = ""
        self.master = None
        self.slaves = []

    def __getattr__(self,item):
        if item == 'client':
            config = self.config
            ret = self.__dict__[item] = Session(profile_name=config.profile_name, region_name=config.region).client('ec2')
            return ret
        else:
            raise AttributeError

    # set task name and id
    def setTask(self, taskName, taskID):
        if taskName and taskID is None:
            res = self.getDupTaskIds(taskName)
            if len(res) > 0:
                msg = "Found multiple tasks named %s, please try a new name or resume." % taskName
                raise DupTaskException(msg)
        self.taskName = taskName
        self.taskID = taskID if taskID else res[0] if res else self._genID(taskName)
        self.master = None
        self.slaves = []
        self.updateInstances()

    # set task description
    def setTaskDesc(self, desc):
        self.taskDesc = desc

    # get task descrition tag
    def getTaskDesc(self):
        filter_cond = [{TAG_NAME: "tag:" + TAG_TASKID, "Values": [self.taskID]},{TAG_NAME: "tag:" + TAG_ROLE, "Values": ["Master"]}]
        self.descParser.setResponse(self.client.describe_instances(Filters=filter_cond))
        self.taskDesc = self.descParser.getTaskDesc()
        return self.taskDesc

    # get TaskID set within JAC node on aws
    def getDupTaskIds(self, taskName=None):
        if taskName:
            filter_cond = [{TAG_NAME: "tag:" + TAG_TASKNAME, "Values": [taskName]}]
        else:
            filter_cond = [{TAG_NAME: "tag:" + TAG_ROLE, "Values": ["Master"]}]
        self.descParser.setResponse(self.client.describe_instances(Filters=filter_cond))
        return self.descParser.listTaskIDs()

    # check all nodes is available to connection
    def allInitialized(self):
        IDs = [i["InstanceId"] for i in self.listInstances()]
        res = self.client.describe_instance_status(InstanceIds=IDs)['InstanceStatuses']
        index = str([i["InstanceStatus"]['Details'] for i in res]).find("initializing")
        return True if res and index < 0 else False

    def _genID(self, name):
        import os, time
        return "%s_%s@%s_%s" % (name, os.getlogin(), os.uname()[1], time.strftime("%Y%m%d_%H%M%S%z"))

    # requests describe instances and updates master/slaves information
    def updateInstances(self):
        filter_cond = [{TAG_NAME: "tag:" + TAG_TASKID, "Values": [self.taskID]}]
        self.descParser.setResponse(self.client.describe_instances(Filters=filter_cond))
        details = self.descParser.listDetails();
        master = [i for i in details if i["Role"] == "Master"]
        self.master = master[0] if master else None
        self.slaves = [i for i in details if i["Role"] == "Slave"]
        self.print("Nodes: %d maseter and %d slave(s) under TASK %s" % (
        1 if self.master else 0, len(self.slaves), self.taskName))

    # list master/ slaves info
    def listInstances(self):
        filter_cond = [{TAG_NAME: "tag:" + TAG_TASKID, "Values": [self.taskID]}]
        self.descParser.setResponse(self.client.describe_instances(Filters=filter_cond))
        return self.descParser.listDetails()

    # internal use, start instances with given ID list.
    def startInstances(self, IDs, verbose):
        res = self.client.start_instances(InstanceIds=IDs) if IDs else "No instance in the list"
        self.print("Start instances:" + str(IDs), verbose)
        self.print(json.dumps(res, indent=2), verbose)
        self.updateInstances()
        return res

    # internal use, stop a list of intances
    def stopInstances(self, IDs, verbose):
        res = self.client.stop_instances(InstanceIds=IDs) if IDs else "No instance in the list"
        self.print("Stop instances:" + str(IDs), verbose)
        self.print(json.dumps(res, indent=2), verbose)
        self.updateInstances()
        return res

    # internal use, stop a list of instances
    def terminateInstances(self, IDs, verbose):
        res = self.client.terminate_instances(InstanceIds=IDs) if IDs else "No instance in the list"
        self.print("Terminate instances:" + str(IDs), verbose)
        self.print(json.dumps(res, indent=2), verbose)
        self.updateInstances()
        return res

    # internal use, lanuch a number of instances, with the same image ID, instance type, security groups and area
    def creatInstances(self, ImageID, num, InstanceType, SecurityGroups, area, verbose):
        res = self.client.run_instances(ImageId=ImageID, MinCount=num, MaxCount=num, \
                                        InstanceType=InstanceType, SecurityGroups=SecurityGroups, \
                                        Placement={"AvailabilityZone": area})
        self.print(res, verbose)
        return res

    def startMaster(self, verbose=None):
        if self.master:
            self.startInstances([self.master['InstanceId']], verbose)

    def stopMaster(self, verbose=None):
        if self.master:
            self.stopInstances([self.master['InstanceId']], verbose)

    def startSlaves(self, verbose=None):
        self.startInstances([i['InstanceId'] for i in self.slaves if i["State"] != "stopping"], verbose)

    def stopSlaves(self, verbose=None):
        self.stopInstances([i['InstanceId'] for i in self.slaves if i["State"] != "stopping"], verbose)

    def startAll(self, verbose=None):
        self.startMaster(verbose)
        self.startSlaves(verbose)

    def stopAll(self, verbose=None):
        self.stopMaster(verbose)
        self.stopSlaves(verbose)

    def terminateMaster(self, verbose=None):
        if (self.master):
            return self.terminateInstances([self.master["InstanceId"]], verbose)
        else:
            return "No master running"

    def terminateSlaves(self, verbose=None):
        return self.terminateInstances([i["InstanceId"] for i in self.slaves], verbose)

    # create a master node if don't have one.
    #  by default image with lightdm which allows instance be accessed by remote desktop
    #  then tag this node with "name":"Master"
    def addMaster(self, LXDM=True, instType=None, verbose=None):
        if not self.master:
            imageID = self.config.ami["LXDM"] if LXDM else self.config.ami["basic"]
            instType = self.config.instType["master"] if not instType else instType
            res = self.creatInstances(imageID, 1, instType, self.config.securityGroups, self.config.zone, verbose)
            ID = res['Instances'][0]["InstanceId"]
            self.client.create_tags(Resources=[ID], Tags=[{'Key': TAG_NAME, 'Value': TAGVAL_NAME + self.taskName},
                                                          {'Key': TAG_ROLE, 'Value': 'Master'},
                                                          {'Key': TAG_TASKNAME, "Value": self.taskName},
                                                          {'Key': TAG_TASKID, "Value": self.taskID},
                                                          {'Key': TAG_TASKDESC, "Value": self.taskDesc}])
            self.updateInstances()
            return ID
        else:
            return "Running Master, Terminate it before lanuch a new one"

    # create a number of slaves
    #  by default image is basic which only have jmeter and java installed
    #  then tag this node with "name":"Slave"
    def addSlaves(self, num, LXDM=False, instType=None, verbose=None):
        imageID = self.config.ami["LXDM"] if LXDM else self.config.ami["basic"]
        instType = self.config.instType["slave"] if not instType else instType
        res = self.creatInstances(imageID, num, instType, self.config.securityGroups, self.config.zone, verbose)
        IDs = [i["InstanceId"] for i in res['Instances']]
        self.client.create_tags(Resources=IDs, Tags=[{'Key': TAG_NAME, 'Value': TAGVAL_NAME + self.taskName},
                                                     {'Key': TAG_ROLE, 'Value': 'Slave'},
                                                     {'Key': TAG_TASKNAME, "Value": self.taskName},
                                                     {'Key': TAG_TASKID, "Value": self.taskID}])
        self.updateInstances()
        return IDs


class DupTaskException(Exception):
    pass
