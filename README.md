Diatribe
======
[![Build Status](https://travis-ci.org/twexler/diatribe.png?branch=master)](https://travis-ci.org/twexler/diatribe) [![Coverage Status](https://coveralls.io/repos/twexler/diatribe/badge.png?branch=master)](https://coveralls.io/r/twexler/diatribe?branch=master)

An IRC bot written in python with flask, twisted, redis, and bootstrap

Plugins
=======

- [IMDB](http://www.imdb.com) (i, imdb, tv, movie): Searches imdb for a TV show/movie title
- [Twitter](https://twitter.com) (t, twitter): Retrieves user's latest tweet
- [Urban Dictionary](http://www.urbandictionary.com) (ud, urbandictionary): Retrieves definitions from urban dictionary
- [Google](https://www.google.com) (google, g): Retrieves single result from Google
- Weather (w, weather): Retrieves weather for specified location
- URLs: Triggered when a user posts a url to a channel, retrieves metadata about URL, stores in a database and can be displayed(for historical purposes) in a webapp

Heroku
------

You can run this on heroku, it requires the Redis Cloud addon.
