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

total_post_limit = 80

cooldown = 72

###################################################################################################
# Classes                                                                                         #
###################################################################################################

class Submission:
	author = ""
	title = ""
	body = ""
	subreddit = ""
	url = ""
	label = 0
	
	def __init__(self, author, title, body, subreddit, url):
		self.author = author
		self.title = title
		self.body = body
		self.subreddit = subreddit
		self.url = url

class Comment:
	author = ""
	body = ""
	subreddit = ""
	url = ""
	label = 0
	
	def __init__(self, author, body, subreddit, url):
		self.author = author
		self.body = body
		self.subreddit = subreddit
		self.url = url

###################################################################################################
# Functions                                                                                       #
###################################################################################################

def GetFile(path):
	if os.path.isfile(path):
		return open(path, "r").read()
	return ""

def Scrape(term_list, subreddit_list, reddit):
	submissions = []
	comments = []

	post_limit = round(total_post_limit / len(subreddit_list))

	##############################################################
	# Loop Through Subreddits                                    #
	##############################################################
	for subreddit_name in subreddit_list:
		subreddit = reddit.subreddit(subreddit_name)
		print("Searching in /r/" + subreddit_name)

		##############################################################
		# Loop Through Hot Submissions                               #
		##############################################################
		for submission in subreddit.hot(limit=post_limit):
			sub_text = submission.title.lower() + " :: " + submission.selftext.lower()
			sub_tokens = word_tokenize(sub_text)
				
			s_found_terms = []

			for tok in sub_tokens:
				if (tok in term_list):
					s_found_terms.append(tok)

			if (len(s_found_terms) > 0):
				s = Submission(submission.author,
				submission.title,
				submission.selftext,
				submission.subreddit.display_name,
				submission.url)
					
				submissions.append(s)

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
					c = Comment(comment.author,
					comment.body,
					submission.subreddit.display_name,
					comment.permalink)
					
					comments.append(c)

	return submissions, comments

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
	
	flagged_submissions = []
	flagged_comments = []

	# tokenizer = AutoTokenizer.from_pretrained("Hate-speech-CNERG/dehatebert-mono-english")
	# model = AutoModelForSequenceClassification.from_pretrained("Hate-speech-CNERG/dehatebert-mono-english")

	# labels = ["Neutral", "Hateful"]

	##############################################################
	# Main Loop                                                  #
	##############################################################
	while(True):
		t0 = time.monotonic()
		print("Waking up!")
		print()

		##############################################################
		# Scrape                                                     #
		##############################################################
		new_subs, new_coms = Scrape(term_list, subreddit_list, reddit)

		##############################################################
		# Loop Over New Submissions & Comments                       #
		##############################################################
		old_subs = flagged_submissions
		old_coms = flagged_comments

		print("-------------------------------------------------------------")
		print("Submissions")
		print("-------------------------------------------------------------")
		for n in new_subs:
			found = False
			for o in old_subs:
				if (n.url == o.url):
					found = True
			if (not found):
				
				# inputs = tokenizer(n.body, truncation=True, return_tensors="pt")

				# with torch.no_grad():
				# 	logits = model(**inputs).logits

				# n.label = logits.argmax().item()

				flagged_submissions.append(n)

				print()
				print("-------------------------------------------------------------")
				print(n.author)
				print(n.title)
				# print(n.subreddit)
				print(n.url)
				# print(labels[n.label])
				print("-------------------------------------------------------------")
				print()

		print("-------------------------------------------------------------")
		print("Comments")
		print("-------------------------------------------------------------")
		for n in new_coms:
			found = False
			for o in old_coms:
				if (n.url == o.url):
					found = True
			if (not found):

				# inputs = tokenizer(n.body, truncation=True, return_tensors="pt")

				# with torch.no_grad():
				# 	logits = model(**inputs).logits

				# n.label = logits.argmax().item()
				
				flagged_comments.append(n)

				print()
				print("-------------------------------------------------------------")
				print(n.author)
				print(n.body)
				# print(n.subreddit)
				print(n.url)
				# print(labels[n.label])
				print("-------------------------------------------------------------")
				print()

		print("Sleeping...")
		t1 = time.monotonic()
		time.sleep(max(1, cooldown - (t1 - t0)))

		if (len(flagged_submissions) + len(flagged_comments) > 1000):
			break

	output = ""

	output += "##############################################################" + "\n"
	output += "# Submissions                                                #" + "\n"
	output += "##############################################################" + "\n"
	
	for n in flagged_submissions:
		output += "Title: " + n.title
		output += "Author: /u/" + n.author
		output += "Text: " + n.body
		output += "Subreddit: /r/" + n.subreddit
		output += "URL:" + n.url

	output += "##############################################################" + "\n"
	output += "# Comments                                                   #" + "\n"
	output += "##############################################################" + "\n"
	
	for n in flagged_comments:
		output += "Author: /u/" + n.author
		output += "Text: " + n.body
		output += "Subreddit: /r/" + n.subreddit
		output += "URL:" + n.url

	file = open(output_path, "a")
	file.write(output)
	file.close()

if __name__ == '__main__':
    main()