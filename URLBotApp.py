#!/usr/bin/python

import os
import sys
import math
import logging
import urlparse
import hashlib

from datetime import datetime
from optparse import OptionParser

import redis

from flask import Flask, g, url_for, render_template


DATABASE = None
DEBUG = True
app = Flask(__name__)

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
	if page == 1:
		start = 0
	else:
		start = page * num_results
	end = start + num_results
	key_search = "%s.%s.*" % (net_id, chan_id)
	url_key_list = g.redis.keys(key_search)
	logging.debug("key list is %s" % url_key_list)
	urls = []
	for url_key in url_key_list:
		url = g.redis.hgetall(url_key)
		url['ts'] = datetime.fromtimestamp(float(url['ts']))
		urls.append(url)
	return render_template('channel.html', network=network, channel=channel, urls=urls, range=range)

@app.before_request
def before_request():
	url = urlparse.urlparse(os.environ.get('REDISCLOUD_URL') or DATABASE)
	g.redis = redis.StrictRedis(host=url.hostname, port=url.port, password=url.password)

@app.teardown_request
def teardown_request(obj):
	g.redis.connection_pool.disconnect()

def main(host, port):
	app.config.from_object(__name__)
	app.run(host, port)

if __name__ == '__main__':
	parser = OptionParser()
	parser.add_option('-D', '--dsn', dest='dsn')
	parser.add_option('-l', '--listen', dest='listen', default="127.0.0.1")
	parser.add_option('-p', '--port', dest='port', default=5000, type="int")
	opts = parser.parse_args()[0]
	if not opts.dsn:
		logging.error('no dsn specified')
		sys.exit(1)
	DATABASE = opts.dsn
	main(opts.listen, opts.port)