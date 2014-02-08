import unittest
import urlparse

from werkzeug.routing import Map, Rule

from urlbot.bot.converters import *


class URLConverterTest(unittest.TestCase):

    def setUp(self):
        url_map = Map([
            Rule('/<url("youtube.com"):url>', endpoint="youtube"),
            Rule('/<url:url>', endpoint="url"),
        ], converters={'url': URLConverter})
        self.urls = url_map.bind('', '/', '')

    def test_regular_url(self):
        msg = "http://google.com"
        url = "http://google.com"
        endpoint, args = self.matcher(msg)
        self.assertEquals(endpoint, 'url')
        self.assertEquals(args['url'], url)

    def test_regular_url_with_preceding_text(self):
        msg = "test http://google.com"
        url = "http://google.com"
        endpoint, args = self.matcher(msg)
        self.assertEquals(endpoint, 'url')
        self.assertEquals(args['url'], url)

    def test_regular_url_with_trailing_text(self):
        msg = "http://google.com test"
        url = "http://google.com"
        endpoint, args = self.matcher(msg)
        self.assertEquals(endpoint, 'url')
        self.assertEquals(args['url'], url)

    def test_regular_url_with_surrounding_text(self):
        msg = "test http://google.com test"
        url = "http://google.com"
        endpoint, args = self.matcher(msg)
        self.assertEquals(endpoint, 'url')
        self.assertEquals(args['url'], url)

    def test_regular_url_with_trailing_text_and_punctuation(self):
        msg = "test http://google.com test."
        url = "http://google.com"
        endpoint, args = self.matcher(msg)
        self.assertEquals(endpoint, 'url')
        self.assertEquals(args['url'], url)

    def test_complex_url(self):
        msg = r"https://www.google.com/#q=test+test%20test"
        url = r"https://www.google.com/#q=test+test%20test"
        endpoint, args = self.matcher(msg)
        self.assertEquals(endpoint, 'url')
        self.assertEquals(args['url'], url)

    def test_complex_url_with_preceding_text(self):
        msg = r"test https://www.google.com/#q=test+test%20test"
        url = r"https://www.google.com/#q=test+test%20test"
        endpoint, args = self.matcher(msg)
        self.assertEquals(endpoint, 'url')
        self.assertEquals(args['url'], url)

    def test_complex_url_with_trailing_text(self):
        msg = r"https://www.google.com/#q=test+test%20test test"
        url = r"https://www.google.com/#q=test+test%20test"
        endpoint, args = self.matcher(msg)
        self.assertEquals(endpoint, 'url')
        self.assertEquals(args['url'], url)

    def test_complex_url_with_surrounding_text(self):
        msg = r"test https://www.google.com/#q=test+test%20test test"
        url = r"https://www.google.com/#q=test+test%20test"
        endpoint, args = self.matcher(msg)
        self.assertEquals(endpoint, 'url')
        self.assertEquals(args['url'], url)

    def test_complex_url_with_trailing_text_and_punctuation(self):
        msg = r"https://www.google.com/#q=test+test%20test test."
        url = r"https://www.google.com/#q=test+test%20test"
        endpoint, args = self.matcher(msg)
        self.assertEquals(endpoint, 'url')
        self.assertEquals(args['url'], url)

    def test_youtube_url(self):
        msg = r"http://www.youtube.com/watch?v=vIcdbxzrtbI"
        url = r"http://www.youtube.com/watch?v=vIcdbxzrtbI"
        endpoint, args = self.matcher(msg)
        self.assertEquals(endpoint, 'youtube')
        self.assertEquals(args['url'], urlparse.urlparse(url))

    def matcher(self, msg):
        msg = msg.replace(' ', '  ')
        logging.debug('msg is: %s' % msg)
        endpoint, args = self.urls.match("/" + msg)
        return endpoint, args
