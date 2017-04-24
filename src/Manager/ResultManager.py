from .Manager import Manager
from .BotoSession import BotoSession

class ResultManager(Manager,BotoSession):
    def __init__(self,config):
        Manager.__init__(self)
        BotoSession.__init__(self,config)

    def __getattr__(self,item):
        if item == "client":
            sess = self.newSess(self.user)
            ret = self.__dict__[item] = sess.client("s3")
            return ret
        else:
            raise AttributeError("No attribute %s"%item)

    def setUser(self,user):
        self.user = user

    def list(self):
        res = self.client.list_objects(Bucket=self.config.s3bucket,Prefix=self.user+"/"+"summary/")
        return [i["Key"] for i in res["Contents"]]

    def get(self,path):
        body = self.client.get_object(Bucket=self.config.s3bucket,Key=path)["Body"]
        return body.read().decode('utf-8')