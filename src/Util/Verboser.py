class Verboser(object):
    def __init__(self):
        self.verboseOrNot = False

    # make Verboser NOT to print responses or results to the stdin
    def mute(self):
        self.verboseOrNot = False

    # make Verboser actively print responses and results to the stdin
    def verbose(self):
        self.verboseOrNot = True

    def print(self, output, end="\n", verbose=None):
        if verbose or verbose is None and self.verboseOrNot:
            print(output, end=end)
