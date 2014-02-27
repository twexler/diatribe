#!/usr/bin/python

import os
import sys
import urlparse
import logging
import hashlib
import json
import importlib
import glob

from optparse import OptionParser


import redis

from twisted.words.protocols import irc
from twisted.internet import ssl, reactor, protocol

from werkzeug.routing import Map, DEFAULT_CONVERTERS, BaseConverter, Rule
from werkzeug.exceptions import NotFound, MethodNotAllowed

from converters import *


class Diatribe(irc.IRCClient):
    """docstring for Diatribe"""

    nickname = None
    channels = {}
    plugins = {}

    def __init__(self, nickname, config):
        self.nickname = nickname
        self.plugin_config = config
        triggerConverter = self.create_trigger_converter()
        my_converters = {'fstring': FinalStringConverter,
                         'url': URLConverter, 'trigger': triggerConverter}
        my_converters.update(DEFAULT_CONVERTERS)
        self.rule_map = Map([], converters=my_converters)
        self.load_plugins()
        self.mapper = self.rule_map.bind(self.nickname, '/',
                                         default_method='chanmsg')
        logging.debug('mapper rules: %s' % str(self.mapper.map._rules))

    def load_plugins(self):
        path = os.path.relpath(os.path.dirname(__file__))
        logging.debug('path is %s' % path)
        for plugin_src in glob.glob('%s/plugins/*.py' % path):
            name = plugin_src.replace('.py', '').replace('/', '.')
            if name.find('__') > 0:
                continue
            logging.debug('Attempting to load plugin at %s' % name)
            try:
                plugin = importlib.import_module(name)
            except ImportError:
                logging.error('Unable to load plugin at %s' % plugin_src)
                logging.exception("Caught exception loading plugin:")
                continue
            self.plugins.update({name: {'class': plugin}})
            try:
                klass = getattr(plugin, plugin.ENTRY_CLASS)
            except AttributeError:
                logging.error('Unable to load plugin %s, ENTRY_CLASS undefined' % name)
                continue
            try:
                klass(self)
                logging.info('successfully loaded plugin %s' % name)
            except:
                logging.error('Failed to initialize plugin %s' % name)
                logging.exception('Caught exception: ')
        pass

    def create_trigger_converter(self):
        my_tc = BaseConverter
        my_tc.regex = r"%s|(%s:\s+)" % (self.plugin_config['trigger'],
                                        self.nickname)
        return my_tc

    def register_command(self, name, command,
                         endpoint, methods=None, custom_rule=None, query=True):
        plugin = self.plugins[name]
        if 'commands' in plugin:
            plugin['commands'].append(command)
        else:
            plugin['commands'] = [command]
        self.plugins[name] = plugin
        rules = []
        if len(plugin['commands']) > 1:
            rules.append("<any(%s):cmd> " % ', '.join(plugin['commands']))
        else:
            rules.append(plugin['commands'][0])
        if custom_rule:
            rules.append(custom_rule)
        if query:
            rules.append("<fstring:query>")
        logging.debug('rules are %s' % rules)
        rule_str = "/<trigger:t>" + ' '.join(rules)
        rule = Rule(rule_str, endpoint=endpoint, methods=methods)
        if rule in self.rule_map._rules:
            index = self.rule_map._rules.index(rule)
            del self.rule_map._rules[index]
            self.rule_map._rules.update()
        self.rule_map.add(rule)

    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        logging.info("connected")

    def signedOn(self):
        logging.info("signed on to %s" % self.hostname)
        if self.factory.network not in self.factory.store.hkeys('networks'):
            self.host_id = hashlib.sha1(self.factory.network).hexdigest()[:9]
            self.factory.store.hset('networks',
                                    self.factory.network, self.host_id)
            logging.debug('set host id in redis')
        else:
            self.host_id = self.factory.store.hget('networks',
                                                   self.factory.network)
            logging.debug('got host id from redis')
        for channel in self.factory.config['channels']:
            self.join(channel.encode('UTF-8'))

    def joined(self, channel):
        logging.debug('host_id is %s ' % self.host_id)
        if channel not in self.channels:
            chan_obj = {}
            chan_obj['id'] = hashlib.sha1(channel).hexdigest()[:9]
            self.channels[channel] = chan_obj
            chan_ids = dict([(k, v['id']) for k, v in self.channels.iteritems()])
            self.factory.store.hmset('%s.channels' % self.host_id, chan_ids)
            logging.debug('set %s.channels to %s' % (self.host_id, chan_ids))
        logging.info("joined %s" % channel)

    def privmsg(self, nick, channel, msg):
        nick = nick.split("!")[0].encode('UTF-8')
        channel = channel.decode('UTF-8')
        msg = msg.encode('UTF-8')
        if channel == self.nickname:
            self.dispatch_plugin(nick, nick, msg, method='privmsg')
        else:
            self.dispatch_plugin(nick, channel, msg)

    def dispatch_plugin(self, nick, channel, msg=None, method=None):
        logging.debug('dispatching plugin with msg: %s' % msg)
        path = "/"+msg.replace(' ', '  ')
        logging.debug('path is %s' % path)
        try:
            endpoint, args = self.mapper.match(path, method)
        except (NotFound, MethodNotAllowed):
            logging.debug('not calling endpoint')
            if method in ['privmsg', 'chanmsg']:
                logging.debug("%s: <%s> %s" % (channel, nick, msg))
                return False
            return False
        else:
            logging.debug('calling endpoint %s, args %s' % (str(endpoint), args))
            endpoint(channel.encode('UTF-8'), nick, msg, args)


class DiatribeFactory(protocol.ClientFactory):
    """docstring for DiatribeFavtory"""

    def __init__(self, network, config):
        dbn = os.environ.get('REDISCLOUD_URL', config['dbn'])
        if not dbn or "redis" not in dbn:
            logging.error("Diatribe doesn't support anything except redis right now, please use a redis db")
            sys.exit(1)
        url = urlparse.urlparse(dbn)
        self.store = redis.StrictRedis(host=url.hostname,
                                       port=url.port, password=url.password)
        self.network = network
        self.config = config['networks'][network]
        if 'plugins' in config:
            self.plugin_config = config['plugins']
        else:
            self.plugin_config = None

    def buildProtocol(self, addr):
        p = Diatribe(self.config['nickname'].encode('UTF-8'),
                     self.plugin_config)
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
        f = DiatribeFactory(network, config)
        if net_config['ssl']:
            reactor.connectSSL(net_config['network'],
                               net_config['port'], f,
                               ssl.ClientContextFactory())
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
