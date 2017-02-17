from .ResponseParser import *

class DescribeInstancesParser(ResponseParser):
    def __init__(self,reponse=None,sg = []):
        ResponseParser.__init__(self,reponse)
        self.sgIncluded = sg
    
    def setResponse(self,response):
        self.response = response
    
    def _getPrivateIp(self,i):
        if not i["NetworkInterfaces"]: return "N/A"
        return i["NetworkInterfaces"][0].get("PrivateIpAddress")
    
    def _getPublicIp(self,i):
        if not i["NetworkInterfaces"]: return "N/A"
        return i["NetworkInterfaces"][0].get("Association",{"PublicIp":"N/A"})["PublicIp"] 
    
    def _getSecurityGroups(self,i):
        return [j["GroupName"] for j in i["SecurityGroups"]]
    
    def _inSG(self, A):
        return any(i in A for i in self.sgIncluded)
    
    def listDetails(self):
        instances = []
        for i in self.response["Reservations"]:
            for j in i["Instances"]:
                instances.append(j)
        return [{
                    "InstanceId":i["InstanceId"],
                    "PublicIp":self._getPublicIp(i),
                    "PrivateIpAddress":self._getPrivateIp(i),
                    "Tags":i.get("Tags",[{"Value":"N/A"}]),
                    "State":i.get("State",[{"Value":"N/A"}])
                }  
                for i in  instances
                if (not self.sgIncluded or self._inSG(self._getSecurityGroups(i))) \
                    and i["State"]["Name"] !="terminated"
               ]
               