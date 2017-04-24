from .Config import Config


# configuration class for instance manager


class AWSConfig(Config):
    # passing config dictionary to init
    #  used as parameter to instance manager init.
    def __init__(self, **kargs):
        self.session_param={
            "region_name":kargs["region"],
            "aws_access_key_id":kargs["aws_access_key_id"],
            "aws_secret_access_key":kargs["aws_secret_access_key"]
        }
        self.ami = kargs["ami"]
        self.securityGroups = kargs["security_groups"]
        self.zone = kargs["zone"]
        self.instType = kargs["InstType"]
        self.role = kargs["role"]
        self.s3_role = kargs["s3_role"]
        self.s3bucket = kargs["s3_bucket"]
