from paramiko import SSHClient, AutoAddPolicy
from .Connection import *
from ..Util import Verboser
import os


#  connection by ssh between manager and ec2 instance
#  cmd can be passed to the remote machines by this connection


class SSHConnection(Connection, Verboser):
    def __init__(self, config):
        Connection.__init__(self)
        Verboser.__init__(self)
        self.verbose()
        self.__dict__.update(config.__dict__)
        self.ssh = SSHClient()

    def updateHostname(self, hostname):
        self.param["hostname"] = hostname

    def connect(self):
        self.ssh.set_missing_host_key_policy(AutoAddPolicy())
        self.ssh.connect(**self.param)

    # if verbose is true, the stdout stream won't close until the remote machine finishes cmd.
    def cmd(self, cmd, verbose):
        _, stdout, stderr = self.ssh.exec_command(cmd)
        if not verbose: return
        if cmd:
            self.print("\n%s@%s $" % (self.param["username"], self.param["hostname"]), end='')
            self.print(cmd + "\n>>> ", end="")
        if stdout:
            for i in stdout:
                self.print(i.replace("\n", "\n>>> "), end="")
        if stderr:
            for i in stderr:
                self.print(i.replace("\n", "\n>>> "), end="")
        print(" ")

    def close(self):
        self.ssh.close()

    def put(self,src,des,callback=None):
        sftp = self.ssh.open_sftp()
        sftp.chdir(self.instance_home)
        if os.path.isdir(src):
            for s in os.listdir(src):
                if os.path.isdir(s):
                    pass
                elif not s.startswith("."):
                    sftp.put(os.path.join(src,s),os.path.join(des,s),callback)
                    self.print(s,verbose=False)
        else:
            sftp.put(src,os.path.join(des,src.split("/")[-1]),callback)
        sftp.chdir()
        sftp.close()
