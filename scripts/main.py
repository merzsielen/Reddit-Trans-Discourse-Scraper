import os
import time
import praw
import torch
from nltk.tokenize import word_tokenize, sent_tokenize
from transformers import AutoTokenizer, AutoModelForSequenceClassification, AutoModelForMaskedLM

###################################################################################################
# Settings                                                                                        #
###################################################################################################

client_id_path = os.path.dirname(__file__) + "/../settings/id"
client_secret_path = os.path.dirname(__file__) + "/../settings/secret"
user_agent_path = os.path.dirname(__file__) + "/../settings/user_agent"

subreddit_list_path = os.path.dirname(__file__) + "/../settings/subreddit_list"
term_list_path = os.path.dirname(__file__) + "/../settings/term_list"

output_path = os.path.dirname(__file__) + "/../output/flagged.txt"

posts_per_minute = 80
posts_per_subreddit = 200
subreddits_per_minute = posts_per_subreddit / posts_per_minute

desired_entries = 10000

###################################################################################################
# Classes                                                                                         #
###################################################################################################

class Submission:
	id = ""
	author = ""
	title = ""
	body = ""
	subreddit = ""
	url = ""
	label = 0
	
	def __init__(self, id, author, title, body, subreddit, url):
		self.id = id
		self.author = author
		self.title = title
		self.body = body
		self.subreddit = subreddit
		self.url = url

class Comment:
	id = ""
	author = ""
	body = ""
	subreddit = ""
	url = ""
	label = 0

	parent_id = ""
	parent_author = ""
	parent_body = ""
	parent_url = ""
	parent_label = 0
	
	def __init__(self, id, author, body, subreddit, url, parent_id, parent_author, parent_body, parent_url):
		self.id = id
		self.author = author
		self.body = body
		self.subreddit = subreddit
		self.url = url
		
		self.parent_id = parent_id
		self.parent_author = parent_author
		self.parent_body = parent_body
		self.parent_url = parent_url

###################################################################################################
# Functions                                                                                       #
###################################################################################################

def GetFile(path):
	if os.path.isfile(path):
		return open(path, "r").read()
	return ""

def Scrape(term_list, subreddit_name, reddit):
	comments = []

	subreddit = reddit.subreddit(subreddit_name)
	print("Searching in /r/" + subreddit_name)

	##############################################################
	# Loop Through Hot Submissions                               #
	##############################################################
	for submission in subreddit.hot(limit=posts_per_subreddit):
		
		##############################################################
		# Loop Through Comments                                      #
		##############################################################
		submission.comments.replace_more(limit=0)
		for comment in submission.comments.list():
			com_text = comment.body.lower()
			com_tokens = word_tokenize(com_text)

			c_found_terms = []
					
			for tok in com_tokens:
				if (tok in term_list):
					c_found_terms.append(tok)

			if (len(c_found_terms) > 0):
				# We need to find the parent and grab its info.
				parent_id = comment.parent_id
				p = [c for c in submission.comments.list() if (c.id == parent_id[3:])]
				
				ci = 0
				ca = ""
				cb = ""
				cs = ""
				cu = ""

				ci = comment.id
				if (comment.author != None):
					ca = comment.author.name
				cb = comment.body
				cs = submission.subreddit.display_name
				cu = comment.permalink

				pi = 0
				pa = ""
				pb = ""
				pu = ""

				if (len(p) > 0):
						pi = p[0].id
						# It isn't entirely clear to me why this is coming back
						# as a NoneType in rare circumstances.
						if (p[0].author != None):
							pa = p[0].author.name
						pb = p[0].body
						pu = p[0].permalink

				c = Comment(ci, ca, cb, cs, cu,
				pi, pa, pb, pu)

				comments.append(c)

	return comments

###################################################################################################
# Main                                                                                            #
###################################################################################################

def main():
	##############################################################
	# Credentials & Setup                                        #
	##############################################################
	term_list = GetFile(term_list_path).split(',')
	subreddit_list = GetFile(subreddit_list_path).split(',')

	reddit = praw.Reddit(client_id=GetFile(client_id_path),
					  client_secret=GetFile(client_secret_path),
					  user_agent=GetFile(user_agent_path))
	
	current_subreddit = 0
	flagged_comments = []

	##############################################################
	# Main Loop                                                  #
	##############################################################
	while(True):
		t0 = time.monotonic()

		##############################################################
		# Scrape                                                     #
		##############################################################
		sub_name = subreddit_list[current_subreddit]
		new_coms = Scrape(term_list, sub_name, reddit)

		##############################################################
		# Loop Over New Comments                                     #
		##############################################################
		old_coms = flagged_comments

		print("-------------------------------------------------------------")
		print("New Comments")
		print("-------------------------------------------------------------")
		for n in new_coms:
			found = False
			for o in old_coms:
				if (n.url == o.url):
					found = True
			if (not found):

				flagged_comments.append(n)

				print()
				print("-------------------------------------------------------------")
				print(n.author)
				print(n.body)
				# print(n.subreddit)
				print(n.url)
				# print(labels[n.label])
				if (n.parent_id != 0):
					print("-----------------------------")
					print("Parent:")
					print(n.parent_author)
					print(n.parent_body)
					print("-----------------------------")
				print("-------------------------------------------------------------")
				print()

		print("Entries found: " + str(len(flagged_comments)))
		if (len(flagged_comments) >= desired_entries):
			break

		# Get next subreddit.
		current_subreddit = (current_subreddit + 1) % len(subreddit_list)

		t1 = time.monotonic()
		time.sleep(max(1, (float(subreddits_per_minute * 60) - (t1 - t0))))

	output = ""

	output += "##############################################################" + "\n"
	output += "# Comments                                                   #" + "\n"
	output += "##############################################################" + "\n"
	
	for n in flagged_comments:
		output += "Author: /u/" + n.author + "\n"
		output += "Text: " + n.body + "\n"
		output += "Subreddit: /r/" + n.subreddit + "\n"
		output += "URL:" + n.url + "\n"
		output += "##############################################################" + "\n"

	file = open(output_path, 'w', encoding='utf8')
	file.write(output)
	file.close()

if __name__ == '__main__':
    main()