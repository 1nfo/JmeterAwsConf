from boto3 import Session


class BotoSession(object):
    def __init__(self,config):
        self.config = config

    def newSess(self,sessionName):
        sts = Session(**self.config.session_param).client('sts')
        tmp = sts.assume_role(RoleArn=self.config.role,RoleSessionName="session_"+sessionName)["Credentials"]
        ret = Session(aws_access_key_id=tmp["AccessKeyId"], aws_secret_access_key=tmp["SecretAccessKey"],
                                                aws_session_token=tmp["SessionToken"], region_name=self.config.session_param["region_name"])
        return ret
