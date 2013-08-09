from storm.locals import *

#simple interface to db for URLs
class Network(object):
	__storm_table__ = "network"
	id = Int(primary=True)
	name = Unicode()

class Channel(object):
	__storm_table__ = "channel"
	id = Int(primary=True)
	name = Unicode()
	network_id = Int()
	network = Reference(network_id, Network.id)

class URL(object):
	__storm_table__ = "url"
	id = Int(primary=True)
	title = RawStr()
	url = RawStr()
	source = RawStr()
	channel_id = Int()
	channel = Reference(channel_id, Channel.id)
	timestamp = DateTime()
