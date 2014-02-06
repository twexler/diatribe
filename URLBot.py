#!/usr/bin/python

import os
import sys
import re
import urlparse
import logging
import hashlib
import time
import json
import importlib

from optparse import OptionParser


import requests
import redis

from twisted.words.protocols import irc
from twisted.words.protocols.irc import assembleFormattedText, attributes as A
from twisted.internet import ssl, reactor, protocol
from BeautifulSoup import BeautifulSoup


URL_RE = r"(http[s]*:\/\/(.*))"

class URLBot(irc.IRCClient):
    """docstring for URLBot"""

    nickname = None
    channel_ids = {}

    def __init__(self, nickname):
        self.nickname = nickname

    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        logging.info("connected")

    def signedOn(self):
        hostname = self.factory.config['network'].decode('UTF-8')
        logging.info("signed on to %s" % self.hostname)
        if self.factory.network not in self.factory.store.hkeys('networks'):
            self.host_id = hashlib.sha1(self.factory.network).hexdigest()[:9]
            self.factory.store.hset('networks', self.factory.network, self.host_id)
            logging.debug('set host id in redis')
        else:
            self.host_id = self.factory.store.hget('networks', self.factory.network)
            logging.debug('got host id from redis')
        for channel in self.factory.config['channels']:
            self.join(channel.encode('UTF-8'))

    def joined(self, channel):
        logging.debug('host_id is %s ' % self.host_id)
        if channel not in self.channel_ids:
            self.channel_ids[channel] = hashlib.sha1(channel).hexdigest()[:9]
            self.factory.store.hmset('%s.channels' % self.host_id, self.channel_ids)
            logging.debug('set %s.channels to %s' % (self.host_id, self.channel_ids))
        logging.info("joined %s" % channel)

    def privmsg(self, nick, channel, msg):
        nick = nick.split("!")[0]
        channel = channel.decode('UTF-8')
        if msg.startswith('!'):
            cmd = msg.split()[0][1:]
            if self.do_command(cmd, channel, msg, nick):
                return
        if channel != self.nickname:
            matches = re.findall(URL_RE, msg)
            logging.debug("matches: %s" % matches)
            if matches:
                url = matches[0][0]  # tuple inside a list, wat
                logging.info("caught url: %s" % url)
                try:
                    r = requests.get(url)
                except requests.exceptions.ConnectionError:
                    logging.debug('invalid url')
                soup = BeautifulSoup(r.text, convertEntities=BeautifulSoup.HTML_ENTITIES)
                title = soup.title.string
                my_msg = "%s" % title
                formatted_msg = assembleFormattedText(A.bold[my_msg.encode('UTF-8')])
                self.msg(channel.encode('UTF-8'), formatted_msg)
                url_obj = {}
                url_obj['title'] = str(title)
                url_obj['url'] = url
                url_obj['source'] = "<%s> %s" % (nick, msg)
                url_obj['ts'] = time.time()
                url_id = hashlib.sha1(url).hexdigest()[:9]
                key = "%s.%s.%s" % (self.host_id, self.channel_ids[channel], url_id)
                logging.debug("url_obj is %s, key is %s" % (url_obj, key))
                self.factory.store.hmset(key, url_obj)
        logging.info("%s: <%s> %s" % (channel, nick, msg))

    def do_command(self, cmd, channel, msg, user):
        """import the neccessary module for a command handler and execute it's main()"""
        try:
            name = "modules.%s" % cmd
            logging.debug("attempting to re/load %s module" % name)
            if name in sys.modules:
                logging.debug('reloading module %s' % name)
                reload(sys.modules[name])
                mod = sys.modules[name]
            else:
                mod = importlib.import_module(name)
        except Exception as e:
            logging.exception('Caught exception importing cmd %s' % name)
            return False
        try:
            mod.main(self, channel, msg, user)
            return True
        except Exception as e:
            logging.exception("Caught exception running cmd %s" % cmd)
            return False


class URLBotFactory(protocol.ClientFactory):
    """docstring for URLBotFavtory"""

    def __init__(self, network, config):
        dbn = os.environ.get('REDISCLOUD_URL', config['dbn']) 
        if not dbn or "redis" not in dbn:
            logging.error("URLBot doesn't support anything except redis right now, please use a redis db")
            sys.exit(1)
        url = urlparse.urlparse(dbn)
        self.store = redis.StrictRedis(host=url.hostname, port=url.port, password=url.password)
        self.network = network
        self.config = config['networks'][network]
        self.plugin_config = config['plugins']

    def buildProtocol(self, addr):
        p = URLBot(self.config['nickname'].encode('UTF-8'))
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
    for network in config['networks']:
        net_config = config['networks'][network]
        logging.debug('netconfig is %s ' % net_config)
        f = URLBotFactory(network, config)
        if net_config['ssl']:
            reactor.connectSSL(net_config['network'], net_config['port'], f, ssl.ClientContextFactory())
        else:
            reactor.connectTCP(net_config['network'], net_config['port'], f)
        del f
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
