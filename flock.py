'''
Flock is a tool for fetching historical tweets or for streaming tweets live
Created June 20, 2019 by Casey Key, Oracle SE Intern
Go Rams!
'''
from collections import Counter # For term frequencies
import csv # Exporting tweets
import cx_Oracle # For connecting to ADB
import datetime # Calculate rate of tweets
import json # Loading twitter credentials
import os # For finding console width
import pprint # For printing dicts such as Tweet data
import re # For tokenizing via regex
import requests # For retrieving sentiment from api
import sys # For keyword 'track' arguments
import time # For finding last tweet in previous fetch
from textblob import TextBlob # For sentiment analysis
from twython import Twython, TwythonStreamer # Gateway to Twitter
from urllib3.exceptions import ProtocolError # For handling IncompleteRead error
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer # For sentiment analysis

'''
Load credentials for Twitter or 
Oracle Database (requires .ora file)
'''
def load_creds(json_creds):     
        if type(json_creds) is dict:
            return json_creds
        with open(json_creds, "r") as f:
            return json.load(f)



creds = load_creds('twitter-creds.json')
con = cx_Oracle.connect(creds['user'], creds['pass'], dsn=creds['dsn'])

def get_search_terms(): 
    '''
    Get keywords and labels from the user.
    For example "bitcoin" : {"btc", "bitcoin", "satoshi nakamoto"}
    Where "bitcoin" is the associated label for these search terms.
        - Saves query to query.txt
        - Returns a dictionary
    '''
    groups = []
    terms = {}
    
    try:
        print("What topics do you want to search for?\n")
        print("Press enter to use previous query.")
        print("Enter one topic per prompt.")
        print("Then, press enter when complete.\n")

        while True:
            label = input("Search label: ")
            # User entered empty input
            if not label:
                if groups:
                    raise ValueError("Done with labels")
                else:
                    # Do we have a previous query to load?
                    try:
                        with open('./query.txt', 'r') as f:
                            return json.load(f)
                    except FileNotFound as e:
                        print(e, ": must enter at least one label")
                    continue
            groups.append(label)

    # User finished adding topics
    # Now user adds  search terms associated with each topic
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
   
    # print(terms)

    with open('query.txt', 'w', newline='\n') as f:
        json.dump(terms, f)

    return terms

def create_stream_db(name):
    # View all tables
    cursor = con.cursor()
    tables = cursor.execute("SELECT table_name from user_tables")
    tables = [table[0].lower() for table in tables]
    print("Tables\n" + '-'*10)
    for table in tables:
        print(table)
    if name.lower() not in tables:
        sql = '''create table {}
                (ID NUMBER(25),
                 TWEET_DATE date,
                 HASHTAGS VARCHAR(400),
                 TEXT VARCHAR(400),
                 TWITTER_USER VARCHAR(28),
                 FOLLOWERS NUMBER(10),
                 FOLLOWING NUMBER(10),
                 FAVORITE_COUNT NUMBER(6),
                 RETWEET_COUNT NUMBER(8),
                 USER_LOC VARCHAR(28),
                 KEYWORD VARCHAR(100),
                 NEGATIVE NUMBER(2),
                 NEUTRAL NUMBER(2),
                 POSITIVE NUMBER(2))'''.format(name)
        cursor.execute(sql)
    return


class Flock(object):

    def __init__(self, json_creds, output, cont):
        self._creds =  load_creds(json_creds)
        self._output = output # Output type ('csv' or 'adb')
        self._cont = cont # Continue last query
        if self._output == 'adb':
            self._table = "oracle_sentiment"  # input("What database table would you like to use or create? ")
            create_stream_db(self._table)

        with open('./query.txt', 'r') as query:
            self._groups = get_search_terms() if not cont else json.load(query)

        self._streamer = Streamer(self._creds['CONSUMER_KEY'], self._creds['CONSUMER_SECRET'],
                                  self._creds['ACCESS_KEY'], self._creds['ACCESS_SECRET'],
                                  groups=self._groups, output=self._table)
    
    # Flock().tracks = [term1, term2, ..., termN]
    @property
    def tracks(self):
        # Extract tracks from search_query
        tracks = []
        groups = self._groups
        for keywords in groups.values():
            for keyword in keywords:
                tracks.append(keyword)
        return tracks
    
    # This begins a streaming session
    def start(self, quiet=True):
        print("Streaming tweets about:")   
        for index, track in enumerate(self.tracks):
            print(str(index) + ". " + track)

        stream = self._streamer
        stream.quiet = quiet

        # try/catch for clean exit after Ctrl-C
        try:
            # Start stream, restart on error
            # https://github.com/tweepy/tweepy/issues/908
            while True:
                try:
                    stream.statuses.filter(track=self.tracks)
                except (ProtocolError, AttributeError, Exception) as e:
                    print("Error:", e)
                    time.sleep(3)
                    continue
            
        except (KeyboardInterrupt, SystemExit):
            print("\nSaved", stream.total_tweets, "tweets in", stream.duration)
            cursor = con.cursor()
            print(next(iter(cursor.execute('select count(*) from TWEETS')))[0])
    

    
    def fetch(self, cont=False, csv=False, adb=True):
        api = Twython(self._creds['CONSUMER_KEY'], self._creds['CONSUMER_SECRET'])
        term_lists = [term for term in self._groups.values()]
        terms = []
        for tl in term_lists:
            for term in tl:
                terms.append(term)
        print("Fetching tweets matching: ", terms)
        # input("Press enter to continue.")
        
        last_date = datetime.datetime.now()
        if self._cont:
            if csv:
                # Read last line (Tweet) in output file
                # Credit: Dave @ https://bit.ly/2JGPcUw
                with open(self._output, 'rb') as f:
                    f.seek(-2, os.SEEK_END)
                    while f.read(1) != b'\n':
                        f.seek(-2, os.SEEK_CUR)
                    last_tweet = f.readline().decode()
                tweet_items = last_tweet.split(',')
                last_date = time.strptime(tweet_items[0], '%a %b %d %H:%M:%S +0000 %Y')
            elif adb:
                continue
                cursor = con.cursor()        
                sql = 'select to_char(max(to_date(tweet_date, \'Dy Mon dd hh24:mi:ss "+0000" yyyy\')), \'Dy Mon dd hh24:mi:ss "+0000" yyyy\') from {}'.format(self._table)
                result = cursor.execute(sql)
                last_time = next(iter(result))[0]
                if not last_time: 
                    return
                last_date = time.strptime(last_time, '%a %b %d %H:%M:%S +0000 %Y')
            print("Starting fetch from:", time.strftime('%a %b %d %H:%M:%S +0000 %Y', last_date))

        tweets = []
        MAX_ATTEMPTS = 20
        COUNT_OF_TWEETS_TO_BE_FETCHED = 5000000000000  # int(input("How many tweets would you like?: ")) 

        for i in range(0,MAX_ATTEMPTS):
            if(COUNT_OF_TWEETS_TO_BE_FETCHED < len(tweets)):
                break # we got 500 tweets... !!

            #----------------------------------------------------------------#
            # STEP 1: Query Twitter
            # STEP 2: Save the returned tweets
            # STEP 3: Get the next max_id
            #----------------------------------------------------------------#

            # STEP 1: Query Twitter
            results = []
            if(i == 0):
                # Query twitter for data.
                for term in terms:
                    results.append(api.search(q=term,count='100'))
            else:
                # After the first call we should have max_id from result of previous call. 
                # Pass it in query.
                for term in terms:
                    results.append(api.search(q=term,include_entities='true',max_id=next_max_id))

            # STEP 2: Save the returned tweets
            for result in results:
                for status in result['statuses']:
                    if status.get('lang', None) == 'en':
                        # Extract tweet and append to file
                        basic = Tweet.process_tweet(status)
                        summary = Tweet.summarize(status)
                        # Note Streamer uses self.groups, not _groups. 
                        # TODO: Fix consistency
                        basic['keyword'] = Tweet.find_group(summary, self._groups)
                        if basic['keyword'] != "misc":

                            date = time.strptime(basic['tweet_date'], '%a %b %d %H:%M:%S +0000 %Y')
                            date = datetime.datetime.fromtimestamp(time.mktime(date))
                            if type(last_date) is not str and type(last_date) is not datetime.datetime:
                                time_last = time.mktime(last_date)
                                last_date = datetime.datetime.fromtimestamp(time_last)

                            if cont == False or date > last_date:
                                Tweet.save_to_adb(basic, self._table)
                        
                        else:
                            print("misc keyword in fetch")
            # STEP 3: Get the next max_id
            try:
                # Parse the data returned to get max_id to be passed in consequent call.
                next_results_url_params = result['search_metadata']['next_results']
                next_max_id = next_results_url_params.split('max_id=')[1].split('&')[0]
            except:
                # No more next pages
                 break


'''
Streamer takes api credentials, a "groups" dictionary, and an outfile
Used by the Flock class.
'''
class Streamer(TwythonStreamer):
 
    def __init__(self, *creds, groups, output):
        self._start_time = datetime.datetime.now()
        self.last_tweet_time =  self._start_time
        self.total_tweets = 0
        self.total_difference = 0
        self.groups = groups
        self.output = output
        self._quiet = True
        super().__init__(*creds)  

    @property
    def quiet(self):
        return self._quiet

    @quiet.setter
    def quiet(self, value):
        self._quiet = value

    @property
    def duration(self):
        return datetime.datetime.now() - self._start_time

    # Received data
    def on_success(self, data):
        # Only collect tweets in English
        lang = data.get('lang', None)
        if lang == 'en':
                self.total_tweets += 1
                # Calculate average time per tweet
                tweet_time = datetime.datetime.now()
                tweet_time_difference = tweet_time - self.last_tweet_time
                self.total_difference += tweet_time_difference.total_seconds()
                avg_time_per_tweet = self.total_difference / self.total_tweets
                self.last_tweet_time = tweet_time
                
                # Extract tweet and append to file
                basic = Tweet.process_tweet(data)
                summary = Tweet.summarize(data)
                basic['keyword'] = Tweet.find_group(summary, self.groups)
                if basic['keyword'] != "misc":
                    Tweet.save_to_adb(basic, self.output)
                else:
                    with('errors.txt', 'a') as f:
                        error_time = datetime.datetime.now()
                        pp = pprint.PrettyPrinter(indent=2, stream=f)
                        f.write('-'*20)
                        f.write(str(error_time) + ': Tweet filed under "misc":')
                        f.write('-'*10 + "Data" + '-'*10 + '\n')
                        pp.pprint(data)
                        f.write("-"*10 + "Summary" + "-"*10 + '\n')
                        pp.pprint(summary)
                        f.write('-'*10 + 'Groups' + '-'*10 + '\n')
                        pp.pprint(self.groups)
                        f.write('-'*20)
                        print(str(error_time) + ": Misc logged\n")
                        return
                
                # Update stream status to console
                try:
                    rows, columns = os.popen('stty size', 'r').read().split()
                    print('-' * int(columns))
                # We are running headless
                except:
                    print('-' * 10)
                
                print(avg_time_per_tweet, "secs/tweet;", self.total_tweets, "total tweets")
                print("Keyword:", basic['keyword'], "Tweet:", basic['text'])    
    
    # Problem with the API
    def on_error(self, status_code, data):
        print(status_code, data)
        self.disconnect()


'''
This is required for term frequencies
Not sure where to encapsulating all
the NLP functions to allow for News
and Tweets to share them.

Requires a connection object, "con".
'''
def create_freq_db(name):
    # View all tables
    cursor = con.cursor()
    tables = cursor.execute("SELECT table_name from user_tables")
    tables = [table[0] for table in tables]
    if name not in tables:
        sql = '''create table {}
                (TWEET_DATE DATE,
                 TOKEN VARCHAR(280),
                 COUNT NUMBER(38))'''.format(name)
        cursor.execute(sql)

'''
Methods for processing Tweets
'''
class Tweet:
    # TODO: Make a tweet object have the attributes: summary, basic, and keyword
    # TODO: Add methods for printing out the atributes

    # Save each tweet to csv file
    @staticmethod
    def save_to_csv(outfile, tweet):
        with open(outfile, 'a', newline='\n') as f:
            if f.tell() == 0:
                try: header = list(tweet.keys())
                except Exception as e:
                    print(tweet)
                writer = csv.DictWriter(f,fieldnames=header, quoting=csv.QUOTE_MINIMAL)
                writer.writeheader()
                try: writer.writerow(list(tweet.values())) # Occasionally causes an error for no keys
                except Exception as e:
                    print(tweet)

            else:
                writer = csv.writer(f)
                writer.writerow(list(tweet.values())) # Occasionally causes an error for no keys

    # Format tweet for database
    @staticmethod
    def sanitize(tweet):
        for key, text in tweet.items():
            if type(text) is str:
                tweet[key] = str(text).replace("'","").replace('"','').\
                                       encode('utf-8', errors='ignore').\
                                       decode('utf-8', errors='ignore')
        return tweet

    # Save each tweet to an ADB
    @staticmethod
    def save_to_adb(tweet, table):
        cursor = con.cursor()
        sql = '''INSERT INTO {}
                (ID,TWEET_DATE,HASHTAGS,TEXT,TWITTER_USER,
                 FOLLOWERS,FOLLOWING,
                 FAVORITE_COUNT,RETWEET_COUNT,USER_LOC,KEYWORD,
                 negative,neutral,positive) 
                 VALUES (:id, to_date(:tweet_date, \'Dy Mon dd hh24:mi:ss "+0000" yyyy\'), 
                         :hashtags, :text, :twitter_user,
                         :followers, :following, :favorite_count, 
                         :retweet_count, :user_loc, :keyword, :negative, 
                         :neutral, :positive)'''.format(table)
        print(sql)
        tweet['hashtags'] = str(tweet['hashtags'])
        tweet = Tweet.sanitize(tweet)
        try:
            cursor.execute(sql, tweet)
            print("SQL inserted into ", table, "for Tweet with ID = ", tweet['id'])
            con.commit()
        except Exception as e:
            print("Error with tweet: ", e)
            pp = pprint.PrettyPrinter(indent=2)
            pp.pprint(tweet)

    '''
    Used for sanitizing input for ADW
    Credit: https://bit.ly/2NhKy4f
    '''
    @staticmethod
    def deEmojify(inputString):
        return inputString.encode('ascii', 'ignore').decode('ascii')

    '''
    This loads the most comprehensive text portion of the tweet  
    Where "data" is an individual tweet, treated as JSON / dict
    Inspired by: colditzjb @ https://github.com/tweepy/tweepy/issues/878
    '''
    @staticmethod
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
    This loads the most comprehensive hashtag portion of the tweet  
    Where "data" is an individual tweet, treated as JSON / dict
    Inspired by: colditzjk @ https://github.com/tweepy/tweepy/issues/878
    '''
    @staticmethod
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
                        # Try f or basic text of an original tweet
                        try: text = data['entities']['hashtags']
                        except:
                            # Nothing left to check for
                            text = ''

        hashtags = []
        for entity in text:
            hashtags.append(entity["text"].lower())
        return text

    
    # ------------- Tokenize Text ---------------- 

    emoticons_str = r'''
        (?:
            [:=;] # Eyes
            [o)\-^]? # Nose (optional)
            [D\)\]\(\]\/\\OpPd] # Mouth
        )'''
    
    regex_str = \
        [
            emoticons_str,
            r'<[&>]+>', # HTML tags
            r'@(\w+)', # @mentions
            r'\#(\w+)', # Hashtags
            r'(http|https|ftp):\/\/[a-zA-Z0-9\\.\/]+', # URLs
            r'(?:\d+,?)+(?:\.?\d+)?', # Numbers
            r"(?:[a-z][a-z'\-_]+[a-z])", # Contractions & compound adjectives (-, ')
            r'(?:[\w_]+)', # Other words
            r'(?:\S)' # Anything else
        ]

    tokens_re = re.compile(r'('+'|'.join(regex_str)+')', re.VERBOSE | re.IGNORECASE)
    emoticon_re = re.compile(r'^'+emoticons_str+'$', re.VERBOSE | re.IGNORECASE)
    
    @staticmethod
    def tokenize(text):
        return tokens_re.findall(text)

    # Extract tokens from tweet text portions
    @staticmethod
    def preprocess(text, lowercase=False):
        tokens = tokenize(text)
        if lowercase:
            tokens = [token if emoticon_re.search(token) else token.lower() for token in tokens]
        return tokens
    
    @staticmethod
    def update_freq_db(tweet):
        create_freq_db("tweet_freqs")

    # --------------------------------------------
    
    # Sentiment Alg inspired by Chris "shirosaidev" Park
    # https://github.com/shirosaidev/stocksight
    def get_sentiment_from_url(text):
        sentimentURL = 'http://text-processing.com/api/sentiment/'
        payload = {'text': text}

        try:
            post = requests.post(sentimentURL, data=payload)
        except requests.exceptions.RequestException as re:
            print("Exception: requests exception getting sentiment from url caused by %s" % re)
            raise

        # return None if we are getting throttled or other connection problem
        if post.status_code != 200:
            print("Can't get sentiment from url caused by %s %s" % (post.status_code, post.text))
            return None

        response = post.json()

        # neg = response['probability']['neg']
        # neutral = response['probability']['neutral']
        # pos = response['probability']['pos']
        label = response['label']

        # determine if sentiment is positive, negative, or neutral
        if label == "neg":
            sentiment = "negative"
        elif label == "neutral":
            sentiment = "neutral"
        else:
            sentiment = "positive"

        return sentiment


    def get_sentiment(text):
        """Determine if sentiment is positive, negative, or neutral
        algorithm to figure out if sentiment is positive, negative or neutral
        uses sentiment polarity from TextBlob, VADER Sentiment and
        sentiment from text-processing URL
        could be made better :)
        """

        # pass text into sentiment url
        sentiment_url = Tweet.get_sentiment_from_url(text)

        # pass text into TextBlob
        text_tb = TextBlob(text)

        # pass text into VADER Sentiment
        analyzer = SentimentIntensityAnalyzer()
        text_vs = analyzer.polarity_scores(text)

        if sentiment_url is None:
            if text_tb.sentiment.polarity <= 0 and text_vs['compound'] <= -0.5:
                sentiment = "negative"  # very negative
            elif text_tb.sentiment.polarity <= 0 and text_vs['compound'] <= -0.1:
                sentiment = "negative"  # somewhat negative
            elif text_tb.sentiment.polarity == 0 and text_vs['compound'] > -0.1 and text_vs['compound'] < 0.1:
                sentiment = "neutral"
            elif text_tb.sentiment.polarity >= 0 and text_vs['compound'] >= 0.1:
                sentiment = "positive"  # somewhat positive
            elif text_tb.sentiment.polarity > 0 and text_vs['compound'] >= 0.1:
                sentiment = "positive"  # very positive
            else:
                sentiment = "neutral"
        else:
            if text_tb.sentiment.polarity < 0 and text_vs['compound'] <= -0.1 and sentiment_url == "negative":
                sentiment = "negative"  # very negative
            elif text_tb.sentiment.polarity <= 0 and text_vs['compound'] < 0 and sentiment_url == "neutral":
                sentiment = "negative"  # somewhat negative
            elif text_tb.sentiment.polarity >= 0 and text_vs['compound'] > 0 and sentiment_url == "neutral":
                sentiment = "positive"  # somewhat positive
            elif text_tb.sentiment.polarity > 0 and text_vs['compound'] >= 0.1 and sentiment_url == "positive":
                sentiment = "positive"  # very positive
            else:
                sentiment = "neutral"

        # output sentiment
        print("Sentiment (url): " + str(sentiment_url))
        print("Sentiment (algorithm): " + str(sentiment))

        return sentiment


    # Filter for data to save
    @staticmethod
    def process_tweet(tweet):
        d = {'positive': 0, 'negative': 0, 'neutral':0}
        d['id'] = tweet['id']
        d['tweet_date'] = tweet['created_at']
        d['hashtags'] = [hashtag['text'] for hashtag in Tweet.getHashtags(tweet)]
        text = Tweet.getText(tweet)
        text = Tweet.deEmojify(text) 
        text = text.lower().replace('\n', ' ')
        d['text'] = text
        # strip out hashtags for language processing
        text = re.sub(r'[#|@|\$]\S+', '', text)
        text.strip()
        sentiment = Tweet.get_sentiment(text)
        d[sentiment] = 1
        d['twitter_user'] = Tweet.deEmojify(tweet['user']['screen_name'])
        d['followers'] = tweet['user']['followers_count']
        d['following'] = tweet['user']['friends_count']
        d['favorite_count'] = tweet['favorite_count']
        d['retweet_count'] = tweet['retweet_count']
        location = tweet['user']['location']
        if location:
            location = Tweet.deEmojify(location)
        d['user_loc'] = location 
        return d

    '''
    This extracts all aspects that are searched for in a tweet
    Suggested extra_fields: "id_str", "retweet_count", "favorite_count", "created_at"
    Returns a dictionary
    Credit: https://gwu-libraries.github.io/sfm-ui/posts/2016-11-10-twitter-interaction
    '''
    @staticmethod
    def summarize(tweet, extra_fields = None):
        new_tweet = {}
        for field, value in tweet.items():
            if field in ['text', 'full_text', 'screen_name', \
                         'expanded_url', 'display_url', 'id_str'] and value is not None:
                if field == 'text' or field == 'full_text':
                    text = tweet[field]
                    text = Tweet.deEmojify(text)
                    text = text.lower().replace('\n', ' ')
                    new_tweet[field] = text
                elif field == 'screen_name':
                    new_tweet['twitter_user'] = tweet[field]
                else:
                    new_tweet[field] = value
            
            elif extra_fields and field in extra_fields:
                if field == 'created_at':
                    new_tweet['tweet_date'] = tweet[field]
                else:
                    new_tweet[field] = value

            elif field in ['retweeted_status', 'quoted_status', 'user', 'extended_tweet', 'entities']:
                if value:
                    new_tweet[field] = Tweet.summarize(value)

            elif field == 'hashtags' and len(value):
                for hashtag in value:
                    Tweet.summarize(hashtag)

            elif field == 'urls':
                if type(value) == list and len(value):
                    for link_dict in value:
                        new_tweet[field] = Tweet.summarize(link_dict)
                        
        return new_tweet


    '''
    This method determnes the search term
    used for this tweet.
    Note: We can use this to "tally" the occurences of each term
    By changing to tweet[groups][keyword] = 1
    '''
    @staticmethod
    def find_group(tweet, groups):
        for group, keywords in groups.items():
            found = False
            found = Tweet.find_keyword(tweet, keywords, found)
            if(found):
                return group
        return 'misc'
   
    '''
    Helper method for find_group
    '''
    @staticmethod
    def find_keyword(tweet, keywords, found):
        if type(tweet) == str: 
            for keyword in keywords:
                for word in keyword.split():
                    if tweet.lower().find(word) != -1:
                        found = True
        else:
            for key, value in tweet.items():
                found = Tweet.find_keyword(value, keywords, found)
        return found

if __name__ == '__main__':           
    # Save filters and output file  
    argv = sys.argv
    outfile = 'saved-tweets.csv' if len(argv) == 1 else sys.argv[1]
    samesearch = True if len(argv) == 3 else False
    creds = 'twitter-creds.json'


    # Check correct arguments were given
    if len(argv) > 3:
        print('Usage:', os.path.basename(__file__), 
              '[api-creds.json] [outfile] [continue]')
        sys.exit(1)

 
    stream = Flock(creds, outfile, samesearch)
    stream.fetch(cont=True)
    stream.start()       


