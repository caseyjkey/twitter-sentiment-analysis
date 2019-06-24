import csv
import json
from twython import TwythonStreamer

# Load Twitter API credentials
with open("twitter-creds.json", "r") as f:
    creds = json.load(f)

def deEmojify(inputString):
    return inputString.encode('ascii', 'ignore').decode('ascii')

# Filter out unwanted data
def process_tweet(tweet):
    d = {}
    d['hashtags'] = [hashtag['text'] for hashtag in tweet['entities']['hashtags']]
    d['text'] = deEmojify(tweet['text']).replace("\n", " ")
    d['user'] = tweet['user']['screen_name']
    # d['user_loc'] = tweet['user']['location']
    return d

# Create a class that inherits TwythonStreamer
class MyStreamer(TwythonStreamer):

    # Received data
    def on_success(self, data):

        # Only collect tweets in English
        if data['lang'] == 'en':
            tweet_data = process_tweet(data)
            self.save_to_csv(tweet_data)

    # Problem with the API
    def on_error(self, status_code, data):
        print(status_code, data)
        self.disconnect()

    # Save each tweet to csv file
    def save_to_csv(self, tweet):
        print(tweet.keys())
        with open(r'saved_tweets.csv', 'a') as f:
            if f.tell() == 0:
                header = list(tweet.keys())
                writer = csv.DictWriter(f,fieldnames=header)
                writer.writeheader()
                writer.writerow(list(tweet.values()))
            else:
                writer = csv.writer(f)
                writer.writerow(list(tweet.values()))
           
# Instantiate a MyStreamer object
stream = MyStreamer(creds['CONSUMER_KEY'], creds['CONSUMER_SECRET'],
                    creds['ACCESS_KEY'], creds['ACCESS_SECRET'])

# Start the stream
stream.statuses.filter(track='Oracle')
