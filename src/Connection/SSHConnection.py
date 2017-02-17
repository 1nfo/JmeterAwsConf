from paramiko import SSHClient, AutoAddPolicy 
from .Connection import *

## connection by ssh between manager and ec2 instance
#  cmd can be passed to the remote machines by this connection
class SSHConnection(Connection):
    def __init__(self,config):
        self.param = config.__dict__;
        self.ssh = SSHClient()
    
    def updateHostname(self,hostname):
        self.param["hostname"] = hostname
    
    def connect(self):
        self.ssh.set_missing_host_key_policy(AutoAddPolicy()) 
        self.ssh.connect(**self.param)
    
    # if verbose is true, the stdout stream won't close until the remote machine finishes cmd.   
    def cmd(self,cmd,verbose):
        stdin, stdout, stderr = self.ssh.exec_command(cmd)
        if not verbose: return
        if cmd:
            print("\n%s@%s $"%(self.param["username"],self.param["hostname"]),end='')
            print(cmd+"\n>>> ",end="")
        if stdout:
            for i in stdout:
                print(i.replace("\n","\n>>> "),end="")        
        if stderr:
            for i in stderr:
                print(i.replace("\n","\n>>> "),end="")
    
    def close(self):
        self.ssh.close()