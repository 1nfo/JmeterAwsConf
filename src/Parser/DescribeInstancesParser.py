from .ResponseParser import *

TAG_CLUSTERID = "__JAC_CLUSTERID__"
TAG_CLUSTERNAME = "__JAC_CLUSTERNAME__"
TAG_NAME = "Name"
TAGVAL_NAME = "JAC_"
TAG_ROLE = "__JAC_ROLE__"
TAG_CLUSTERDESC = "__JAC_CLUSTERDESC__"
TAG_USER = "__JAC_USER__"


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

    def _getClusterIDs(self, i):
        for j in i:
            if j["Key"] == TAG_CLUSTERID: return j["Value"]

    def _getClusterDesc(self,i):
        for j in i:
            if j["Key"] == TAG_CLUSTERDESC: return j["Value"]
        return ""

    def _getUser(self,i):
        for j in i:
            if j["Key"] == TAG_USER: return j["Value"]
        return ""

    def listClusterIDs(self):
        instances = []
        for i in self.response["Reservations"]:
            for j in i["Instances"]:
                instances.append(j)
        return list(set([
                        (self._getClusterIDs(i.get("Tags", [])), self._getClusterDesc(i.get("Tags",[])), self._getUser(i.get("Tags",[])))
                        for i in instances
                        if i["State"]["Name"] not in ["terminated", "shutting-down"]
                    ]))

    def getClusterDesc(self):
        instances = []
        for i in self.response["Reservations"]:
            for j in i["Instances"]:
                instances.append(j)
        tags = instances[0]["Tags"]
        return self._getClusterDesc(tags)
