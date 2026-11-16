from urllib.error import HTTPError


class FailingProvider():
    def __init__(self, command_type, raw_options, utils):
        pass

    def request(self, messages):
        raise HTTPError('https://example.invalid', 401, 'Unauthorized', {}, None)
