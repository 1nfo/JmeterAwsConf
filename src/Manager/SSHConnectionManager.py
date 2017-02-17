from .Manager import Manager
        
class SSHConnectionManager(Manager):
    def __init__(self,masterConn=None,slavesConn={}):
        self.updateConnections(masterConn,slavesConn)
        self.verboseOrNot = True
    
    def updateConnections(self,masterConn,slavesConn):
        self.masterConn = masterConn
        self.slavesConn = slavesConn

    def connectMaster(self):
        self.masterConn.connect()
        
    def closeMaster(self):
        self.masterConn.close()
        
    def connectSlaves(self,IDs=[]):
        if not IDs: IDs = list(self.slavesConn.keys())
        for ID in IDs:
            self.slavesConn[ID].connect()
    
    def closeSlaves(self,IDs=[]):
        if not IDs: IDs = list(self.slavesConn.keys())
        for ID in IDs:
            self.slavesConn[ID].close()
            
    def cmdMaster(self,cmd,verbose=None):
        transport = self.masterConn.ssh.get_transport()
        if not transport or not transport.is_active(): print("Not active connection")
        else: self.masterConn.cmd(cmd, verbose if verbose is not None else self.verboseOrNot)
    
    def cmdSlaves(self,cmd,IDs=[],verbose=None):
        verbose = verbose if verbose is not None else self.verboseOrNot
        transport = self.masterConn.ssh.get_transport()
        if not IDs: IDs = [k for k in self.slavesConn if transport and transport.is_active()]
        # if cmd is list, cmd are mapped to different slaves
        if type(cmd)==list:
            n = len(cmd) if len(cmd)<len(IDs) else len(IDs)
            for i in range(n):
                self.slavesConn[IDs[i]].cmd(cmd[i],verbose)
        # if dict, mapping according to instance's id
        if type(cmd)==dict:
            if not IDs: print("parameter 'IDs' is specified but ignored since cmd included it")
            for ID in cmd:
                if not ID in self.slavesConn.keys(): print('%s is not found in SSH connection manager'%ID)
                else:
                    self.slavesConn[ID].cmd(cmd[ID],verbose)
        # if str, all slaves exec the same one
        if type(cmd)==str:
            if not IDs: print("No active connection")
            else:
                for ID in IDs:
                    self.slavesConn[ID].cmd(cmd,verbose)