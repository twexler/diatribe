#requires that plugins/wunderground_key be set in config.json

import logging

import requests

from twisted.words.protocols.irc import assembleFormattedText, attributes as A

CLASS_NAME = "WeatherPlugin"
SHORT_HELP = "%(trigger)sw, %(trigger)sweather <location>: outputs \
              the most recent weather from the location specified"

API_URL = "https://api.wunderground.com/api/%(key)s/conditions/q/%(query)s.json"


class WeatherPlugin():

    def __init__(self, bot):
        bot.register_command(__name__, 'w', self.current_conditions)
        bot.register_command(__name__, 'weather', self.current_conditions)
        self.bot = bot

    def current_conditions(self, channel, nick, msg, args):
        query = ' '.join(args['query'].split('  ')).lstrip()
        if 'wunderground_key' not in self.bot.plugin_config:
            logging.debug('configure weather plugin')
            self.bot.msg(channel,
                         'Weather plugin not configured')
            return False
        try:
            args = {'key': self.bot.plugin_config['wunderground_key'],
                    'query': query}
            r = requests.get(API_URL % args)
            r.raise_for_status()
            data = r.json()['current_observation']
        except:
            logging.exception('Caught exception while searching for weather')
            self.bot.msg(channel,
                         'Cannot find weather for %s' % query)
            return False
        response = assembleFormattedText(A.bold[data['display_location']['full'].encode('UTF-8')])
        response += assembleFormattedText(A.normal[" (%s): " % query])
        response += "%(weather)s, %(temperature_string)s, Humidity: %(relative_humidity)s, %(observation_time)s" % data
        self.bot.msg(channel, response.encode('UTF-8'))
