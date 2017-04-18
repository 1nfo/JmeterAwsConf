import sys, io


class Redirector:
    def __init__(self, buffer=None, pauseFunc=None):
        self.buff = buffer if buffer else io.StringIO()
        self.pauseFunc = pauseFunc
        self.sids = set([])

    # nested stream, sys.stdout could be a Redirector as well.
    def __enter__(self):
        self.stdout = sys.stdout
        sys.stdout = self
        return self

    def __exit__(self, *arg):
        sys.stdout = self.stdout
        self.stdout = None

    def write(self, output):
        sys.__stdout__.write(output)
        self.buff.write(output)
        if self.pauseFunc: self.pauseFunc()

    def flush(self):
        ret = self.buff.getvalue()
        self.buff.seek(0)
        self.buff.truncate(0)
        return ret

    def add(self,sid):
        self.sids.add(sid)

    def remove(self,sid):
        self.sids.remove(sid)


## test
if __name__ == "__main__":
    ## test
    print("redirector start:")
    with Redirector() as re:
        print("something")

        print("now flushing")

        re.stdout.write(re.flush())

        print("flush done")

        print("flush again")

        re.stdout.write(re.flush())

    print("redirector done")
