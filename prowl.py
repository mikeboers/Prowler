"""Module for sending notifications to an iPhone via Prowl.

Currently I only support the send API method, and am having issues with the
verify method.

Note that the server actually returns some XML that looks like this:
    <?xml version="1.0" encoding="UTF-8"?>
    <prowl>
    <success code="200" remaining="975" resetdate="1256310030" />
    </prowl>
I am currently ignoring all of this, and only looking for "success". The
remaning attribute is how many messages that will be accepted for this key until
the resetdate (unix timestamp) at which point the count will be reset (to 1000,
currently).

If you want this aynscronous I would suggest running:
    threading.Thread(target=send, kwargs=dict(...)).start()

See: http://prowl.weks.net/

"""


import urllib
import urllib2
import logging
import threading


API_URL = 'https://prowl.weks.net/publicapi/%s'
DEFAULT_PRIORITY = 0
DEFAULT_APP = 'py:%s' % __name__
DEFAULT_EVENT = 'default'


def verify(key):
    data = {'apikey': key}
    res = urllib2.urlopen(API_URL % 'verify', urllib.urlencode(data))
    print res.read()
    
    
def send(key, message, priority=None, app=None, event=None):
    """Send a message.
    
    Parameters:
        key -- The API key for your device as given by the Prowl website.
        message -- The message to send.
        priority -- Integer from -2 to 2 inclusive.
        app -- App identifier to send as.
        event -- Event identifier to send as.
    """
    

    data = {
        'apikey': key,
        'priority': int(priority or DEFAULT_PRIORITY),
        'application': str(app or DEFAULT_APP)[:256],
        'event': str(event or DEFAULT_EVENT)[:1024],
        'description': str(message)[:10000]
    }
    res = urllib2.urlopen(API_URL % 'add', urllib.urlencode(data))
    res_data = res.read()
    success = 'success' in res_data
    # print res_data
    res.close()
    return success


class Prowl(object):
    """An object to simplify repeated prowling.
    
    Parameters for the constructor are the same as for prowl.send, and set the
    defaults which can be overidden by the Prowl.send (except for the key,
    that may never change.)
    """
    
    def __init__(self, key, priority=None, app=None, event=None):
        self.key = key
        self.priority = priority
        self.app = app
        self.event = event
    
    def send(self, message, priority=None, app=None, event=None):
        """Send a message.
        
        Parameters here overide the defaults of this object.
        """
        return send(
            key=self.key,
            message=message,
            priority=priority or self.priority,
            app=app or self.app,
            event=event or self.event
        )


class LogHandler(logging.Handler, Prowl):
    """Log handler which sends messages via Prowl.
    
    Constructor takes prowl parameters which will be used when sending logs.
    """
    
    def __init__(self, async=False, **kwargs):
        logging.Handler.__init__(self)
        Prowl.__init__(self, **kwargs)
        self.async = async

    def emit(self, record):
        
        app = self.app
        try:
            app = app % record.__dict__
        except:
            pass
        
        event = self.event
        try:
            event = event % record.__dict__
        except:
            pass
        
        msg = self.format(record)
        
        if self.async:
            threading.Thread(target=self.send, kwargs=dict(message=msg,
                app=app, event=event)).start()
        else:
            self.send(message=msg, app=app, event=event)



if __name__ == '__main__':
    import time, threading, atexit
    KEY = '8e1bd6fef4e1d49aa1a8e6ad9d47abdbdecb1ff7'
    
    if True:
        send(KEY, 'This is a message')
    
    if False:
        thread = threading.Thread(target=send, args=(KEY, 'This is a message'))
        thread.start()
        print 'resuming'
        
    
    if False:
        prowler = Prowl('8e1bd6fef4e1d49aa1a8e6ad9d47abdbdecb1ff7',
            event='Testing'
        )
        assert prowler.send("This is a test!"), 'Did not send!'
        
    if False:
        handler = LogHandler('8e1bd6fef4e1d49aa1a8e6ad9d47abdbdecb1ff7')
        logger = logging.getLogger(__name__ + '.test')
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        logger.info("This is info!")