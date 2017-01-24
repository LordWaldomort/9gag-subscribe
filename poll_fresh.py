import requests
import json
import time
import sqlite3
import threading

ngag = __import__("9gag")

posts_processed=[]

BASE_URL = "http://9gag.com"
COMMENT_URL = "http://comment-cdn.9gag.com/v1/cacheable/comment-list.json?appId=a_dd8f2b7d304a10edaf6f29517ea0ca4100a43d1b&count=0&url=http%3A%2F%2F9gag.com%2Fgag%2F"
first_start = True

posts_to_comment = {}
db_conn = 0
max_tags_in_comment = 10


session=0

def get_new_posts():
	global posts_processed
	global first_start
	load_url = "/fresh"
	return_ids = []
	global posts_to_comment
	hit_last = False
	while hit_last == False:	
		response = requests.get(BASE_URL+load_url, headers={"X-Requested-With":"XMLHttpRequest", "Accept":"application/json, text/javascipt, */*; q=0.01"})
		try:
			ids = response.json()["ids"]
		except ValueError as e:
			print e
			print "Skipping cycle!"
			print "Might happen again"
			continue
		hit_last = first_start
		first_start = False
		for id in ids:
			if id in posts_processed:
				print "Found last point at", id
				hit_last = True
				break
			return_ids+=[id]
			posts_to_comment[id]=0
			posts_processed+=[id]
		load_url = response.json()["loadMoreUrl"]
	return return_ids



def get_op_id(post_id):
	response = requests.get(COMMENT_URL+post_id)
	try:
		response_json = response.json()
	except ValueError as e:
		print e
		print "Skipping post", post_id
		print "Post not handled"
		return ""
	return response_json["payload"]["opUserId"]



def comment_on_post(post_id, op_user_id):
	global db_conn
	global session
	tag_ids = db_conn.execute("select name from subscriptions, user_id_to_name where op_id='"+op_user_id+"' and subscriptions.subscriber_id = user_id_to_name.user_id;").fetchall()
	counter = 0
	comment_text = ""
	while counter < len(tag_ids):
		comment_text += "@"+tag_ids[counter][0]+", "
		counter += 1
		if counter % 10 == 0:
			ngag.post_comment(session, post_id, comment_text)
			comment_text = ""
	if comment_text!="":
		ngag.post_comment(session, post_id, comment_text)
		comment_text = ""
	return None

def process_post_queue():
	for post_id in posts_to_comment.keys():
		op_user_id=get_op_id(post_id)
		if op_user_id != "":
			comment_on_post(post_id, op_user_id)
			del posts_to_comment[post_id]
		else:
			posts_to_comment[post_id]+=1
			if posts_to_comment[post_id] == 5:
				del posts_to_comment[post_id]

def init_9gag_py():	
	global session
	ngag.get_login_credentials()
	session = requests.session()
	print 'logging in'
	ngag.login(session)
	print 'logged in'


keep_running = True

def post_polling_thread():
	global keep_running
	while keep_running:
		print "Polling new posts"
		get_new_posts()
		for i in range(60):
			if keep_running == False:
				break
			time.sleep(1)
def post_commenting_thread():
	global keep_running
	global db_conn
	db_conn = sqlite3.connect("subscription_data.db")
	while keep_running:
		print "Processing comment queue"
		process_post_queue()
		print posts_to_comment
		for i in range(300):
			if keep_running == False:
				break
			time.sleep(1)


def main():
	global keep_running
	init_9gag_py()
	t1=threading.Thread(target=post_polling_thread)
	t1.start()
	time.sleep(10)
	t2=threading.Thread(target=post_commenting_thread)
	t2.start()
	try:
		while 1:
			time.sleep(1)
	except KeyboardInterrupt:
		print "Closing threads, might have to wait for maximum 1 seconds"
		keep_running = False
		t1.join()
		t2.join()
		print "Threads closed"
		print "EXIT"
if __name__ == "__main__":
	main()
