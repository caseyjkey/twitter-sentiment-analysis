import csv # Exporting tweets
import datetime # Calculate rate of tweets
import json # Loading twitter credentials
import os # For finding console width
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
        while True:
            label = input("Enter group label or press enter: ")
            groups.append(label)
    except KeyError:
        for label in groups:
            terms[label] = []  
            try:
                while True:
                    keyword = input("Enter a keyword associated with " + label + " or press enter: ")
                    terms[label].append(keyword)
            except:
                continue
    except:
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
    # Try for extended text of original tweet, if RT'd (streamer)
    try: text = data['retweeted_status']['extended_tweet']['entities']['hashtags']
    except: 
        # Try for extended text of an original tweet, if RT'd (REST API)
        try: text = data['retweeted_status']['entities']['hashtags']
        except:
            # Try for extended text of an original tweet (streamer)
            try: text = data['extended_tweet']['entities']['hashtags']
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
This function takes a "tweet" dictionary and a
Streamer's track "keywords" as a list.
Returns the keyword
TODO: Figure out why some misc tweets
'''
def find_keyword(tweet, keywords):
    kw = set()
    for keyword in keywords:
        for word in keyword.split():
            if tweet['text'].find(word) != -1:
                kw.add(word)
            elif tweet['twitter_user'].find(word) != -1:
                kw.add(word)
            elif word in tweet['hashtags']:
                kw.add(word)
        try:
            print("!!!!!!!!!!!!!!!!!Going into quoted status")
            print(process_tweet(tweet['quoted_status']))
            find_keyword(process_tweet(tweet['quoted_status']), keywords)
            print("-------------------------------------------")
            print(tweet['quoted_status'])

        except:
            continue
    if len(kw) > 1:
        tweet['keyword'] = " ".join(kw)
    elif len(kw):
         tweet['keyword'] = str(kw.pop()) 
    else:
 #       print(json.dumps(tweet, indent=4, sort_keys=True))
 #       sys.exit(1)
        tweet['keyword'] = "misc"
    return tweet['keyword']    


# Create a class that inherits TwythonStreamer
class MyStreamer(TwythonStreamer):
    # start_time = None
    # last_tweet_time = None
    # total_tweets = None
    # total_difference = None
    

    def __init__(self, *creds, keywords, outfile):
        self.start_time = datetime.datetime.now()
        self.last_tweet_time =  self.start_time
        self.total_tweets = 0
        self.total_difference = 0
        self.keywords = keywords
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
            tweet_data = process_tweet(data)
            find_keyword(tweet_data, self.keywords)
            if tweet_data['keyword'] == "misc":
                print(json.dumps(data, indent=4, sort_keys=True))
                sys.exit(1) 
            self.save_to_csv(tweet_data)
            
            # Update stream status to console
            rows, columns = os.popen('stty size', 'r').read().split()

            print('-' * int(columns))
            print(avg_time_per_tweet, "secs/tweet;", self.total_tweets, "total tweets")
            print("Keyword:", tweet_data['keyword'], "Tweet:", tweet_data['text'])

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
                writer.writerow(list(tweet.values())) # Occasionally causes an error for no keys
            else:
                writer = csv.writer(f)
                writer.writerow(list(tweet.values())) # Occasionally causes an error for no keys

if "__name__" == "__main__":           
    # Load Twitter API credentials
    with open("twitter-creds.json", "r") as f:
        creds = json.load(f)
    

    print(get_search_terms())
    if len(argv) > 2:
        print("Usage:", os.path.basename(__file__), 
              "[outfile]")
        sys.exit(1)

    # Determine and print filters

    tracks = argv[2:] # Track filters are not case-sensitive 
    print("Streaming tweets about:")   
    for track in range(len(tracks)):
        print(">", tracks[track])

    # try/catch for clean exit after Ctrl-C
    try:
        # Start the stream
        stream = MyStreamer(creds['CONSUMER_KEY'], creds['CONSUMER_SECRET'],
                            creds['ACCESS_KEY'], creds['ACCESS_SECRET'],
                            keywords=tracks, outfile=outfile)

        stream.statuses.filter(track=tracks)
        
    except (KeyboardInterrupt, SystemExit):
        print("Saved", stream.total_tweets, "tweets in", datetime.datetime.now() - stream.start_time)
