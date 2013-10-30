#!/usr/bin/python

import os
import sys
import re
import urlparse
import logging
import hashlib
import time
import json

from optparse import OptionParser


import requests
import redis

from twisted.words.protocols import irc
from twisted.internet import ssl, reactor, protocol
from BeautifulSoup import BeautifulSoup


URL_RE = r"(http[s]*:\/\/(.*))"

class URLBot(irc.IRCClient):
	"""docstring for URLBot"""

	nickname = "aurlbot"
	channel_ids = {}

	def connectionMade(self):
		irc.IRCClient.connectionMade(self)
		logging.info("connected")

	def signedOn(self):
		hostname = self.factory.config['network'].decode('UTF-8')
		logging.info("signed on to %s" % self.hostname)
		if hostname not in self.factory.store.hkeys('networks'):
			self.host_id = hashlib.sha1(hostname).hexdigest()[:9]
			self.factory.store.hset('networks', hostname, self.host_id)
			logging.debug('set host id in redis')
		else:
			self.host_id = self.factory.store.hget('networks', hostname)
			logging.debug('got host id from redis')
		for channel in self.factory.config['channels']:
			self.join(channel.encode('UTF-8'))

	def joined(self, channel):
		if channel not in self.channel_ids:
			self.channel_ids[channel] = hashlib.sha1(channel).hexdigest()[:9]
			self.factory.store.hmset('%s.channels' % self.host_id, self.channel_ids)
			logging.debug('set %s.channels to %s' % (self.host_id, self.channel_ids))
		logging.info("joined %s" % channel)

	def privmsg(self, nick, channel, msg):
		nick = nick.split("!")[0]
		channel = channel.decode('UTF-8')
		if channel != self.nickname:
			matches = re.findall(URL_RE, msg)
			logging.debug("matches: %s" % matches)
			if matches:
				url = matches[0][0]  # tuple inside a list, wat
				logging.info("caught url: %s" % url)
				r = requests.get(url)
				soup = BeautifulSoup(r.text)
				title = soup.title.string
				my_msg = "%s" % title
				self.msg(channel.encode('UTF-8'), my_msg.encode('UTF-8'))
				url_obj = {}
				url_obj['title'] = str(title)
				url_obj['url'] = url
				url_obj['source'] = "<%s> %s" % (nick, msg)
				url_obj['ts'] = time.time()
				url_id = hashlib.sha1(url).hexdigest()[:9]
				key = "%s.%s.%s" % (self.host_id, self.channel_ids[channel], url_id)
				logging.debug("url_obj is %s" % url_obj)
				self.factory.store.hmset(key, url_obj)
		logging.info("%s: <%s> %s" % (channel, nick, msg))


class URLBotFactory(protocol.ClientFactory):
	"""docstring for URLBotFavtory"""

	def __init__(self, config):
		dbn = os.environ.get('REDISCLOUD_URL', config['dbn']) 
		if not dbn or "redis" not in dbn:
			logging.error("URLBot doesn't support anything except redis right now, please use a redis db")
			sys.exit(1)
		url = urlparse.urlparse(dbn)
		self.store = redis.StrictRedis(host=url.hostname, port=url.port, password=url.password)
		self.config = config

	def buildProtocol(self, addr):
		p = URLBot()
		p.factory = self
		return p

	def clientConnectionLost(self, connector, reason):
		connector.connect()

	def clientConnectionFailed(self, connector, reason):
		reactor.stop()

def main(config="config.json", debug=False):
	if debug:
		logging.basicConfig(level=logging.DEBUG)
	try:
		config = json.load(open(config))
	except:
		logging.error('unable to parse config')
		sys.exit(1)
	f = URLBotFactory(config)
	if config['ssl']:
		reactor.connectSSL(config['network'], config['port'], f, ssl.ClientContextFactory())
	else:
		reactor.connectTCP(config['network'], config['port'], f)
	reactor.run()

if __name__ == '__main__':
	parser = OptionParser()
	parser.add_option('-c', '--config', dest='config', default="config.json")
	parser.add_option('-d', '--debug', action="store_true", dest="debug")
	opts = parser.parse_args()[0]
	for opt, val in opts.__dict__.iteritems():
		if not val and opt != "debug":
			print "missing option --%s" % opt
			sys.exit(1)
	main(**opts.__dict__)
