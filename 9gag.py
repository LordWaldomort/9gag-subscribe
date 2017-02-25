import ConfigParser
import json
import os
import requests
import sqlite3
import sys
import time
import re

CONFIG_FILE = 'config.cfg'
SQLITE_DB_FILE = 'subscription_data.db'
NOTIFICATIONS_DUMP_FILE = 'notifications_processed.json'
TAGGER_BOT_DISPLAY_NAME = '@post_tagger'
COMMAND_SUBSCRIBE = 'subscribe'

APP_ID = 'a_dd8f2b7d304a10edaf6f29517ea0ca4100a43d1b'

BASE_URL = 'https://9gag.com'
LOGIN = '/login'
CACHEABLE = '/cacheable'
NOTIFICATION = '/notifications/load-more?refKey='
COMMENT_LIST_URL = 'http://comment.9gag.com/v1/comment-list.json'
COMMENT_POST_URL = 'http://comment.9gag.com/v1/comment.json'

COMMENT_MENTION_REGEX = re.compile('<li [^>]* data-actionType="COMMENT_MENTION" [^>]*>')
COMMENT_REPLY_REGEX = re.compile('<li [^>]* data-actionType="COMMENT_REPLY" [^>]*>')
COMMENT_ID_REGEX = re.compile('.*data-objectId="http://9gag.com/gag/([^#]*)#([^"]*)".*')
NOTIFICATION_NEXT_KEY_REGEX = re.compile('<li class=".*badge-notification-nextKey[^"]*">([^<]*)</li>')

OPCLIENTID_REGEX =  re.compile("'opClientId': '([^']*)'")
OPSIGNATURE_REGEX =  re.compile("'opSignature': '([^']*)'")

login_data = {'username': '***', 'password': '***'}
notifications_processed = []
cacheable = {}

def read_dump_files():
	global notifications_processed
	if os.path.exists(NOTIFICATIONS_DUMP_FILE):
		f = open(NOTIFICATIONS_DUMP_FILE)
		notifications_processed = json.load(f)
		f.close()
		print 'Read notifications_processed from file'

def write_dump_files():
	print 'Dumping notifications_processed'
	global notifications_processed
	if len(notifications_processed) > 150:
		notifications_processed = notifications_processed[-100:]
	f = open(NOTIFICATIONS_DUMP_FILE, 'w+')
	json.dump(notifications_processed, f)
	f.close()

def get_login_credentials():
	cfg = ConfigParser.ConfigParser()
	cfg.read(CONFIG_FILE)
	login_data['username'] = cfg.get('credentials', 'username')
	login_data['password'] = cfg.get('credentials', 'password')

def login(session):
	try:
		session.post(BASE_URL + LOGIN, data=login_data)
	except:
		print "Couldn't login"
		exit(-1)
		return False
	data = {"json":'[{"action":"vote","params":{}},{"action":"user","params":{}},{"action":"user-preference","params":{}},{"action":"user-quota","params":{}}]'}
	headers = {
		"X-Requested-With": "XMLHttpRequest",
		"Accept": "application/json, text/javascipt, */*; q=0.01",
	}
	try:
		r = session.post(BASE_URL + CACHEABLE, data=data, headers=headers)
	except:
		print 'Couldn\' get cacheable: ', r, e
		exit()

	global cacheable
	try:
		cacheable = r.json()
	except ValueError as e:
		print 'Couldn\' get cacheable: ', r, e
		exit()


def get_new_notifications(session):
	comments = []
	found_last = False
	next_key = ''

	while not found_last:
		try:
			r = session.get(BASE_URL + NOTIFICATION + next_key)
		except:
			continue
		notifs = COMMENT_MENTION_REGEX.findall(r.text) + COMMENT_REPLY_REGEX.findall(r.text)
		for notif in notifs:
			m = COMMENT_ID_REGEX.match(notif)
			if m.group(2) in notifications_processed:
				found_last = True
				break
			comments.append((m.group(1), m.group(2)))
			notifications_processed.append(m.group(2))
		next_key_all = NOTIFICATION_NEXT_KEY_REGEX.findall(r.text)
		if len(next_key_all) == 0 or len(next_key_all[0]) == 0:
			break
		next_key = next_key_all[0]	# Assume first one to be the correct one
	return comments

def get_subscription_from_comment(session, post_id, comment_id):
	data = {
		'appId': APP_ID,
		'url': 'http://9gag.com/gag/' + post_id,
		'count': 0,
		'level': 1,
		'commentId': comment_id,
	}
	try:
		r = session.post(COMMENT_LIST_URL, data=data)
	except:
		print e
		return None
	try:
		result = r.json()
	except ValueError as e:
		print e
		return None

	if result['status'] != 'OK':
		return None

	opclient_data = get_opclient_data(post_id)
	if not opclient_data:
		return None

	op_id = opclient_data[0]
	if len(op_id) == 0 or op_id == '0':
		# TODO handle no OP case
		return None


	comments = result['payload']['comments']

	if len(comments) == 0:
		return None

	comments_to_process = [comments[0]] + comments[0]["children"]

	chosen_comment = None
	for comment in comments_to_process:
		if comment['commentId'] == comment_id:
			chosen_comment = comment
			break

	if not chosen_comment:
		return None

	comment_text = chosen_comment['text']
	if comment_text.startswith(TAGGER_BOT_DISPLAY_NAME + ' ' + COMMAND_SUBSCRIBE):
		return None

	subscriber_name = chosen_comment['user']['displayName']
	subscriber_id = chosen_comment['user']['userId']

	return (op_id, subscriber_name, subscriber_id)

def get_opclient_data(post_id):
	try:
		response = requests.get("http://9gag.com/gag/"+post_id)
	except:
		return None
	client_id = OPCLIENTID_REGEX.findall(response.text)
	client_signature = OPSIGNATURE_REGEX.findall(response.text)
	if len(client_id) == 1 and len(client_signature) == 1:
		return client_id[0], client_signature[0]

def post_comment(session, post_id, text, withClient=False):
	data = {
		'appId': APP_ID,
		'url': 'http://9gag.com/gag/' + post_id,
		'text': text,
		'isAnonymous': 'off',
		'auth': cacheable['user']['commentSso']
	}
	if withClient == True:
		opclient_data = get_opclient_data(post_id)
		if not opclient_data:
			return False
		data["opClientId"] = opclient_data[0]
		data["opSignature"] = opclient_data[1]
	try:
		r = session.post(COMMENT_POST_URL, data=data)
	except:
		return False
	try:
		result = r.json()
	except ValueError as e:
		print r, e
		return False
	if result['status'] != 'OK':
		print result
		return False
	print "Quota =",result["payload"]["quota"]["count"]
	print "opUserId =", result["payload"]["opUserId"]
	return result["payload"]["comment"]["commentId"]
def delete_comment(session, post_id, comment_id):
	data = {
		'appId' : APP_ID,
		'url' : 'http://9gag.com/gag/' + post_id,
		'auth' : cacheable['user']['commentSso'],
		'_method' : 'DELETE',
		'id' : comment_id
	}
	try:
		r = session.post(COMMENT_POST_URL, data=data)
        except:
		return False
	try:
                result = r.json()
        except ValueError as e:
                print r, e
                return False
        if result['status'] != 'OK':
                print result
                return False
	print "Deleted comment for", post_id
        print "Quota =",result["payload"]["quota"]["count"]
        return True

def add_subscription(sql_conn, op_id, subs_id, post_id):
	if op_id == subs_id:
		print 'Smartass user', op_id, ' subscribing to themself'
		return
	existing = sql_conn.execute("""
			SELECT COUNT(*)
			FROM subscriptions
			WHERE op_id = '{}'
				AND subscriber_id = '{}'
		""".format(op_id, subs_id)).fetchall()[0][0]
	if existing > 0:
		print 'existing', op_id, subs_id
		return

	sql_conn.execute("""
			INSERT INTO subscriptions (op_id, subscriber_id, post_id)
			VALUES ('{}', '{}', '{}')
		""".format(op_id, subs_id, post_id))

	sql_conn.commit()

def update_mapping(sql_conn, user_id, user_name):
	existing = sql_conn.execute("""
			SELECT COUNT(*)
			FROM user_id_to_name
			WHERE user_id = '{}'
		""".format(user_id)).fetchall()[0][0]
	if existing > 0:
		sql_conn.execute("""
				UPDATE user_id_to_name
				SET name = '{}'
				WHERE user_id = '{}'
			""".format(user_name, user_id))
	else:
		sql_conn.execute("""
				INSERT INTO user_id_to_name (user_id, name)
				VALUES ('{}', '{}')
			""".format(user_id, user_name))

	sql_conn.commit()

def update_subscriptions(session, sql_conn):
	notifs = get_new_notifications(session)
	print 'Found', len(notifs), 'new notifications'
	for notif in notifs:
		subscription = get_subscription_from_comment(session, notif[0], notif[1])
		if subscription is None:
			continue
		op_id, subs_name, subs_id = subscription
		add_subscription(sql_conn, op_id, subs_id, notif[0])
		update_mapping(sql_conn, subs_id, subs_name)
	write_dump_files()

def main():
	sql_conn = sqlite3.connect(SQLITE_DB_FILE)
	get_login_credentials()
	session = requests.session()
	print 'logging in'
	login(session)
	print 'logged in'

	read_dump_files()

	try:
		while True:
			print 'Updating subscriptions'
			update_subscriptions(session, sql_conn)
			time.sleep(60)
	except KeyboardInterrupt:
		print 'Got KeyboardInterrupt'
		sql_conn.close()
		print 'EXIT'

if __name__ == '__main__':
	main()
