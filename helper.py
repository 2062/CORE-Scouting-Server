from functools import wraps
from werkzeug import exceptions as ex
from flask import request, g

import model.user as user


def check_args(*required_args):
	"""
	checks that the required arguments (specified in a tuple or list) exist in
	the supplied data if they don't exist, then an exception is raised
	"""
	for arg in required_args:
		if arg not in g.args:
			raise ex.BadRequest('the argument "%s" was not supplied in your request' % arg)


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
