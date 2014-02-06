import logging

import requests

from twisted.words.protocols.irc import assembleFormattedText, attributes as A

API_URL = "https://api.wunderground.com/api/%(key)s/conditions/q/%(query)s.json"

def main(bot, channel, msg, user):
	query = ' '.join(msg.split()[1:])
	if 'wunderground_key' not in bot.factory.plugin_config:
		logging.debug('configure weather plugin')
		bot.msg(channel.encode('UTF-8'), 'Weather plugin not configured')
		return False
	try:
		args = {'key': bot.factory.plugin_config['wunderground_key'], 'query': query}
		r = requests.get(API_URL % args)
		r.raise_for_status()
		data = r.json()['current_observation']
	except:
		logging.exception('Caught exception while searching for weather')
		bot.msg(channel.encode('UTF-8'), 'Cannot find weather for %s' % query)
		return False
	response = assembleFormattedText(A.bold[data['display_location']['full'].encode('UTF-8')])
	response += assembleFormattedText(A.normal[" (%s): " % query])
	response += "%(weather)s, %(temperature_string)s, Humidity: %(relative_humidity)s, %(observation_time)s" % data
	bot.msg(channel.encode('UTF-8'), response.encode('UTF-8'))