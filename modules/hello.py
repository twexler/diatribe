def main(bot, channel, msg, user):
	bot.msg(channel.encode('UTF-8'), 'msg: %s' % msg)
	bot.msg(channel.encode('UTF-8'), 'Hello %s' % user)