import logging

from twisted.words.protocols.irc import assembleFormattedText, attributes as A

from werkzeug.routing import Rule

import requests

CLASS_NAME = "IMDBPlugin"

SEARCH_API_URL = "http://www.omdbapi.com/?s=%s"
ID_API_URL = "http://www.omdbapi.com/?i=%s"
IMDB_URL = "http://www.imdb.com/title/%s/"


class IMDBPlugin():
    """docstring for UrbanDictionaryPlugin"""

    def __init__(self, bot):
        bot.rule_map.add(Rule('/<any(i, imdb, movie, tv):cmd> <fstring:query>',
                              endpoint=self.search_imdb))
        self.bot = bot

    def search_imdb(self, channel, nick, msg, args):
        query = args['query'].lstrip().replace('  ', ' ')
        try:
            r = requests.get(SEARCH_API_URL % query)
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            self.bot.msg(channel,
                         "Cannot find %s on IMDB" % query)
            return False
        r_data = r.json()
        if 'Error' in r_data:
            self.bot.msg(channel,
                         "Cannot find %s on IMDB" % query)
            return False
        cmd = args['cmd']
        if cmd in ['tv', 'movie']:
            result = self.find_correct_type(cmd, r_data['Search'])
            if result is None:
                msg = 'No %s found for "%s"' % (cmd, query)
                self.bot.msg(channel, msg.encode('UTF-8'))
                return False
            imdb_id = result['imdbID']
        else:
            imdb_id = r_data['Search'][0]['imdbID']
        r2 = requests.get(ID_API_URL % imdb_id)
        data = r2.json()
        title = data['Title'].encode('UTF-8')
        year = data['Year'].encode('UTF-8')
        genre = data['Genre'].encode('UTF-8')
        imdb_url = IMDB_URL % imdb_id.encode('UTF-8')
        summary = data['Plot'].encode('UTF-8')
        formatted_msg = assembleFormattedText(A.bold[title])
        formatted_msg += assembleFormattedText(A.normal[" (%s), " % year])
        formatted_msg += assembleFormattedText(A.bold['Genres: '])
        formatted_msg += assembleFormattedText(A.normal[genre])
        formatted_msg += " %s" % imdb_url
        formatted_plot = assembleFormattedText(A.bold['Plot: '])
        formatted_plot += assembleFormattedText(A.normal[summary])
        self.bot.msg(channel, formatted_msg)
        self.bot.msg(channel, formatted_plot)
        return

    def find_correct_type(self, search_type, results):
        logging.debug('search type is: %s' % search_type)
        if search_type == "tv":
            logging.debug('searching for tv')
            for result in results:
                r_type = result['Type'].lower()
                if r_type == "series" or r_type == "episode":
                    return result
            return None
        elif search_type == "movie":
            logging.debug('searching for movies')
            for result in results:
                if result['Type'].lower() == "movie":
                    return result
            return None
        return None
