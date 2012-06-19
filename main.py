import model.helper as helper
#import browseDb.main as browseDb
#from threading import Timer
import os
import model.user as user
import db as db
from override_flask import Flask
from flask import request, send_from_directory, abort, g

app = Flask(__name__,)

db.check()  # make sure mongo is setup


@app.before_request
def before_request():
	g.notify = []  # an array that holds notifications (like non-fatal errors or important messages)

	# a variable that holds an error... if there is one (there should be 1 or 0 errors returned)
	# a error is formatted as ('title','discription')
	#	title: one word name for the error
	#	discription: text givent to the user to tell what happened/how to fix
	g.error = ()

	g.user = user.Instance()  # starts out as guest user, store user object in g (thread safe context)

	try:  # try to authenticate
		g.user.check(username=request.args['username'], token=request.args['token'], ip=request.remote_addr)  # validate user token if username and token are supplied
	except KeyError:
		pass  # one or more of the attributes was/were not defined, proceed with guest status
	except Exception as error:
		return helper.error_dump(error)


@app.after_view
def after_view(rv):
	if not type(rv) in (dict, list):  # check to see that it's json, if not then return
		return
	#put stuff from g in response
	return


@app.route('/favicon.ico')
def favicon():
	"""send the favicon from the typical location at /favicon.ico"""
	return send_from_directory(
		os.path.join(app.root_path, 'static'),
		'favicon.ico',
		mimetype='image/vnd.microsoft.icon',
		cache_timeout=60 * 60 * 24 * 365 * 5,  # set cache timeout to 5 years
	)


# @app.route('/<path:filename>', subdomain="static")
# def static(filename):
# 	"""send static files from separate sub-domain"""
# 	return send_from_directory(
# 		app.static_folder,
# 		filename,
# 	)


@app.route('/')
def index():
	return """
		<!DOCTYPE html>
		<html>
			<head>
				<title>CSD</title>
			</head>
			<body>
				<p>put docs generated by sphinx here</p>
			</body>
		</html>
	"""


@app.route('/test')
def json():
	import model.scraper.event as event
	return event.getEventList(request.args['year'])


#TODO: add mongs like db browser, with option to only return json (read only?) (restricted - not able to read user collection)


# def cron():
# 	"""handles simple cron-like jobs such as rescraping"""
# 	print "cron jobs can be put here"
# 	t = Timer(10000, cron)
# 	t.start()

# cron()


# 	inputs = web.input(username='', token='')
# 	#only run user.check if username and token are defined... still allows use of default guest account


# app.add_processor(processor)


@app.route('/user/<action>')
def user_request(action):
	"""
		handles requests for:
			data - returns client-safe data
			logins - returns token
			signups
	"""

	if action == 'data':
		return g.user.safe_data()
	elif action == 'login':
		#CONSIDER: add a delay to prevent excessive attempts

		try:
			helper.check_args(('username', 'password'), request.args)
		except Exception as error:
			return helper.error_dump(error)

		try:
			g.user.login(username=request.args['username'], password=request.args['password'], ip=request.remote_addr)
		except Exception as error:
			return helper.error_dump(error)  # bad info supplied

		return {'token': g.user.data['session']['token']}

	# signup and update are actually the same thing, just seperated in case I need to change something in the future
	elif action == 'signup' or action == 'update':
		try:
			helper.check_args(('data'), request.args)
		except Exception as error:
			return helper.error_dump(error)

		try:
			g.user.update(request.args['data'])
		except Exception as error:
			return helper.error_dump(error)

		return {'notify': action + ' successful'}

	else:
		return abort(404)  # not one of the defined methods for interacting w/ the server


@app.route('/admin/task/<task>')
def admin_task(task):
	"""used for running admin tasks manually (they can also be triggered by cron/timed tasks)"""

	if not g.user.can('run_admin_task'):
		return {'error': 'invalid permissions'}

	if task == 'reset':
		db.reset()
		return {'notify': 'reset successful'}
	else:
		return abort(404)  # not one of the defined methods for interacting w/ the server

if __name__ == "__main__":
	app.run(debug=True)
