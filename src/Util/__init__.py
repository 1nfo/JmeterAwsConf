from .Redirector import Redirector
from .Verboser import Verboser
from .JMX import JMX
import time

def now():
    return time.strftime("%Y%m%d_%H%M%S",time.gmtime())
