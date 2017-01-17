import ConfigParser
import requests
import sys
import re

CONFIG_FILE = 'config.cfg'

BASE_URL = 'https://9gag.com'
LOGIN = '/login'
NOTIFICATION = '/notifications/load_more?refKey='

COMMENT_MENTION_REGEX = re.compile('<li [^>]* data-actionType="COMMENT_MENTION" [^>]*>')
COMMENT_ID_REGEX = re.compile('.*data-objectId="http://9gag.com/gag/([^#]*)#([^"]*)".*')
NOTIFICATION_NEXT_KEY_REGEX = re.compile('<li class=".*badge-notification-nextKey[^"]*">([^<]*)</li>')

login_data = {'username': '***', 'password': '***'}
last_notification_parsed = ''

def get_login_credentials():
	cfg = ConfigParser.ConfigParser()
	cfg.read(CONFIG_FILE)
	login_data['username'] = cfg.get('credentials', 'username')
	login_data['password'] = cfg.get('credentials', 'password')

def login(session):
	session.post(BASE_URL + LOGIN, data=login_data)

def get_new_notifications(session):
	global last_notification_parsed

	comments = []
	found_last = False
	next_key = ''

	while not found_last:
		r = session.get(BASE_URL + NOTIFICATION + next_key)
		notifs = COMMENT_MENTION_REGEX.findall(r.text)
		for notif in notifs:
			m = COMMENT_ID_REGEX.match(notif)
			if m.group(2) == last_notification_parsed:
				found_last = True
				break
			comments.append((m.group(1), m.group(2)))
		next_key_all = NOTIFICATION_NEXT_KEY_REGEX.findall(r.text)
		if len(next_key_all) == 0 or len(next_key_all[0]) == 0:
			break
		next_key = next_key_all[0]	# Assume first one to be the correct one

	if len(comments) > 0:
		last_notification_parsed = comments[0][1]
	return comments

def main():
	get_login_credentials()
	session = requests.session()
	print 'logging in'
	login(session)
	print 'logged in'
	print get_new_notifications(session)

if __name__ == '__main__':
	main()
