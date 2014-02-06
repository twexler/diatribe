"""A simple hello command for the masses
Plugins take 4 arguments:
	:bot an instance of URLBot
	:channel the channel from which the message that invoked the command originated,
	:msg the actual message containing the command and any arguments
	:user the nickname of the user from which the commmand was issued
"""
def main(bot, channel, msg, user):
	bot.msg(channel.encode('UTF-8'), 'Hello %s' % user)