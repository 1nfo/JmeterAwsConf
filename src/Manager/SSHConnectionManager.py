from .Manager import Manager


#  connect to cluster by ssh and execute commands
class SSHConnectionManager(Manager):
    def __init__(self, masterConn=None, slavesConn={}):
        Manager.__init__(self)
        self.updateConnections(masterConn, slavesConn)

    #  every times master / slave public ip changed,
    #  the connection config need to be updated
    def updateConnections(self, masterConn, slavesConn):
        self.masterConn = masterConn
        self.slavesConn = slavesConn

    def connectMaster(self):
        self.masterConn.connect()

    def closeMaster(self):
        self.masterConn.close()

    #  connect slaves whoes ID is in the IDs list,
    #  if IDs is not specified or none, connect all slaves.
    def connectSlaves(self, IDs=None):
        if IDs is None: IDs = list(self.slavesConn.keys())
        for ID in IDs:
            self.slavesConn[ID].connect()

    #  close slaves whoes ID is in the IDs list,
    #  if IDs is not specified or none, connect all slaves.
    #  issue: what if connection is not active?
    def closeSlaves(self, IDs=None):
        if IDs is None: IDs = list(self.slavesConn.keys())
        for ID in IDs:
            self.slavesConn[ID].close()

    #  give master a command to execute
    def cmdMaster(self, cmd, verbose=None):
        transport = self.masterConn.ssh.get_transport()
        if not transport or not transport.is_active():
            self.print("Not active connection")
        else:
            self.masterConn.cmd(cmd, verbose if verbose is not None else self.verboseOrNot)

    #  give slaves command(s) to execute
    #  if cmd is a string, then all slaves receive the same cmd,
    #  if it is a list:
    #           1. if list length > # of active connections, ignore extra cmds
    #           2. otherwise, find the top n slaves and assign them cmds in the list side by sid
    #  if it is a dict, then key is instance ID, value is cmd for that instance
    def cmdSlaves(self, cmd, IDs=None, verbose=None):
        verbose = verbose if verbose is not None else self.verboseOrNot
        if not IDs: IDs = [k for k in self.slavesConn
                           if self.slavesConn[k].ssh.get_transport() \
                           and self.slavesConn[k].ssh.get_transport().is_active()
                           ]
        # if cmd is list, cmd are mapped to different slaves
        if type(cmd) == list:
            n = len(cmd) if len(cmd) < len(IDs) else len(IDs)
            for i in range(n):
                self.slavesConn[IDs[i]].cmd(cmd[i], verbose)
        # if dict, mapping according to instance's id
        if type(cmd) == dict:
            if not IDs:
                self.print("parameter 'IDs' is specified but ignored since cmd included it")
            for ID in cmd:
                if not ID in self.slavesConn.keys():
                    self.print('%s is not found in SSH connection manager' % ID)
                else:
                    self.slavesConn[ID].cmd(cmd[ID], verbose)
        # if str, all slaves exec the same one
        if type(cmd) == str:
            if not IDs:
                self.print("No active connection")
            else:
                for ID in IDs:
                    self.slavesConn[ID].cmd(cmd, verbose)


    def putMaster(self,src,des,callback=None,verbose=None):
        self.print("Upload to master",verbose=verbose)
        self.masterConn.put(src,des,callback)


    def putSlaves(self,src,des,callback=None,verbose=None):
        for i,slave in enumerate(self.slavesConn.values()):
            self.print("Upload to slave #%d"%i,verbose=verbose)
            slave.put(src,des,callback)


    def connectAll(self):
        self.connectMaster()
        self.connectSlaves()


    def closeAll(self):
        self.closeMaster()
        self.closeSlaves()


    def putAll(self,src,des,callback=None,verbose=None):
        self.putMaster(src,des,callback=None,verbose=verbose)
        self.putSlaves(src,des,callback=None,verbose=verbose)


    def cmdAll(self,cmd):
        self.cmdMaster(cmd)
        self.cmdSlaves(cmd)
