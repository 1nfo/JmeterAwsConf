from paramiko import SSHClient, AutoAddPolicy 
from .Connection import *

class SSHConnection(Connection):
    def __init__(self,config):
        self.param = config.__dict__;
        self.ssh = SSHClient()
    
    def updateHostname(self,hostname):
        self.param["hostname"] = hostname
    
    def connect(self):
        self.ssh.set_missing_host_key_policy(AutoAddPolicy()) 
        self.ssh.connect(**self.param)
        
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