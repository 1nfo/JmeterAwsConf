## not import by __init__.py,
#  so not visible(abstract class)

from ..util import Verboser

class Manager(Verboser):
    def __init__(self):
        Verboser.__init__(self)