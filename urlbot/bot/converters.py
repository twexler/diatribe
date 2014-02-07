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

    regex = r".*\s*(http[s]*:\/\/([a-z0-9]+([\-\.]{1}[a-z0-9]+)*\.[a-z]{2,6}/?\S*))\s*\w*"

    def __init__(self, map, domain=None):
        self.domain = domain
        pass

    def to_python(self, value):
        http = value.find('http')
        double_space = value.find('  ', http)
        logging.debug('found http at %d' % http)
        logging.debug('found double space at %d' % double_space)
        if double_space > 0:
            value = value[http:double_space]
        else:
            value = value[http:]
        logging.debug('value is: %s' % value)
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