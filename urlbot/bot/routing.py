import urlparse
import logging

from werkzeug.routing import BaseConverter, ValidationError

class FinalStringConverter(BaseConverter):
    """docstring for FinalStringConverter"""

    regex = r".*$"
    def to_python(self, value):
        return str(value)

    def to_url(self, value):
        return str(value)

class URLConverter(BaseConverter):
    """docstring"""

    regex = r"(http[s]*:\/\/(.*))"

    def __init__(self, map, domain=None):
        self.domain = domain
        pass

    def to_python(self, value):
        logging.debug('domain is: %s' % self.domain)
        if self.domain:
            url = urlparse.urlparse(value)
            if self.domain in url.netloc:
                return url
            else:
                raise ValidationError()
        else:
            return str(value)

    def to_url(self, value):
        return str(value)