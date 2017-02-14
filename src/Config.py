class Config(object):
    pass

class AWSConfig(Config):
    def __init__(self, **kargs):
        self.profile_name = kargs["profile_name"]
        self.region = kargs["region"]
        self.ami= kargs["ami"]
        self.securityGroups = kargs["security_groups"]
        self.zone = kargs["zone"]
        self.InstType = kargs["InstType"]
    