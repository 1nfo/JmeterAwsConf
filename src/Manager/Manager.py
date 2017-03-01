## not import by __init__.py,
#  so not visible(abstract class)
#  add string buffer from redirect the print result.


class Manager(object):
    def __init__(self):
        self.verboseOrNot = True

    ## make manager NOT to print responses or results to the stdin
    def mute(self):
        self.verboseOrNot = False
    
    ## make manager actively print responses and results to the stdin
    def verbose(self):
        self.verboseOrNot = True

    def print(self,output,verbose=None):
        if verbose or verbose is None and self.verboseOrNot:
                print(output)