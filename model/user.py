from mongo_descriptors import Db, MongoI, CatDict
from os import urandom
from time import time
from passlib.context import CryptContext

from config import app
from model.db import database as db


pwd_context = CryptContext(
	schemes=["sha512_crypt"],
	default="sha512_crypt",
	all__vary_rounds=0.1
)


def auth(name, password, ip=None):
	user = db.user.find_one(name)
	if not password:
		password = ""
	if not user:
		return None
	if pwd_context.verify(password, user["password"]):
		user = User(name)
		user.new_session(ip)
		return user
	else:
		return False


def token_auth(token, ip=None):
	user = db.user.find_one({"token": str(token)})
	if not user:
		return None
	if ip and not app.config["ALLOW_TOKENS_TO_CHANGE_IP"]:
		if user.ip != ip:
			return False
	else:
		return User(user['_id'])


class User(object):
	db = Db(db=db['user'])
	raw = MongoI()

	password = MongoI("password")
	perms = MongoI("perms", typ=list)

	token = MongoI("token")
	ip = MongoI("ip")
	startTime = MongoI('startTime')

	############
	public_attrs = ['email', 'team', 'fullname']

	email = MongoI("email", typ=str)
	team = MongoI("team", typ=int)
	fullname = MongoI("fullname", typ=str)

	def __init__(self, name, create=False):
		self.oi = str(name)
		if not exists(self.oi):
			if create:
				self.db.insert({"_id": self.oi})
			else:
				raise ValueError("No user " + self.oi)

	def passwd(self, password):
		self.password = pwd_context.encrypt(password)

	def has_perm(self, perm):
		perm = str(perm)
		if "-" + perm in self.perms:
			return False
		if "*" in self.perms:
			return True
		return perm in self.perms

	def give_perm(self, perm):
		if not perm in self.perms:
			self.perms += [str(perm)]

	def new_session(self, ip):
		self.logout()

		self.token = urandom(app.config["TOKEN_LENGTH"]).encode('base64')
		self.ip = ip
		self.startTime = time()

	def logout(self):
		#move old session into log?

		self.token = None
		self.ip = None
		self.startTime = None

	def __repr__(self):
		return str(self.oi) + " (" + self.fullname + ")"

	def to_dict(self):
		ret = {'name': self.oi}
		for i in self.public_attrs:
			ret[i] = getattr(self, i)
		return ret


def new_user(name, password, **kw):
	import model.log
	user = User(name, create=True)

	user.passwd(password)

	for i in User.public_attrs:
		if i in kw.keys():
			user.raw += {i: kw[i]}
	model.log.security("New user ", user.oi, " ", str(user.raw))
	return user


def exists(user):
	return User.db.find_one(user)


def defaults():
	user = new_user("admin", 'mApru', fullname="Kai'ckul")
	user.give_perm("*")
	user = new_user('test-user', 'm3jhrk4')


def list_users():
	users = db.user.find()
	ret = []
	for user in users:
		ret.append(
			User(user["_id"])
		)
	return ret
