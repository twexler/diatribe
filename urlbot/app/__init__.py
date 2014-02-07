#!/usr/bin/python

import os
import sys
import logging
import urlparse
import hashlib
import json

from datetime import datetime
from optparse import OptionParser

import redis

from flask import (Flask, g, url_for,
                   render_template, jsonify, send_from_directory, request)

from twitter import Twitter, OAuth as twitter_oauth
from twitter.api import TwitterHTTPError


def load_config(config_file="config.json"):
    try:
        print config_file
        config = json.load(open(config_file))
    except:
        logging.error('unable to parse config')
        sys.exit(1)
    return config

CONFIG = load_config()
DEBUG = True
app = Flask(__name__)
app.config.from_object(__name__)


@app.route("/")
def index():
    networks = {}
    nets = g.redis.hkeys('networks')
    for net in nets:
        net_id = hashlib.sha1(net).hexdigest()[:9]
        chans = g.redis.hkeys('%s.channels' % net_id)
        networks[net] = chans
    return render_template('index.html', networks=networks, url_for=url_for)


@app.route("/<network>")
def list_channels(network):
    net_id = hashlib.sha1(network).hexdigest()[:9]
    channels = g.redis.hkeys('%s.channels' % net_id)
    return render_template('network.html', channels=channels,
                           network=network, url_for=url_for)


@app.route("/<network>/<channel>/list")
@app.route("/<network>/<channel>/list/<page>/<num_results>")
def list_urls(network, channel, page=1, num_results=20):
    net_id = hashlib.sha1(network).hexdigest()[:9]
    chan_id = hashlib.sha1("#"+channel).hexdigest()[:9]
    num_results = int(num_results)
    page = int(page)
    key_search = "%s.%s.*" % (net_id, chan_id)
    url_key_list = g.redis.keys(key_search)
    logging.debug("key list is %s" % url_key_list)
    urls = []
    for url_key in url_key_list:
        url = g.redis.hgetall(url_key)
        url['ts'] = datetime.fromtimestamp(float(url['ts']))
        if 'type' in url:
            if url['type'] == 'tweet':
                url['tweet_embed'] = fetch_twitter_embed(url['url'])
            elif url['type'] == "youtube":
                url['yt_id'] = urlparse.urlparse(url['url']).query.split('=')[1]
        urls.append(url)
    urls = sorted(urls, sort_url_list)
    total = len(urls)
    if num_results > 0 and page:
        end = num_results * page
        start = end - num_results
        urls = urls[start:end]

    return render_template('channel.html', network=network,
                           channel=channel, urls=urls, range=range, page=page,
                           num_results=num_results,
                           pages=int(total/num_results)+1)


@app.route('/ping')
def ping():
    return jsonify({'status': "OK"})


@app.route('/robots.txt')
def static_from_root():
    return send_from_directory(app.static_folder, request.path[1:])


@app.before_request
def before_request():
    url = urlparse.urlparse(os.environ.get('REDISCLOUD_URL') or app.config['CONFIG']['dbn'])
    g.redis = redis.StrictRedis(host=url.hostname,
                                port=url.port, password=url.password)


@app.teardown_request
def teardown_request(obj):
    g.redis.connection_pool.disconnect()


def fetch_twitter_embed(tweet_url):
    if 'plugins' not in CONFIG:
        return None
    if 'twitter_api' not in CONFIG['plugins']:
        return None
    tweet_id = urlparse.urlparse(tweet_url).path.split('/')[-1:][0]
    creds = CONFIG['plugins']['twitter_api']
    auth = twitter_oauth(creds['access_token'], creds['access_token_secret'],
                         creds['consumer_key'], creds['consumer_secret'])
    t = Twitter(auth=auth)
    try:
        return t.statuses.oembed(_id=tweet_id, align='left')['html']
    except TwitterHTTPError:
        return None


def sort_url_list(x, y):
        if x['ts'] > y['ts']:
                return -1
        elif x['ts'] == y['ts']:
                return 0
        else:
                return 1


def main(config, debug):
    if debug:
        logging.basicConfig(level=logging.DEBUG)
    CONFIG = load_config(config)
    app.config.from_object(__name__)
    app.run(CONFIG.get('host', None), CONFIG.get('port', None))


