class Config(object):
    pass

class AWSConfig(Config):
    def __init__(self, **kargs):
        self.profile_name = kargs["profile_name"]
        self.region = kargs["region"]
        self.ami= kargs["ami"]
        self.securityGroups = kargs["security_groups"]
        self.zone = kargs["zone"]
        self.instType = kargs["InstType"]

class SSHConfig(Config):
    def __init__(self,hostname="",**kargs):
        self.key_filename = kargs["pemFilePath"]
        self.hostname = hostname
        self.username = kargs["username"]

    def updateHostname(self,hostname):
        self.hostname = hostname
    