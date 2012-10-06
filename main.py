#from threading import Timer
from functools import wraps
from model.helper import error_dump, check_args
import model.user as user
import db
from override_flask import Flask
from flask import request, g

app = Flask(__name__,)

# users must login with something to be able to access anything that uses a user object (including signup)
# the limited public "guest" account is automatically used (by client) for most stuff that doesn't require much permission


@app.before_request
def before_request():
	# below stuff (g.notify & g.error) isn't really used... consider removing

	g.notify = []  # an array that holds notifications (like non-fatal errors or important messages)

	# a variable that holds an error... if there is one (there should be 1 or 0 errors returned)
	# a error is formatted as ('title','discription')
	#	title: one word name for the error
	#	description: text given to the user to tell what happened / how to fix
	g.error = ()


@app.after_view
def after_view(rv):
	if not type(rv) in (dict, list):  # check to see that it's json, if not then return
		return
	#put stuff from g in response
	return


def permission_required(*permissions):
	"""
		defines a decorator for checking a user's token
		permissions may also be checked by passing all required permissions as args
		the user object handles a lot of its own authentication, but this decorator makes it easier to check permissions on other things like admin tasks or submitting data
	"""
	def decorator(f):
		@wraps(f)
		def decorated_function(*args, **kwargs):
			try:  # try to authenticate
				check_args(request.args, 'token')

				# store user object in g (thread safe context)
				# users may only authenticate with a token, this is to prevent users from transmitting their username & password with every request
				g.user = user.Instance(token=request.args['token'], ip=request.remote_addr)

				for permission in permissions:
					g.user.can(permission)

			except Exception as error:
				return error_dump(error)  # return error if authentication failed

			return f(*args, **kwargs)
		return decorated_function
	return decorator


@app.route('/')
def index():
	return """
		<!DOCTYPE html>
		<html>
			<head>
				<title>CSD</title>
			</head>
			<body>
				<p>put docs generated by sphinx here?</p>
			</body>
		</html>
	"""


#@app.route('/test')
#def test():
#	import model.scraper.scraper as scraper
#	scraper.event_names(request.args.get('year'))
#	return 'done'

#TODO: add mongs like db browser, with option to only return json (read only?) (restricted - not able to read user collection)


# def cron():
# 	"""handles simple cron-like jobs such as rescraping"""
# 	print "cron jobs can be put here"
# 	t = Timer(10000, cron)
# 	t.start()

# cron()


@app.route('/user/account')
@permission_required()
def user_account():
	return g.user.safe_data()


@app.route('/user/login')
def user_login():
	"""get a token to use for authentication throughout the rest of the site"""
	#NOTE: no permission required for this part because it uses an alternative login method (username & password rather than token) and declares the user object on its own
	#CONSIDER: add a delay for password based login to prevent excessive attempts

	#try:
	check_args(request.args, 'username', 'password')
	g.user = user.Instance(username=request.args['username'], password=request.args['password'], ip=request.remote_addr)
	#except Exception as error:
	#	return error_dump(error)  # bad info supplied

	return {
		'token': g.user.data['session']['token'],
		'notice': 'login successful',
	}


@app.route('/user/logout')
@permission_required()
def user_logout():
	g.user.logout()


@app.route('/user/update')
def user_update():
	try:
		check_args(request.args, 'data')
		g.user.update(request.args['data'])
		g.user.save()
	except Exception as error:
		return error_dump(error)

	return {'notify': 'update successful'}


@app.route('/user/signup')
@permission_required()  # guest account must be loaded - this account performs the signup
def signup():
	try:
		check_args(request.args, 'data')
		g.user.update(request.args['data'])

		#reset permissions
		#remove _id to make new account
		#save to db
	except Exception as error:
		return error_dump(error)

	return {'notify': 'signup successful'}


@app.route('/admin/task/reset')
@permission_required('reset_db')
def reset_db():
	db.reset()
	user.create_default_users()
	return {'notify': 'reset successful'}


if __name__ == "__main__":
	app.run(
		debug=True,
		host='0.0.0.0',  # make dev server public
	)
