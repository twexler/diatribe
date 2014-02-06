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

from flask import Flask, g, url_for, render_template, jsonify

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

@app.route("/<network>/<channel>/list/<page>/<num_results>")
def list_urls(network, channel, page, num_results):
	net_id = hashlib.sha1(network).hexdigest()[:9]
	chan_id = hashlib.sha1(channel).hexdigest()[:9]
	num_results = int(num_results)
	page = int(page)
	key_search = "%s.%s.*" % (net_id, chan_id)
	url_key_list = g.redis.keys(key_search)
	logging.debug("key list is %s" % url_key_list)
	urls = []
	for url_key in url_key_list:
		url = g.redis.hgetall(url_key)
		url['ts'] = datetime.fromtimestamp(float(url['ts']))
		urls.append(url)
	return render_template('channel.html', network=network, channel=channel, urls=urls, range=range)

@app.route('/ping')
def ping():
	return jsonify({'status': "OK"})

@app.before_request
def before_request():
	url = urlparse.urlparse(os.environ.get('REDISCLOUD_URL') or app.config['CONFIG']['dbn'])
	g.redis = redis.StrictRedis(host=url.hostname, port=url.port, password=url.password)

@app.teardown_request
def teardown_request(obj):
	g.redis.connection_pool.disconnect()

def main(config, debug):
	if debug:
		logging.basicConfig(level=logging.DEBUG)
	CONFIG = load_config(config)
	app.config.from_object(__name__)
	app.run(CONFIG.get('host', None), CONFIG.get('port', None))

if __name__ == '__main__':
	parser = OptionParser()
	parser.add_option('-c', '--config', dest='config', default="config.json")
	parser.add_option('-d', '--debug', action="store_true", dest="debug")
	opts = parser.parse_args()[0]
	main(opts.config, opts.debug)