from .Config import Config


# configuration class for instance manager


class AWSConfig(Config):
    # passing config dictionary to init
    #  used as parameter to instance manager init.
    def __init__(self, **kargs):
        self.profile_name = kargs["profile_name"]
        self.region = kargs["region"]
        self.ami = kargs["ami"]
        self.securityGroups = kargs["security_groups"]
        self.zone = kargs["zone"]
        self.instType = kargs["InstType"]
