#!/usr/bin/python

import re
import sys
import logging

from optparse import OptionParser
from datetime import datetime

import requests

from twisted.words.protocols import irc
from twisted.internet import ssl, reactor, protocol
from BeautifulSoup import BeautifulSoup
from storm.locals import create_database, Store

from dbinterface import *

URL_RE = r"(http[s]*:\/\/(.*))"

class URLBot(irc.IRCClient):
	"""docstring for URLBot"""

	nickname = "aurlbot"

	def connectionMade(self):
		irc.IRCClient.connectionMade(self)
		logging.info("connected")

	def signedOn(self):
		self.hostname = self.factory.network.decode('UTF-8')
		logging.info("signed on to %s" % self.hostname)
		networkObj = self.factory.store.find(Network, Network.name == self.hostname).one()
		if not networkObj:
			networkObj = Network()
			networkObj.name = self.hostname
			self.factory.store.add(networkObj)
			self.flushAndCommit()
		self.join(self.factory.channel)

	def joined(self, channel):
		channelObj = self.factory.store.find(Channel, Channel.name == channel.decode('UTF-8')).one()
		networkObj = self.factory.store.find(Network, Network.name == self.hostname).one()
		logging.debug("channel: %s" % channelObj)
		if not channelObj:
			channelObj = Channel()
			channelObj.name = channel.decode('UTF-8')
			channelObj.network = networkObj
			self.factory.store.add(channelObj)
			self.flushAndCommit()
			logging.debug("added %s to db" % channel)
		logging.info("joined %s" % channel)

	def privmsg(self, nick, channel, msg):
		nick = nick.split("!")[0]
		channel = channel.decode('UTF-8')
		if channel != self.nickname:
			matches = re.findall(URL_RE, msg)
			logging.debug("matches: %s" % matches)
			if matches:
				networkObj = self.factory.store.find(Network, Network.name == self.hostname).one()
				channelObj = self.factory.store.find(Channel, Channel.name == channel, 
					Channel.network_id == networkObj.id).one()
				logging.debug("channel object is %s" % channelObj)
				url = matches[0][0]  # tuple inside a list, wat
				logging.info("caught url: %s" % url)
				r = requests.get(url)
				soup = BeautifulSoup(r.text)
				title = soup.title.string
				my_msg = "%s" % title
				self.msg(channel.encode('UTF-8'), my_msg.encode('UTF-8'))
				urlObj = URL()
				urlObj.channel = channelObj
				urlObj.title = str(title)
				urlObj.url = url
				urlObj.source = "<%s> %s" % (nick, msg)
				urlObj.timestamp = datetime.now()
				logging.debug("urlObj is %s" % urlObj)
				self.factory.store.add(urlObj)
				self.flushAndCommit()
		logging.info("%s: <%s> %s" % (channel, nick, msg))

	def flushAndCommit(self):
		self.factory.store.flush()
		self.factory.store.commit()

class URLBotFactory(protocol.ClientFactory):
	"""docstring for URLBotFavtory"""

	def __init__(self, network, channel, store):
		self.store = store
		self.channel = channel
		self.network = network

	def buildProtocol(self, addr):
		p = URLBot()
		p.factory = self
		return p

	def clientConnectionLost(self, connector, reason):
		connector.connect()

	def clientConnectionFailed(self, connector, reason):
		reactor.stop()

def main(network, channel, nickname, dbn, port, ssl_on):
	if ".db" not in dbn:
		logging.error("URLBot doesn't support anything except sqlite right now, please use a sqlite db")
		sys.exit(1)
	database = create_database("sqlite:%s" % dbn)
	store = Store(database)
	f = URLBotFactory(network, channel, store)
	if ssl_on:
		reactor.connectSSL(network, port, f, ssl.ClientContextFactory())
	else:
		reactor.connectTCP(network, port, f)
	reactor.run()

if __name__ == '__main__':
	parser = OptionParser()
	parser.add_option('-n', '--network', dest="network")
	parser.add_option('-c', '--channel', dest='channel')
	parser.add_option('-N', '--nickname', dest="nickname")
	parser.add_option('-D', '--database', dest="dbn")
	parser.add_option('-p', '--port', dest="port", type="int", default=6667)
	parser.add_option('-s', '--ssl', dest="ssl", action="store_true")
	opts = parser.parse_args()[0]
	for opt, val in opts.__dict__.iteritems():
		if not val and opt != "ssl":
			print "missing option --%s" % opt
			sys.exit(1)
	main(**opts.__dict__)
