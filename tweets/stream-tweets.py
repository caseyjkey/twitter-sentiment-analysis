import csv # Exporting tweets
import datetime # Calculate rate of tweets
import json # Loading twitter credentials
import os # For finding console width
import sys # For keyword 'track' arguments
# import threading # For saving tweets by track keyword


from twython import TwythonStreamer # Gateway to Twitter

# Track filters can be passed as arguments
argv = sys.argv


# Load Twitter API credentials
with open("twitter-creds.json", "r") as f:
    creds = json.load(f)

# Used for sanitizing input for ADW
def deEmojify(inputString):
    return inputString.encode('ascii', 'ignore').decode('ascii')

# Filter out unwanted data
def process_tweet(tweet):
    d = {}
    d['date'] = tweet['created_at']
    d['hashtags'] = [hashtag['text'] for hashtag in tweet['entities']['hashtags']]
    d['text'] = deEmojify(tweet['text']).replace("\n", " ")
    d['user'] = tweet['user']['screen_name']
    # d['user_loc'] = tweet['user']['location']
    return d

'''
This function takes a "tweet" dictionary and a
Streamer's track "keywords" as a list.
Returns the keyword
'''
def find_keyword(tweet, keywords):
    kw = ""
    for keyword in keywords:
        print("keyword",keyword)
        for word in keyword.split():
            print("word",word)
            if word in tweet['text']:
                kw += " " + word if kw else word
            elif word in tweet['user']:
                kw += " " + word if kw else word
            elif word in tweet['hashtags']:
                kw += " " + word if kw else word
    tweet['keyword'] = kw 
    return kw    


# Create a class that inherits TwythonStreamer
class MyStreamer(TwythonStreamer):
    # start_time = None
    # last_tweet_time = None
    # total_tweets = None
    # total_difference = None
    

    def __init__(self, *creds, keywords):
        self.start_time = datetime.datetime.now()
        self.last_tweet_time =  self.start_time
        self.total_tweets = 0
        self.total_difference = 0
        self.keywords = keywords
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
        with open(r'saved_tweets.csv', 'a') as f:
            if f.tell() == 0:
                header = list(tweet.keys())
                writer = csv.DictWriter(f,fieldnames=header)
                writer.writeheader()
                writer.writerow(list(tweet.values()))
            else:
                writer = csv.writer(f)
                writer.writerow(list(tweet.values()))
           
# Determine and print filters
tracks = 'oracle' # Track filters are not case-sensitive 
print("Streaming tweets about:", tracks)
if len(argv) != 1:
    seperator = ', '
    tracks = seperator.join(argv[1:])
    for track in tracks:
        print(">", track)
else:
    print(">", tracks)


try:
    # Start the stream
    stream = MyStreamer(creds['CONSUMER_KEY'], creds['CONSUMER_SECRET'],
                        creds['ACCESS_KEY'], creds['ACCESS_SECRET'], keywords=tracks)
    stream.statuses.filter(track=tracks)
    
except (KeyboardInterrupt, SystemExit):
    print("Saved", stream.total_tweets, "tweets in", stream.start_time - datetime.datetime.now())
    stream_track.join()
