import csv # Exporting tweets
import datetime # Calculate rate of tweets
import json # Loading twitter credentials
import os # For finding console width
import pprint
import sys # For keyword 'track' arguments
from twython import TwythonStreamer # Gateway to Twitter

# Track filters and output file  can be passed as arguments
argv = sys.argv
outfile = "saved-tweets.csv" if len(argv) == 1 else sys.argv[1]

'''
Get keywords and labels from the user.
For example "bitcoin" : {"btc", "bitcoin", "satoshi nakamoto"}
Where "bitcoin" is the associated label for these search terms.
'''
def get_search_terms():
    groups = []
    terms = {}
    try:
        print("What do you want to search for?\n")
        print("Enter one topic per prompt.")
        print("Press enter when complete.\n")

        while True:
            label = input("Search label: ")
            if not label:
                raise ValueError("Done with labels")
            groups.append(label)
    except ValueError:
        print("\nEnter the keywords for your search.") 
        print("Press enter to continue.\n")
        for label in groups:
            terms[label] = [label]  
            try:
                
                while True:
                    keyword = input("Keyword for " + label + ": ")
                    if not keyword:
                        raise ValueError("Done with keywords")
                    if keyword not in terms[label]:
                        terms[label].append(keyword)
            except:
                continue
    except Exception as inst:
        print("Exception:", inst)
        print("Invalid input")
        sys.exit(1)
    
    return terms

'''
Used for sanitizing input for ADW
Credit: https://bit.ly/2NhKy4f
'''
def deEmojify(inputString):
    return inputString.encode('ascii', 'ignore').decode('ascii')

'''
This loads the most comprehensive text portion of the tweet  
Where "data" is an individual tweet, treated as JSON / dict
Inspired by: colditzjb @ https://github.com/tweepy/tweepy/issues/878
'''
def getText(data):       
    # Try for extended text of original tweet, if RT'd (streamer)
    try: text = data['retweeted_status']['extended_tweet']['full_text']
    except: 
        # Try for extended text of an original tweet, if RT'd (REST API)
        try: text = data['retweeted_status']['full_text']
        except:
            # Try for extended text of an original tweet (streamer)
            try: text = data['extended_tweet']['full_text']
            except:
                # Try for extended text of an original tweet (REST API)
                try: text = data['full_text']
                except:
                    # Try for basic text of original tweet if RT'd 
                    try: text = data['retweeted_status']['text']
                    except:
                        # Try for basic text of an original tweet
                        try: text = data['text']
                        except: 
                            # Nothing left to check for
                            text = ''
    return text

'''
This loads the most comprehensive text portion of the tweet  
Where "data" is an individual tweet, treated as JSON / dict
Inspired by: colditzjk @ https://github.com/tweepy/tweepy/issues/878
'''
def getHashtags(data):            
    try: text = data['quoted_status']['extended_tweet']['entities']['hashtags']
    except:
        # Try for extended text of original tweet, if RT'd (streamer)
        try: text = data['retweeted_status']['extended_tweet']['entities']['hashtags']
        except: 
            # Try for extended text of an original tweet, if RT'd (REST API)
            try: text = data['retweeted_status']['entities']['hashtags']
            except:
                # Try for basic text of original tweet if RT'd 
                try: text = data['retweeted_status']['entities']['hashtags']
                except:
                    # Try for basic text of an original tweet
                    try: text = data['entities']['hashtags']
                    except:
                        # Nothing left to check for
                        text = ''

    hashtags = []
    for entity in text:
        hashtags.append(entity["text"].lower())
    return text

# Filter out unwanted data
def process_tweet(tweet):
    # print(json.dumps(tweet, indent=2))
    d = {}
    d['tweet_date'] = tweet['created_at']
    d['hashtags'] = [hashtag['text'] for hashtag in getHashtags(tweet)]
    text = getText(tweet)
    text = deEmojify(text)
    text = text.lower().replace("\n", " ")
    d['text'] = text
    d['twitter_user'] = tweet['user']['screen_name']
    d['user_loc'] = tweet['user']['location']
    return d

'''
This extracts all aspects that are searched for in a tweet
Suggested extra_fields: "id_str", "retweet_count", "favorite_count", "created_at"
Returns a dictionary
Credit: https://gwu-libraries.github.io/sfm-ui/posts/2016-11-10-twitter-interaction
'''
def summarize(tweet, extra_fields = None):
    new_tweet = {}
    for field, value in tweet.items():
        if field in ['text', 'full_text', 'screen_name', 'expanded_url', 'display_url'] and value is not None:
            if field == 'created_at':
                new_tweet['tweet_date'] = tweet[field]
            elif field == 'text' or field == 'full_text':
                text = tweet[field]
                text = deEmojify(text)
                text = text.lower().replace('\n', ' ')
                new_tweet[field] = text
            elif field == 'screen_name':
                new_tweet['twitter_user'] = tweet[field]
            else:
                new_tweet[field] = value
        elif extra_fields and field in extra_fields:
            new_tweet[field] = value
        elif field == 'hashtags' and len(value):
            #new_tweet[field] = []
            #for hashtag in value:
            #    new_tweet[field].append(hashtag['text']) 
            for hashtag in value:
                summarize(hashtag)
        elif field == 'urls':
            if type(value) == list and len(value):
            #new_tweet[field] = []
                for link_dict in value:
                    new_tweet[field] = summarize(link_dict)
            #    new_tweet[field].append(link[

        elif field in ['retweeted_status', 'quoted_status', 'user', 'extended_tweet', 'entities']:
            if field:
                new_tweet[field] = summarize(value)
    return new_tweet


'''
We can use this to instead "tally" the occurences of each group
By changing to tweet[group] = 1
'''
def find_group(tweet, groups):
    for group, keywords in groups.items():
        if(find_keyword(tweet, keywords)):
            return group
    return 'misc'


def find_keyword(tweet, keywords):
    kw = set()
    if not tweet:
        return
    
    if type(tweet) == str: 
        for keyword in keywords:
            for word in keyword.split():
                if tweet.find(word) != -1:
                    return True
        return
    
    for key, value in tweet.items():
        find_keyword(value, keywords)
    
    return False
    
# Create a class that inherits TwythonStreamer
class MyStreamer(TwythonStreamer):
    # start_time = None
    # last_tweet_time = None
    # total_tweets = None
    # total_difference = None
    

    def __init__(self, *creds, groups, outfile):
        self.start_time = datetime.datetime.now()
        self.last_tweet_time =  self.start_time
        self.total_tweets = 0
        self.total_difference = 0
        self.groups = groups
        self.outfile = outfile
        super().__init__(*creds)  

    # Received data
    def on_success(self, data):
            
        
        # Only collect tweets in English
        if data['lang'] == 'en':
            self.total_tweets += 1
            # Calculate average time per tweet
            tweet_time = datetime.datetime.now()
            tweet_time_difference = tweet_time - self.last_tweet_time
            self.total_difference += tweet_time_difference.total_seconds()
            avg_time_per_tweet = self.total_difference / self.total_tweets
            self.last_tweet_time = tweet_time
            
            # Extract tweet and append to file
            basic = process_tweet(data)
            summary = summarize(data)
            basic['keyword'] = find_group(summary, self.groups)
            if basic['keyword'] == "misc":
                print(json.dumps(data, indent=4, sort_keys=True))
                print("Summarized tweet --------------------------------")
                pp = pprint.PrettyPrinter(indent=4)
                pp.pprint(summary)
                sys.exit(1) 
            self.save_to_csv(basic)
            
            # Update stream status to console
            rows, columns = os.popen('stty size', 'r').read().split()

            print('-' * int(columns))
            print(avg_time_per_tweet, "secs/tweet;", self.total_tweets, "total tweets")
            print("Keyword:", basic['keyword'], "Tweet:", basic'text'])

    # Problem with the API
    def on_error(self, status_code, data):
        print(status_code, data)
        self.disconnect()

    # Save each tweet to csv file
    def save_to_csv(self, tweet):
        with open(outfile, 'a') as f:
            if f.tell() == 0:
                header = list(tweet.keys())
                writer = csv.DictWriter(f,fieldnames=header)
                writer.writeheader()
                print(tweet)
                writer.writerow(list(tweet.values())) # Occasionally causes an error for no keys
            else:
                writer = csv.writer(f)
                writer.writerow(list(tweet.values())) # Occasionally causes an error for no keys

if __name__ == "__main__":           
    # Check correct arguments were given
    if len(argv) > 2:
        print("Usage:", os.path.basename(__file__), 
              "[outfile]")
        sys.exit(1)

    # Load Twitter API credentials
    with open("twitter-creds.json", "r") as f:
        creds = json.load(f)


    # Extract tracks from search_query
    tracks = []
    groups = get_search_terms()
    for keywords in groups.values():
        for keyword in keywords:
            tracks.append(keyword)

    print("Streaming tweets about:")   
    for track in range(len(tracks)):
        print(">", tracks[track])

    # try/catch for clean exit after Ctrl-C
    try:
        # Start the stream
        stream = MyStreamer(creds['CONSUMER_KEY'], creds['CONSUMER_SECRET'],
                            creds['ACCESS_KEY'], creds['ACCESS_SECRET'],
                            keywords=groups, outfile=outfile)

        stream.statuses.filter(track=tracks)
        
    except (KeyboardInterrupt, SystemExit):
        print("Saved", stream.total_tweets, "tweets in", datetime.datetime.now() - stream.start_time)
