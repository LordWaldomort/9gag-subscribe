import ConfigParser
import requests
import sys
import re

CONFIG_FILE = 'config.cfg'
TAGGER_BOT_DISPLAY_NAME = '@post_tagger'
COMMAND_SUBSCRIBE = 'subscribe'

BASE_URL = 'https://9gag.com'
LOGIN = '/login'
NOTIFICATION = '/notifications/load-more?refKey='
COMMENT_URL = 'http://comment.9gag.com/v1/comment-list.json'

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

def get_subscription_from_comment(session, post_id, comment_id):
	data = {
		'appId': 'a_dd8f2b7d304a10edaf6f29517ea0ca4100a43d1b',
		'url': 'http://9gag.com/gag/' + post_id,
		'count': 0,
		'level': 1,
		'commentId': comment_id,
	}
	r = session.post(COMMENT_URL, data=data)
	result = r.json()
	if result['status'] != 'OK':
		return None

	op = result['payload']['opUserId']
	if len(op) == 0:
		# TODO handle no OP case
		return None
	comments = result['payload']['comments']
	if len(comments) == 0:
		return None

	comment_text = comments[0]['text']
	if comment_text != (TAGGER_BOT_DISPLAY_NAME + ' ' + COMMAND_SUBSCRIBE):
		return None

	subscriber_display_name = comments[0]['user']['displayName']
	subscriber_user_id = comments[0]['user']['userId']

	return (op, subscriber_display_name, subscriber_user_id)

def main():
	get_login_credentials()
	session = requests.session()
	print 'logging in'
	login(session)
	print 'logged in'
	notifs = get_new_notifications(session)
	print 'getting comments'
	for notif in notifs:
		print get_subscription_from_comment(session, notif[0], notif[1])

if __name__ == '__main__':
	main()
