import logging

from twisted.words.protocols.irc import assembleFormattedText, attributes as A

from werkzeug.routing import Rule

import requests

CLASS_NAME = "UrbanDictionaryPlugin"

API_URL = "http://api.urbandictionary.com/v0/define?term=%s"


class UrbanDictionaryPlugin():
    """docstring for UrbanDictionaryPlugin"""

    def __init__(self, bot):
        bot.rule_map.add(Rule('/<trigger:t><any(ud, urbandictionary):cmd> <fstring:query>',
                              endpoint=self.urbandictionary_lookup))
        self.bot = bot

    def urbandictionary_lookup(self, channel, nick, msg, args):
        query = args['query']
        try:
            r = requests.get(API_URL % query)
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            self.bot.msg(channel, 'No results for %s' % query)
            return False
        data = r.json()
        if 'result_type' in data:
            if data['result_type'] == "no_results":
                self.bot.msg('No results for %s' % query)
                return False
            else:
                definition = data['list'][0]
                word = definition['word'].encode('UTF-8')
                def_text = definition['definition'].encode('UTF-8')
                permalink = definition['permalink'].encode('UTF-8')
                formatted_msg = assembleFormattedText(A.bold[word])
                formatted_msg += assembleFormattedText(A.normal[": "])
                formatted_msg += def_text.split('\r\n')[0]
                formatted_msg += assembleFormattedText(A.bold[" See more: "])
                formatted_msg += assembleFormattedText(A.normal[permalink])
                self.bot.msg(channel, formatted_msg)
        else:
            self.bot.msg(channel, 'No results for %s' % query)
            return False
