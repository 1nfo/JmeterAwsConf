import json
from ..Parser import *
from .Manager import Manager
from .BotoSession import BotoSession


# instance manager is responsible to provide wrapped API from SDK
#  to control master and slaves' lifecycle
class InstanceManager(Manager,BotoSession):
    # init with AWSConfig class
    def __init__(self, config):
        Manager.__init__(self)
        BotoSession.__init__(self,config)
        self.descParser = DescribeInstancesParser()
        self.clusterName = ""
        self.clusterID = ""
        self.clusterDesc = ""
        self.master = None
        self.slaves = []
        self.user=""

    def __getattr__(self,item):
        if item in ('client', 'iam'):
            # sess = Session(**config.session_param).client('sts')
            # tmp = sess.assume_role(RoleArn=self.config.role,RoleSessionName="session_"+self.clusterName)["Credentials"]
            # ret = Session(aws_access_key_id=tmp["AccessKeyId"], aws_secret_access_key=tmp["SecretAccessKey"],
                                #                aws_session_token=tmp["SessionToken"], region_name=self.config.session_param["region_name"])
            sess = self.newSess(self.clusterName)
            if item == "client":
                ret = self.__dict__[item] = sess.client("ec2")
            elif item == "iam":
                ret = self.__dict__[item] = sess.client("iam")
            return ret
        else:
            raise AttributeError("No attribute %s"%item)


    # set cluster name and id
    def setCluster(self, clusterName, clusterID=None, user=None):
        if clusterName and clusterID is None:
            res = self.getDupClusterIds(clusterName)
            if len(res) > 0:
                msg = "Found multiple clusters named %s, please try a new name or resume." % clusterName
                raise DupClusterException(msg)
        self.clusterName = clusterName
        self.clusterID = clusterID if clusterID else res[0] if res else self._genID(clusterName,user)
        self.master = None
        self.slaves = []
        self.user = user
        self.updateInstances()

    # set cluster description
    def setClusterDesc(self, desc):
        self.clusterDesc = desc

    # get cluster descrition tag
    def getClusterDesc(self):
        filter_cond = [{TAG_NAME: "tag:" + TAG_CLUSTERID, "Values": [self.clusterID]},{TAG_NAME: "tag:" + TAG_ROLE, "Values": ["Master"]}]
        self.descParser.setResponse(self.client.describe_instances(Filters=filter_cond))
        self.clusterDesc = self.descParser.getClusterDesc()
        return self.clusterDesc

    # get ClusterID set within JAC node on aws
    def getDupClusterIds(self, clusterName=None):
        if clusterName:
            filter_cond = [{TAG_NAME: "tag:" + TAG_CLUSTERNAME, "Values": [clusterName]}]
        else:
            filter_cond = [{TAG_NAME: "tag:" + TAG_ROLE, "Values": ["Master"]}]
        self.descParser.setResponse(self.client.describe_instances(Filters=filter_cond))
        return self.descParser.listClusterIDs()

    # check all nodes is available to connection
    def allInitialized(self):
        IDs = [i["InstanceId"] for i in self.listInstances()]
        res = self.client.describe_instance_status(InstanceIds=IDs)['InstanceStatuses']
        index = str([i["InstanceStatus"]['Details'] for i in res]).find("initializing")
        return True if res and index < 0 else False

    def _genID(self, name, user):
        from ..Util import now
        return "%s_%s_%s" % (name, user, now())

    # requests describe instances and updates master/slaves information
    def updateInstances(self):
        filter_cond = [{TAG_NAME: "tag:" + TAG_CLUSTERID, "Values": [self.clusterID]}]
        self.descParser.setResponse(self.client.describe_instances(Filters=filter_cond))
        details = self.descParser.listDetails();
        master = [i for i in details if i["Role"] == "Master"]
        self.master = master[0] if master else None
        self.slaves = [i for i in details if i["Role"] == "Slave"]
        self.print("Nodes: %d maseter and %d slave(s) under CLUSTER %s" % (
        1 if self.master else 0, len(self.slaves), self.clusterName))

    # list master/ slaves info
    def listInstances(self):
        filter_cond = [{TAG_NAME: "tag:" + TAG_CLUSTERID, "Values": [self.clusterID]}]
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
    def creatInstances(self, ImageID, num, InstanceType, SecurityGroups, area, verbose, role={}):
        res = self.client.run_instances(ImageId=ImageID, MinCount=num, MaxCount=num, \
                                        InstanceType=InstanceType, SecurityGroups=SecurityGroups, \
                                        Placement={"AvailabilityZone": area},\
                                        IamInstanceProfile=role)
        self.print(res, verbose)
        return res

    def startMaster(self, verbose=None):
        if self.master:
            self.startInstances([self.master['InstanceId']], verbose)
            # self.iam.add_role_to_instance_profile(InstanceProfileName='string',RoleName=self.config.s3role)

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
    def addMaster(self, instType=None, verbose=None):
        if not self.master:
            imageID = self.config.ami["master"]
            instType = self.config.instType["master"] if not instType else instType
            res = self.creatInstances(imageID, 1, instType, self.config.securityGroups, self.config.zone, verbose, role=self.config.s3_role)
            ID = res['Instances'][0]["InstanceId"]
            self.client.create_tags(Resources=[ID], Tags=[{'Key': TAG_NAME, 'Value': TAGVAL_NAME + self.clusterName},
                                                          {'Key': TAG_ROLE, 'Value': 'Master'},
                                                          {'Key': TAG_CLUSTERNAME, "Value": self.clusterName},
                                                          {'Key': TAG_CLUSTERID, "Value": self.clusterID},
                                                          {'Key': TAG_CLUSTERDESC, "Value": self.clusterDesc},
                                                          {"Key": TAG_USER, "Value": self.user}])
            self.updateInstances()
            return ID
        else:
            return "Running Master, Terminate it before lanuch a new one"

    # create a number of slaves
    #  by default image is basic which only have jmeter and java installed
    #  then tag this node with "name":"Slave"
    def addSlaves(self, num, instType=None, verbose=None):
        imageID = self.config.ami["slave"]
        instType = self.config.instType["slave"] if not instType else instType
        res = self.creatInstances(imageID, num, instType, self.config.securityGroups, self.config.zone, verbose)
        IDs = [i["InstanceId"] for i in res['Instances']]
        self.client.create_tags(Resources=IDs, Tags=[{'Key': TAG_NAME, 'Value': TAGVAL_NAME + self.clusterName},
                                                     {'Key': TAG_ROLE, 'Value': 'Slave'},
                                                     {'Key': TAG_CLUSTERNAME, "Value": self.clusterName},
                                                     {'Key': TAG_CLUSTERID, "Value": self.clusterID},
                                                     {"Key": TAG_USER, "Value": self.user}])
        self.updateInstances()
        return IDs


class DupClusterException(Exception):
    pass
