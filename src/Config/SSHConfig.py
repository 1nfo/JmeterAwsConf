from .Config import Config


#  configuration class for a ssh connection, \
#  passing to connection __init__ function.


class SSHConfig(Config):
    #  init the class, by taking hosting name and a dict
    #  which contains AWS key file path and username for ssh connection
    def __init__(self, hostname="", **kargs):
        self.param = {
            "key_filename":kargs["pemFilePath"],
            "hostname":hostname,
            "username":kargs["username"]
        }
        self.instance_home = kargs["instance_home"]

    #  since the whole cluster share one key file,
    #  the only thing different for each connection is IP addr.
    #  this one MIGHT BE useful
    def updateHostname(self, hostname):
        self.hostname = hostname
