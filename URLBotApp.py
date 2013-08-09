#!/usr/bin/python

import sys
import logging
import math

from datetime import datetime
from optparse import OptionParser

from storm.locals import create_database, Store
from flask import Flask, g, url_for, render_template

from dbinterface import *

DATABASE = None
DEBUG = False
app = Flask(__name__)

@app.route("/")
def index():
	Network.channels = ReferenceSet(Network.id, Channel.network_id)
	return render_template('index.html', networks=g.db.find(Network), url_for=url_for)

@app.route("/<network>/<channel>/list/<page>/<num_results>")
def list_urls(network, channel, page, num_results):
	num_results = int(num_results)
	page = int(page)
	if page == 1:
		start = 0
	else:
		start = page * num_results
	end = start + num_results
	networkObj = g.db.find(Network, Network.name == network).one()
	channelObj = g.db.find(Channel, Channel.name == channel,
		Channel.network_id == networkObj.id).one()
	urls = g.db.find(URL, URL.channel_id == channelObj.id)
	results_count = urls.count()
	num_pages = int(math.ceil(float(results_count) / float(num_results)))
	return render_template('channel.html', network=networkObj,
		channel=channelObj, results_count=results_count, 
		num_results=num_results, urls=urls[start:end], page=page, 
		num_pages=num_pages, url_for=url_for, datetime=datetime, range=range)

@app.before_request
def before_request():
	db = create_database(DATABASE)
	g.db = Store(db)

@app.teardown_request
def teardown_request(obj):
	g.db.close()

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
	DATABASE = "sqlite:%s" % opts.dsn
	main(opts.listen, opts.port)