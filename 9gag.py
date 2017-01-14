import requests
import sys
import re

login_data = {'username': '***', 'password': '***'}

BASE_URL = 'https://9gag.com'
LOGIN = '/login'
NOTIFICATION = '/notifications/load_more'

COMMENT_MENTION_REGEX = re.compile('<li [^>]* data-actionType="COMMENT_MENTION" [^>]*>')
COMMENT_ID_REGEX = re.compile('.*data-objectId="http://9gag.com/gag/([^#]*)#([^"]*)".*')

last_notification_parsed = ''

def login(session):
	session.post(BASE_URL + LOGIN, data=login_data)

def get_new_notifications(session):
	global last_notification_parsed
	r = session.get(BASE_URL + NOTIFICATION)
	notifs = COMMENT_MENTION_REGEX.findall(r.text)

	comments = []

	for notif in notifs:
		m = COMMENT_ID_REGEX.match(notif)
		if m.group(2) == last_notification_parsed:
			break
		comments.append((m.group(1), m.group(2)))

	if len(comments) > 0:
		last_notification_parsed = comments[0][1]
	return comments


if __name__ == '__main__':
	session = requests.session()
	print 'logging in'
	login(session)
	print 'logged in'
	print get_new_notifications(session)
