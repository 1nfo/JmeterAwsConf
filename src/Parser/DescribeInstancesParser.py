from .ResponseParser import *

TAG_TASKID = "__JAC_TASKID__"
TAG_TASKNAME = "__JAC_TASKNAME__"
TAG_NAME = "Name"
TAGVAL_NAME = "JAC_"
TAG_ROLE = "__JAC_ROLE__"


# responsible for parsing describe instances response
class DescribeInstancesParser(ResponseParser):
    # sg (security group) is for filtering nodes
    def __init__(self, reponse=None):
        ResponseParser.__init__(self, reponse)

    def setResponse(self, response):
        self.response = response

    def _getPrivateIp(self, i):
        if not i["NetworkInterfaces"]: return "N/A"
        return i["NetworkInterfaces"][0].get("PrivateIpAddress")

    def _getPublicIp(self, i):
        if not i["NetworkInterfaces"]: return "N/A"
        return i["NetworkInterfaces"][0].get("Association", {"PublicIp": "N/A"})["PublicIp"]

    def _getSecurityGroups(self, i):
        return [j["GroupName"] for j in i["SecurityGroups"]]

    def _getTagName(self, i):
        for j in i:
            if j["Key"] == TAG_ROLE: return j["Value"]
        return "N/A"

    # return list of instances
    def listDetails(self):
        instances = []
        for i in self.response["Reservations"]:
            for j in i["Instances"]:
                instances.append(j)
        return [
            {
                "InstanceId": i["InstanceId"],
                "PublicIp": self._getPublicIp(i),
                "PrivateIpAddress": self._getPrivateIp(i),
                "Role": self._getTagName(i.get("Tags", [])),
                "State": i.get("State", [{"Value": "N/A"}])
            }
            for i in instances if i["State"]["Name"] not in ["terminated", "shutting-down"]
            ]

    def _getTaskIDs(self, i):
        for j in i:
            if j["Key"] == TAG_TASKID: return j["Value"]

    def listTaskIDs(self):
        instances = []
        for i in self.response["Reservations"]:
            for j in i["Instances"]:
                instances.append(j)
        return list(set([self._getTaskIDs(i.get("Tags", [])) for i in instances if
                         i["State"]["Name"] not in ["terminated", "shutting-down"]]))
