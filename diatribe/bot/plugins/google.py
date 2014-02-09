import logging

from twisted.words.protocols.irc import assembleFormattedText, attributes as A

import requests

CLASS_NAME = "GooglePlugin"
SHORT_HELP = "%(trigger)sg, %(trigger)sgoogle <query>: \
              returns the definition of <query> from google.com"

API_URL = "http://ajax.googleapis.com/ajax/services/search/web?v=1.0&q=%s"


class GooglePlugin():
    """docstring for TwitterPlugin"""

    def __init__(self, bot):
        bot.register_command(__name__, 'g', self.first_google_result)
        bot.register_command(__name__, 'google', self.first_google_result)
        self.bot = bot

    def first_google_result(self, channel, nick, msg, args):
        if 'google_apis' not in self.bot.plugin_config:
            logging.error('Google apis not configured')
            self.bot.msg('Google search plugin not configured')
        headers = {'Referer': self.bot.plugin_config['google_apis']['referer']}
        try:
            r = requests.get(API_URL % args['query'].replace('  ', ' '),
                             headers=headers)
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            logging.exception("google search httperror: ")
        result = r.json()['responseData']['results'][0]
        title = result['titleNoFormatting'].encode('UTF-8')
        formatted_msg = assembleFormattedText(A.bold[title]) + ": "
        formatted_msg += result['url'].encode('UTF-8')
        self.bot.msg(channel, formatted_msg)
