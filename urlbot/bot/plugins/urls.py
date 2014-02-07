import logging
import time
import hashlib

import requests

from BeautifulSoup import BeautifulSoup

from werkzeug.routing import Rule

from twisted.words.protocols.irc import assembleFormattedText, attributes as A

from twitter import Twitter as twitter_api, OAuth as twitter_oauth
from twitter.api import TwitterHTTPError

CLASS_NAME = "URLPlugin"

YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/videos?part=snippet,contentDetails&id=%(id)s&key=%(apikey)s"


class URLPlugin():

    def __init__(self, bot):
        bot.rule_map.add(Rule('/<url("youtube.com"):url>  <fstring:crap>',
                              endpoint=self.handle_youtube))
        bot.rule_map.add(Rule('/<url("twitter.com"):url>  <fstring:crap>',
                              endpoint=self.handle_twitter))
        bot.rule_map.add(Rule('/<url:url>  <fstring:crap>',
                              endpoint=self.handle_url))
        self.bot = bot
        pass

    def handle_url(self, channel, nick, msg, args):
        url = args['url']
        logging.info("caught url: %s" % url)
        try:
            r = requests.get(url)
        except requests.exceptions.ConnectionError:
            logging.debug('invalid url')
        soup = BeautifulSoup(r.text,
                             convertEntities=BeautifulSoup.HTML_ENTITIES)
        title = soup.title.string
        my_msg = "%s" % title
        formatted_msg = assembleFormattedText(A.bold[my_msg.encode('UTF-8')])
        self.bot.msg(channel.encode('UTF-8'), formatted_msg)
        url_obj = {}
        url_obj['title'] = str(title)
        url_obj['url'] = url
        url_obj['source'] = "<%s> %s" % (nick, msg)
        url_obj['ts'] = time.time()
        url_obj['type'] = 'url'
        url_id = hashlib.sha1(url).hexdigest()[:9]
        self.log_url(url_id, url_obj, channel)

    def handle_youtube(self, channel, nick, msg, args):
        url = args['url'].geturl()
        if 'watch' not in url:
            self.handle_url(channel, nick, msg,
                            args={'url': url})
            return
        logging.debug('got youtube url: %s' % str(args['url']))
        video_id = args['url'].query.split('=')[1]
        apis_config = self.bot.plugin_config['google_apis']
        url_args = {'id': video_id, 'apikey': apis_config['key']}
        try:
            r = requests.get(YOUTUBE_API_URL % url_args,
                             headers={'Referer': apis_config['referer']})
        except requests.exceptions.HTTPError:
            # in case we can't contact the youtube api, log anyway
            self.handle_url(channel, nick, msg,
                            args={'url': url})
            return
        resp = r.json()['items'][0]
        #thanks for fucking up this length encoding, youtube
        length = resp['contentDetails']['duration'].replace('PT', '')
        length = length.replace('H', ':').replace('M', ':').encode('UTF-8')
        length = length.replace('S', '')
        data = resp['snippet']
        url_obj = {}
        url_obj['title'] = data['title'].encode('UTF-8')
        url_obj['thumb_url'] = data['thumbnails']['default']['url']
        url_obj['created_ts'] = time.mktime(
            time.strptime(data['publishedAt'],
                          '%Y-%m-%dT%H:%M:%S.000Z'))
        url_obj['author'] = data['channelTitle'].encode('UTF-8')
        url_obj['length'] = length.encode('UTF-8')
        url_obj['ts'] = time.time()
        url_obj['url'] = url
        url_obj['source'] = "<%s> %s" % (nick, msg)
        url_obj['type'] = 'youtube'
        url_id = hashlib.sha1(url).hexdigest()[:9]
        formatted_msg = assembleFormattedText(A.bold[url_obj['title']]) + " "
        formatted_msg += assembleFormattedText(A.normal["(" + length + ") "])
        formatted_msg += assembleFormattedText(A.bold['Uploaded by: '])
        formatted_msg += assembleFormattedText(A.normal[url_obj['author']])
        formatted_msg += time.strftime(" on %c", time.gmtime(url_obj['created_ts']))
        self.bot.msg(channel.encode('UTF-8'), formatted_msg)
        self.log_url(url_id, url_obj, channel)

    def handle_twitter(self, channel, nick, msg, args):
        url = args['url']
        if 'twitter_api' not in self.bot.plugin_config or 'status' not in url.path:
            self.handle_url(channel, nick, msg, args={'url': url.geturl()})
        creds = self.bot.plugin_config['twitter_api']
        auth = twitter_oauth(creds['access_token'],
                             creds['access_token_secret'],
                             creds['consumer_key'],
                             creds['consumer_secret'])
        t = twitter_api(auth=auth)
        tweet_id = url.path.split('/')[-1:][0]
        try:
            tweet = t.statuses.show(id=tweet_id)
        except TwitterHTTPError:
            logging.exception('Caught twitter api exception:')
            self.handle_url(channel, nick, msg, args={'url': url.geturl()})
            return
        url_obj = {}
        url_obj['type'] = 'tweet'
        url_obj['author'] = tweet['user']['screen_name'].encode('UTF-8')
        url_obj['title'] = tweet['text'].encode('UTF-8')
        url_obj['ts'] = time.time()
        url_obj['source'] = "<%s> %s" % (nick, msg)
        url_obj['url'] = url.geturl()
        formatted_msg = assembleFormattedText(A.bold[url_obj['author']])
        formatted_msg += assembleFormattedText(A.normal[" tweets: "]) + url_obj['title']
        url_id = hashlib.sha1(url.geturl()).hexdigest()[:9]
        self.bot.msg(channel.encode('UTF-8'), formatted_msg)
        self.log_url(url_id, url_obj, channel)

    def log_url(self, url_id, url_obj, channel):
        key = "%s.%s.%s" % (self.bot.host_id,
                            self.bot.channels[channel]['id'], url_id)
        logging.debug("url_obj is %s, key is %s" % (url_obj, key))
        self.bot.factory.store.hmset(key, url_obj)
