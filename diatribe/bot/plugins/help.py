import logging
import re

CLASS_NAME = "HelpPlugin"
SHORT_HELP = "%(trigger)shelp, %(trigger)scommands <command>: outputs \
              helpful information about this bot's commands or get \
              detailed help about a single command"

TABS_RE = r"(\s{2,})"


class HelpPlugin():

    def __init__(self, bot):
        bot.register_command(__name__, 'help', self.send_help, query=False)
        bot.register_command(__name__, 'help', self.send_help)
        bot.register_command(__name__, 'commands', self.send_help)
        self.bot = bot

    def send_help(self, channel, nick, msg, args):
        logging.debug('sending help to %s' % nick)
        format = {'trigger': args['t']}
        if 'query' in args:
            query = args['query']
            for plugin in self.bot.plugins.itervalues():
                if 'commands' not in plugin:
                    continue
                if query in plugin['commands']:
                    if hasattr(plugin['class'], 'LONG_HELP'):
                        help_msg = plugin['class'].LONG_HELP % format
                        self.bot.msg(nick, help_msg.encode('UTF-8'))
                        return
                    else:
                        msg = 'No extra help for %s%s' % (args['t'], query)
                        self.bot.msg(nick, msg.encode('UTF-8'))
                        return
        logging.debug('plugins are %s' % str(self.bot.plugins))
        for plugin in self.bot.plugins.itervalues():
            logging.debug('sending help for %s' % str(plugin))
            if hasattr(plugin['class'], 'SHORT_HELP'):
                help_msg = plugin['class'].SHORT_HELP % format
                help_msg = re.sub(TABS_RE, ' ', help_msg.encode('UTF-8'))
                self.bot.msg(nick, '- %s' % help_msg)
