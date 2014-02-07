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

    regex = r".*(http[s]*:\/\/([a-z0-9]+([\-\.]{1}[a-z0-9]+)*\.[a-z]{2,6}))\S+"

    def __init__(self, map, domain=None):
        self.domain = domain
        pass

    def to_python(self, value):
        logging.debug('value is: %s' % value)
        value = value[value.find('http'):]
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