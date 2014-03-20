from functools import wraps
from werkzeug import exceptions as ex
from flask import request, g, make_response

import model.user as user
import config
import math

class JinjaTest(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
    def __getattr__(self, attr):
        if attr in self.__dict__:
            return self.__dict__[attr]
        return attr

def percent(val, digits = 0):
    if isinstance(val, basestring):
        return val
    # if val != 0: print val
    val *= 10 ** (digits + 2)
    return '{1:.{0}f}%'.format(digits, math.floor(val) / 10 ** digits)


def check_args(*required_args):
    """
    checks that the required arguments (specified in a tuple or list) exist in
    the supplied data if they don't exist, then an exception is raised
    """
    for arg in required_args:
        if arg not in request.args:
            raise ex.BadRequest('the argument "%s" was not supplied in your request' % arg)

def args_required(*args):
    def decorator(f):
        @wraps(f)
        def decor(*arg, **kwargs):
            check_args(*args)
            return f(*args, **kwargs)
        return decor
    return decorator

def permission_required(*permissions):
    """
    defines a decorator for checking a user's token. permissions may also be
    checked by passing all required permissions as args.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            check_args('token')
            token = g.args['token']

            # store user object in g (thread safe context) users may only
            # authenticate with a token, this is to prevent users from
            # transmitting their username & password with every request

            #the token gets escaped when sent, so decode it first
            g.user = user.token_auth(
                token,
                ip=request.remote_addr,
            )

            if not g.user:
                raise ex.Unauthorized('bad token')
            for permission in permissions:
                if not g.user.has_perm(permission):
                    raise ex.Forbidden()
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def allow_origins(func=None, origins=config.ALLOWED_ORIGINS):
    def wrapped(func):
        @wraps(func)
        def decorated(*args, **kwargs):
            origin = request.headers.get('Origin')
            g.cors = True  # origin in origins
            if request.method == 'OPTIONS':
                response = make_response('ok')
                response.headers['Access-Control-Allow-Origin'] = origin
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
                return response
            return func(*args, **kwargs)
        return decorated
    if func:
        return wrapped(func)
    else:
        return wrapped

def cors(response):
    if getattr(g, 'cors', False):
        response.headers['Access-Control-Allow-Origin'] = (
            request.headers.get('Origin')
        )
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response