# not import by __init__.py,
#  so not visible(abstract class)


class ResponseParser(object):
    def __init__(self, response):
        self.response = response
