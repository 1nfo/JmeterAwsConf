from .Manager import Manager
from .BotoSession import BotoSession

class ResultManager(Manager):
    def __init__(self,config):
        Manager.__init__(self)
        BotoSession.__init__(self,config)

    def __getattr__(self,item):
        if item == "client":
            sess = self.newSess(self.clusterName)
            ret = self.__dict__[item] = sess.client("s3")
            return ret
        else:
            raise AttributeError

    def setInfo(self,user="",clusterName=""):
        self.user = user
        self.clusterName = clusterName

    def list(self,path):
        res = self.client.list_objects(Bucket=self.config.s3bucket,Prefix=self.user+"/")
        return [i["Key"] for i in res["Contents"]]