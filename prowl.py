"""Module for sending notifications to an iPhone via Prowl.

Includes a `post` method for one-off messages, a `Prowl` class to assist in
sending multiple messages, and a `LogHandler` for sending log records via
prowl.

See: http://prowl.weks.net/

"""


__author__ = 'Mike Boers'
__author_email__ = 'github@mikeboers.com'
__version__ = '1.0b'
__license__ = 'New BSD License'


from urllib import urlencode
from urllib2 import urlopen, HTTPError
from xml.etree.ElementTree import XML
import logging


__all__ = ['Error', 'get_remaining', 'get_reset_time', 'verify', 'post',
    'Prowl', 'LogHandler']

API_URL_BASE = 'https://prowl.weks.net/publicapi/'

DEFAULT_PRIORITY = 0
DEFAULT_APP = 'py:%s' % __name__
DEFAULT_EVENT = 'default'


class Error(ValueError):
    pass


# This will be continually updated whenever a request is made.
_last_meta_data = {}


def get_remaining():
    """Get the number of posts we are allowed to make before the reset date.
    
    Returns None if no successful requests have been made yet.
    
    """
    return _last_meta_data.get('remaining')

def get_reset_time():
    """Get the time in unix time (UTC) at which our remaining counter resets.
    
    Returns None if no successful requests have been made yet.
    
    """
    return _last_meta_data.get('resetdate')


def _request(method, data=None):
    """Make the raw request to the Prowl API."""
    
    # Catch the errors and treat them just like the normal response.
    try:
        res = urlopen(API_URL_BASE + method, urlencode(data) if data else None)
    except HTTPError as res:
        pass
    
    xml = XML(res.read())
    if xml.tag != 'prowl':
        raise Error('malformed response: unexpected tag %r' % xml.tag)
    children = xml.getchildren()
    if len(children) != 1:
        raise Error('malformed response: too many children')
    node = children[0]
    status, data, text = node.tag, node.attrib, node.text
    
    if status not in ('success', 'error'):
        raise Error('malformed response: unknown status %r' % node.tag)
        
    if 'code' not in node.attrib:
        raise Error('malformed response: no response code')
    
    if status == 'error' and not text:
        raise Error('malformed response: no error message with code %d' % data['code'])
    
    data = dict((k, int(v)) for k, v in data.items())
    _last_meta_data.update(data)
    
    return status, data, text


def verify(key):
    """Verify an API key is valid.
    
    Params:
        key -- The API key to verify
    
    Return:
        True if the key is valid, False if not.
    
    Raises prowl.Error if the response is malformed in any way, or for any
    error reason besides an invalid key (which is what we are testing for).
    
    From the official docs:
    
    For the sake of adding a notification do not call verify first; it costs
    you an API call. You should only use verify to confirm an API key is valid
    in situations like a user entering an API key into your program. If it's
    not valid while posting the notification, you will get the appropriate
    error.
    
    """
    
    tag, data, text = _request('verify?apikey=' + key)
    if tag == 'success':
        return True
    if data['code'] == 401 and text == 'Invalid API key':
        return False
    raise Error(text.lower())
    
    
def post(key, message, priority=None, app=None, event=None, providerkey=None):
    """Send a message.
    
    Parameters:
        key -- An API key, or a list of API keys to post to.
        message -- The message to send.
        priority -- Integer from -2 to 2 inclusive.
        app -- App identifier to send as.
        event -- Event identifier to send as.
        providerkey -- Provider API key if you have been whitelisted.
    """
    
    # We are not enforcing the maximum lengths on the application (256),
    # event (1024), or message (10000). Nor am I forcing anything to be an
    # int or str. I'm going to let the server yell at you.
    data = {
        'apikey': key if isinstance(key, basestring) else ','.join(key),
        'priority': priority or DEFAULT_PRIORITY,
        'application': app or DEFAULT_APP,
        'event': event or DEFAULT_EVENT,
        'description': message
    }
    if providerkey is not None:
        data['providerkey'] = providerkey
    
    status, data, text = _request('add', data)
    if status != 'success':
        raise Error(text.lower())


class Prowl(object):
    """An object to simplify repeated prowling.
    
    Parameters for the constructor are the same as for prowl.send, and set the
    defaults which can be overidden by the Prowl.post.
    """
    
    def __init__(self, key, **defaults):
        self.defaults = defaults
        self.defaults['key'] = key
    
    def post(self, message, **kwargs):
        """Post a message.
        
        Parameters here overide the defaults of this object.
        
        """
        meta = self.defaults.copy()
        meta.update(kwargs)
        return post(
            message=message,
            **meta
        )


class LogHandler(logging.Handler, Prowl):
    
    """Log handler which sends messages via Prowl.
    
    Constructor takes prowl parameters which will be used when sending logs.
    
    The event and app will be used as format strings with the log record
    data. You can use the same keys for log formatters found here:
        http://docs.python.org/library/logging.html#formatter-objects
    
    """
    
    def __init__(self, key, **kwargs):
        logging.Handler.__init__(self)
        Prowl.__init__(self, key, **kwargs)

    def emit(self, record):
        data = {}
        for key in ('app', 'event'):
            if key in self.defaults:
                data[key] = self.defaults[key] % record.__dict__
        message = self.format(record)
        self.post(message=message, **data)
