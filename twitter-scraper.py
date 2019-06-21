import json
import pandas as pd
from twython import Twython

# Load Twitter API credentials
with open("twitter-creds.json", "r") as f:
    creds = json.load(f)

print(creds)

# Instantiate a Twython object
python_tweets = Twython(creds['CONSUMER_KEY'], creds['CONSUMER_SECRET'])

# Create our query
query = {'q': 'Oracle',
         'result_type': 'popular',
         'count': '10',
         'lang': 'en',
        }

# Search tweets
t_dict = {'user': [], 'date': [], 'text': [], 'favorite_count': []}
for status in python_tweets.search(**query)['statuses']:
    t_dict['user'].append(status['user']['screen_name'])
    t_dict['date'].append(status['created_at'])
    t_dict['text'].append(status['text'])
    t_dict['favorite_count'].append(status['favorite_count'])

df = pd.DataFrame(t_dict)
df.sort_values(by='favorite_count', inplace=True, ascending=False)
df.head(5)
