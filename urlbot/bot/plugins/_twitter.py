import logging

from twisted.words.protocols.irc import assembleFormattedText, attributes as A

from werkzeug.routing import Rule

from twitter import Twitter as twitter_api, OAuth as twitter_oauth
from twitter.api import TwitterHTTPError

CLASS_NAME = "TwitterPlugin"


class TwitterPlugin():
    """docstring for TwitterPlugin"""

    def __init__(self, bot):
        bot.rule_map.add(Rule('/<any(t, twitter):cmd>  <user>',
                              endpoint=self.last_tweet))
        self.bot = bot

    def last_tweet(self, channel, nick, msg, args):
        if 'twitter_api' not in self.bot.plugin_config:
            logging.debug('configure twitter plugin')
            self.bot.msg(channel.encode('UTF-8'),
                         'Twitter plugin not configured')
            return False
        creds = self.bot.plugin_config['twitter_api']
        auth = twitter_oauth(creds['access_token'],
                             creds['access_token_secret'],
                             creds['consumer_key'],
                             creds['consumer_secret'])
        t = twitter_api(auth=auth)
        try:
            user = t.users.lookup(screen_name=args['user'])[0]
        except TwitterHTTPError:
            logging.exception('Caught twitter api exception:')
            self.bot.msg('Error retreiving tweet from %s' % args['user'])
            return
        text = user['status']['text'].encode('UTF-8')
        screen_name = args['user'].encode('UTF-8')
        formatted_msg = assembleFormattedText(A.bold[screen_name])
        formatted_msg += assembleFormattedText(A.normal[" tweets: "]) + text
        self.bot.msg(channel.encode('UTF-8'), formatted_msg)
