import requests
import json
import time
posts_processed=["aG0m1Y6"]

BASE_URL = "http://9gag.com"
COMMENT_URL = "http://comment-cdn.9gag.com/v1/cacheable/comment-list.json?appId=a_dd8f2b7d304a10edaf6f29517ea0ca4100a43d1b&count=0&url=http%3A%2F%2F9gag.com%2Fgag%2F"
first_start = True

def get_new_posts():
	global posts_processed
	global first_start
	load_url = "/fresh"
	return_ids = []
	hit_last = False
	while hit_last == False:	
		response = requests.get(BASE_URL+load_url, headers={"X-Requested-With":"XMLHttpRequest", "Accept":"application/json, text/javascipt, */*; q=0.01"})
		ids = response.json()["ids"]
		hit_last = first_start
		first_start = False
		for id in ids:
			if id in posts_processed:
				print "Found last point at", id
				hit_last = True
				break
			return_ids+=[id]
			
			posts_processed+=[id]
		load_url = response.json()["loadMoreUrl"]
	return return_ids


def get_ops(post_ids):
	op_list=[]
	for post_id in post_ids:
		response = requests.get(COMMENT_URL+post_id)
		response_json = response.json()
		op_id = response_json["payload"]["opUserId"]
		if op_id != "":
			op_list += [(post_id, op_id)]
	return op_list

if __name__ == "__main__":
	while 1:
		print "Polling new posts"
		print get_ops(get_new_posts())
		time.sleep(60)
