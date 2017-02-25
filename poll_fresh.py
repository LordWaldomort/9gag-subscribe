import requests
import json
import time
import sqlite3
import threading
import os
ngag = __import__("9gag")

posts_processed=[]

BASE_URL = "http://9gag.com"
COMMENT_URL = "http://comment-cdn.9gag.com/v1/cacheable/comment-list.json?appId=a_dd8f2b7d304a10edaf6f29517ea0ca4100a43d1b&count=0&url=http%3A%2F%2F9gag.com%2Fgag%2F"
first_start = True

posts_to_comment = {}
db_conn = 0
max_tags_in_comment = 3

dump_file_post_array = "poll_data_post_array.json"
dump_file_comment_map = "poll_data_comment_map.json"

session=0

def read_dump_files():
	global posts_processed
	global posts_to_comment
	global first_start
	if os.path.exists(dump_file_post_array):
		f=open(dump_file_post_array)
		posts_processed = json.loads(f.read())
		f.close()
		first_start = False
		print "First start set to false"
	if os.path.exists(dump_file_comment_map):
		f=open(dump_file_comment_map)
		posts_to_comment = json.loads(f.read())
		f.close()


def get_new_posts():
	global posts_processed
	global first_start
	load_url = "/fresh"
	return_ids = []
	global posts_to_comment
	hit_last = False
	while hit_last == False:
		try:
			response = requests.get(BASE_URL+load_url, headers={"X-Requested-With":"XMLHttpRequest", "Accept":"application/json, text/javascipt, */*; q=0.01"})
		except:
			continue
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
	try:
		response = requests.get(COMMENT_URL+post_id)
	except:
		return ""
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
	global max_tags_in_comment
	tag_ids = db_conn.execute("select name from subscriptions, user_id_to_name where op_id='"+op_user_id+"' and subscriptions.subscriber_id = user_id_to_name.user_id;").fetchall()
	chunk_size = max_tags_in_comment

	for i in xrange(0, len(tag_ids), chunk_size):
		comment_text = ' '.join(map(lambda x: '@' + x[0], tag_ids[i:i+chunk_size])) + ' this might interest you - ' + post_id + '.'
		print "Commenting", post_id, comment_text
		ngag.post_comment(session, post_id, comment_text)

def process_post_queue():
	global session
	rejected_list = ""
	for post_id in posts_to_comment.keys():
		if posts_to_comment[post_id] > 4:
			comment_id = ngag.post_comment(session, post_id, "Test comment for "+post_id, True)
			if comment_id != False:
				ngag.delete_comment(session, post_id, comment_id)
		op_user_id=get_op_id(post_id)
		if op_user_id != "":
			comment_on_post(post_id, op_user_id)
			del posts_to_comment[post_id]
		else:
			posts_to_comment[post_id]+=1
			if posts_to_comment[post_id] == 10:
				rejected_list += (post_id + "\n")
				del posts_to_comment[post_id]
	
	file_handle = open("dropped_posts.txt", "a")
	file_handle.write(rejected_list)
	file_handle.close()

def init_9gag_py():
	global session
	ngag.get_login_credentials()
	session = requests.session()
	print 'logging in'
	ngag.login(session)
	print 'logged in'

keep_running = True
def relogin_thread():
	global keep_running
	global session
	first_login = False
	while keep_running:
		if first_login:
			session = requests.session()
			print 'loggin in'
			ngag.login(session)
			print 'logged in'
		else:
			first_login = True	
		for i in range(18000):
			if keep_running == False:
				break
			time.sleep(1)
			




def dump_post_array_to_file():
	global posts_processed
	if len(posts_processed) > 150:
		posts_processed = posts_processed[-100:]
	f=open(dump_file_post_array,"w+")
	f.write(json.dumps(posts_processed))
	f.close()
def dump_comment_map_to_file():
	global posts_to_comment
	f=open(dump_file_comment_map, "w+")
	f.write(json.dumps(posts_to_comment))
	f.close()

	
	

def post_polling_thread():
	global keep_running
	global posts_processed
	while keep_running:
		print "Polling new posts"
		get_new_posts()
		dump_post_array_to_file()
		dump_comment_map_to_file()		
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
		dump_comment_map_to_file()		
		for i in range(300):
			if keep_running == False:
				break
			time.sleep(1)
	db_conn.close()

def main():
	global keep_running
	init_9gag_py()
	read_dump_files()
	t1=threading.Thread(target=post_polling_thread)
	t1.start()
	time.sleep(10)
	t2=threading.Thread(target=post_commenting_thread)
	t2.start()
	t3=threading.Thread(target=relogin_thread)
	t3.start()
	try:
		while 1:
			time.sleep(1)
	except KeyboardInterrupt:
		print "Closing threads, might have to wait for maximum 1 seconds"
		keep_running = False
		t1.join()
		t2.join()
		t3.join()
		print "Threads closed"
		print "EXIT"

if __name__ == "__main__":
	main()
