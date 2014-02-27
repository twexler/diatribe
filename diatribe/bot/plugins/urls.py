import logging
import time
import hashlib
import re

import requests

from BeautifulSoup import BeautifulSoup

from werkzeug.routing import Rule

from twisted.words.protocols.irc import assembleFormattedText, attributes as A

from twitter import Twitter as twitter_api, OAuth as twitter_oauth
from twitter.api import TwitterHTTPError

ENTRY_CLASS = "URLPlugin"

YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/videos?part=snippet,contentDetails&id=%(id)s&key=%(apikey)s"
SPOTIFY_API_URL = "http://ws.spotify.com/lookup/1/.json?uri=spotify:%(type)s:%(id)s"


class URLPlugin():

    def __init__(self, bot):
        bot.rule_map.add(Rule('/<url("youtube.com"):url>',
                              endpoint=self.handle_youtube))
        bot.rule_map.add(Rule('/<url("open.spotify.com"):url>',
                              endpoint=self.handle_spotify))
        bot.rule_map.add(Rule('/<url("twitter.com"):url>',
                              endpoint=self.handle_twitter))
        bot.rule_map.add(Rule('/<url:url>',
                              endpoint=self.handle_url))
        self.bot = bot
        pass

    def handle_url(self, channel, nick, msg, args):
        url = args['url']
        logging.info("caught url: %s" % url)
        try:
            r = requests.get(url)
            r.raise_for_status()
        except (requests.exceptions.ConnectionError,
                requests.exceptions.HTTPError):
            logging.debug('invalid url')
            logging.exception('caught exception trying to fetch %s:' % url)
            return False
        url_obj = {}
        if 'image' in r.headers['content-type']:
            url_obj['type'] = "image"
            title = "Image from %s" % nick
        else:
            soup = BeautifulSoup(r.text,
                                 convertEntities=BeautifulSoup.HTML_ENTITIES)
            title = re.sub(r'([\r\n]|\s{2,})', '', soup.title.string)
            url_obj['type'] = 'url'
        my_msg = "%s" % title
        formatted_msg = assembleFormattedText(A.bold[my_msg.encode('UTF-8')])
        self.bot.msg(channel, formatted_msg)
        url_obj['title'] = str(title)
        url_obj['url'] = url
        url_obj['source'] = "<%s> %s" % (nick, msg)
        url_obj['ts'] = time.time()
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
        self.bot.msg(channel, formatted_msg)
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
        self.bot.msg(channel, formatted_msg)
        self.log_url(url_id, url_obj, channel)

    def handle_spotify(self, channel, nick, msg, args):
        url = args['url']
        path_parts = url.path.split('/')
        spotify_type = path_parts[1]
        spotify_id = path_parts[2]
        if spotify_type != "track":
            #only handle tracks for now
            self.handle_url(channel, nick, msg,
                            args={'url': url.geturl()})
            return
        url_args = {
            'type': spotify_type,
            'id': spotify_id
        }
        try:
            r = requests.get(SPOTIFY_API_URL % url_args)
        except requests.exceptions.HTTPError:
            # in case we can't contact the spotify api, log anyway
            self.handle_url(channel, nick, msg,
                            args={'url': url.geturl()})
            return
        try:
            resp = r.json()[spotify_type]
        except KeyError:
            self.handle_url(channel, nick, msg,
                            args={'url': url.geturl()})
            return
        url_obj = {}
        url_obj['type'] = 'spotify'
        artists = ', '.join([artist['name'] for artist in resp['artists']])
        url_obj['artists'] = artists.encode('UTF-8')
        url_obj['title'] = resp['name'].encode('UTF-8')
        url_obj['album'] = resp['album']['name'].encode('UTF-8')
        url_obj['released'] = resp['album']['released'].encode('UTF-8')
        url_obj['spotify_id'] = spotify_id
        url_obj['spotify_type'] = spotify_type
        url_obj['source'] = "<%s> %s" % (nick, msg)
        url_obj['ts'] = time.time()
        track_name = "%s - %s" % (url_obj['artists'], url_obj['title'])
        formatted_msg = assembleFormattedText(A.bold[track_name])
        formatted_msg += assembleFormattedText(A.normal[' From: '])
        formatted_msg += assembleFormattedText(A.bold[url_obj['album']])
        formatted_msg += assembleFormattedText(A.normal[' (%s)' % url_obj['released']])
        url_id = hashlib.sha1(url.geturl()).hexdigest()[:9]
        self.bot.msg(channel, formatted_msg)
        self.log_url(url_id, url_obj, channel)

    def log_url(self, url_id, url_obj, channel):
        key = "%s.%s.%s" % (self.bot.host_id,
                            self.bot.channels[channel]['id'], url_id)
        logging.debug("url_obj is %s, key is %s" % (url_obj, key))
        self.bot.factory.store.hmset(key, url_obj)
