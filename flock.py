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
import re # For removing useless parts of Tweet text
import requests # For retrieving sentiment from api
import sys # For keyword 'track' arguments
import time # For finding last tweet in previous fetch
from twython import Twython, TwythonStreamer # Gateway to Twitter
from urllib3.exceptions import ProtocolError # For handling IncompleteRead error
import nlp # Custom module containing text analysis tools 


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
            with open('db.txt', 'r+') as db:
                if sys.stdout.isatty():
                    self._table = input("What database table would you like to use or create? ")
                    db.write(self._table)
                else:
                    self._table = db.read().strip()
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
        print("\nFetching tweets matching: ", terms)
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
                # Convert to a datetime object
                last_date = time.strptime(tweet_items[0], '%a %b %d %H:%M:%S +0000 %Y')
            elif adb:
                cursor = con.cursor()        
                sql = 'select tweet_date from {}'.format(self._table)
                result = cursor.execute(sql)
                try:
                    last_date = next(iter(result))[0]
                except Exception:
                    print('No last tweet, starting table from scratch.')
                    return
                
            print("Starting fetch from:", last_date)

        tweets = []
        MAX_ATTEMPTS = 20
        COUNT_OF_TWEETS_TO_BE_FETCHED = 5000000000000  
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
                        tweet = Tweet(status)
                        # Note Streamer uses self.groups, not _groups. 
                        # TODO: Fix consistency
                        tweet.find_topic(self._groups)
                        if tweet.keyword:
                            date = time.strptime(tweet.tweet_date, '%a %b %d %H:%M:%S +0000 %Y')
                            date = datetime.datetime.fromtimestamp(time.mktime(date))
                            if type(last_date) is not str and type(last_date) is not datetime.datetime:
                                time_last = time.mktime(last_date)
                                last_date = datetime.datetime.fromtimestamp(time_last)
                            print(date, '>', last_date, '=', date > last_date)
                            if cont == False or date > last_date:
                                tweet.save_to_adb(self._table)
                        
                        else:
                            with open('errors.txt', 'a') as f:
                                error_time = datetime.datetime.now()
                                pp = pprint.PrettyPrinter(indent=2, stream=f)
                                f.write('-'*7 + 'Fetch' + '-'*7)
                                f.write(str(error_time) + ': Tweet filed under "misc":')
                                f.write('-'*10 + "Data" + '-'*10 + '\n')
                                pp.pprint(tweet.raw)
                                f.write("-"*10 + "Summary" + "-"*10 + '\n')
                                pp.pprint(tweet.summarize(tweet.raw))
                                f.write('-'*10 + 'Groups' + '-'*10 + '\n')
                                pp.pprint(self._groups)
                                f.write('-'*20)
                                print(str(error_time) + ": Misc logged\n") 

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
                tweet = Tweet(data)
                tweet.find_topic(self.groups)
                if tweet.keyword:
                    tweet.save_to_adb(self.output)
                else:
                    with open('errors.txt', 'a') as f:
                        error_time = datetime.datetime.now()
                        pp = pprint.PrettyPrinter(indent=2, stream=f)
                        f.write('-'*20)
                        f.write(str(error_time) + ': Tweet filed under "misc":')
                        f.write('-'*10 + "Data" + '-'*10 + '\n')
                        pp.pprint(tweet.raw)
                        f.write("-"*10 + "Summary" + "-"*10 + '\n')
                        pp.pprint(tweet.summarize(tweet.raw))
                        f.write('-'*10 + 'Groups' + '-'*10 + '\n')
                        pp.pprint(self.groups)
                        f.write('-'*20)
                        print(str(error_time) + ": Misc logged\n")
                        return
                
                # Update stream status to console
                if sys.stdout.isatty():
                    rows, columns = os.popen('stty size', 'r').read().split()
                    print('-' * int(columns))
                # We are running headless
                else:
                    print('-' * 10)
                
                print(avg_time_per_tweet, "secs/tweet;", self.total_tweets, "total tweets")
                print("Keyword:", tweet.keyword, "Tweet:", tweet.text)    
    
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
    
    def __init__(self, tweet):
        self.positive = 0
        self.neutral = 0
        self.negative = 0
        self.raw = tweet
        self.process_tweet(tweet)
        self.sanitize()
        

    # Filter for data to save
    def process_tweet(self, tweet):
        self.id = tweet['id']
        self.tweet_date = tweet['created_at']
        self.getHashtags(tweet)
        self.getText(tweet)
        sent_result = nlp.get_sentiment(self.text)
        setattr(self, sent_result, 1)
        self.twitter_user = self.deEmojify(tweet['user']['screen_name'])
        self.followers = tweet['user']['followers_count']
        self.following = tweet['user']['friends_count']
        self.favorites = tweet['favorite_count']
        self.retweets = tweet['retweet_count']
        location = tweet['user']['location']
        self.user_loc = self.deEmojify(location) if location else "Earth"


    # Save each tweet to csv file
    def save_to_csv(self, outfile):
        with open(outfile, 'a', newline='\n') as f:
            if f.tell() == 0:
                try: header = list(tweet.keys())
                except Exception as e:
                    print(tweet, "Error in save_to_csv")
                writer = csv.DictWriter(f,fieldnames=header, quoting=csv.QUOTE_MINIMAL)
                writer.writeheader()
                try: writer.writerow(list(tweet.values())) # Occasionally causes an error for no keys
                except Exception as e:
                    print(tweet, "Error in save_to_csv")

            else:
                writer = csv.writer(f)
                writer.writerow(list(tweet.values())) # Occasionally causes an error for no keys

    # Format tweet for database
    def sanitize(self):
        for attr in list(vars(self).keys()):
            val = getattr(self, attr)
            if val is str:
                setattr(self, attr, val.replace("'","").replace('"','').\
                                        encode('utf-8', errors='ignore').\
                                        decode('utf-8', errors='ignore'))


    # Save each tweet to an ADB
    def save_to_adb(self, table):
        cursor = con.cursor()
        sql = '''INSERT INTO {}
                (ID,TWEET_DATE,HASHTAGS,TEXT,TWITTER_USER,
                 FOLLOWERS,FOLLOWING,
                 FAVORITE_COUNT,RETWEET_COUNT,USER_LOC,KEYWORD,
                 negative,neutral,positive) 
                 VALUES (:id, to_date(:tweet_date, \'Dy Mon dd hh24:mi:ss "+0000" yyyy\'), 
                         :hashtags, :text, :twitter_user,
                         :followers, :following, :favorites, 
                         :retweets, :user_loc, :keyword, :negative, 
                         :neutral, :positive)'''.format(table)
        print(sql)
        try:
            tweet = {i:vars(self)[i] for i in vars(self) if i!='raw'}
            cursor.execute(sql, tweet)
            print("SQL inserted into ", table, "for Tweet with ID = ", self.id)
            con.commit()
        except Exception as e:
            print("save_to_adb() error: ", e)
            pp = pprint.PrettyPrinter(indent=2)
            pp.pprint(vars(self))

    '''
    Used for sanitizing input for ADW
    Credit: https://bit.ly/2NhKy4f
    '''
    # TODO: check to see if can deprecate
    def deEmojify(self, inputString):
        return inputString.encode('ascii', 'ignore').decode('ascii')

    '''
    This loads the most comprehensive text portion of the tweet  
    Where "data" is an individual tweet, treated as JSON / dict
    Inspired by: colditzjb @ https://github.com/tweepy/tweepy/issues/878
    '''
    def getText(self, data):       
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
        
        text = self.deEmojify(text).lower().replace('\n', ' ')
        
        # strip out hashtags for language processing
        text = re.sub(r'[#|@|\$]\S+', '', text)
        text.strip()
        
        self.text = text
        return text

    '''
    This loads the most comprehensive hashtag portion of the tweet  
    Where "data" is an individual tweet, treated as JSON / dict
    Inspired by: colditzjk @ https://github.com/tweepy/tweepy/issues/878
    '''
    def getHashtags(self, data):            
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
        self.hashtags = str(hashtags)
    
    
    '''
    This extracts all aspects that are searched for in a tweet
    Suggested extra_fields: "id_str", "retweet_count", "favorite_count", "created_at"
    Returns a dictionary
    Credit: https://gwu-libraries.github.io/sfm-ui/posts/2016-11-10-twitter-interaction
    '''
    def summarize(self, tweet, extra_fields = None):
        new_tweet = {}
        for field, value in tweet.items():
            if field in ['text', 'full_text', 'screen_name', \
                         'expanded_url', 'display_url', 'id_str'] and value is not None:
                if field == 'text' or field == 'full_text':
                    text = tweet[field]
                    text = self.deEmojify(text)
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
                    new_tweet[field] = self.summarize(value)

            elif field == 'hashtags' and len(value):
                for hashtag in value:
                    self.summarize(hashtag)

            elif field == 'urls':
                if type(value) is list and len(value):
                    for link_dict in value:
                        new_tweet[field] = self.summarize(link_dict)
                        
        return new_tweet


    '''
    Given a summarized Tweet (searchable text)
    This method determines the search term
    used to find this tweet.
    Note: We can use this to "tally" the occurences of each term
    By changing to tweet[topic][keyword] = 1
    '''
    def find_topic(self, topics):
        tweet = self.summarize(self.raw)
        found = list() 
        for topic, keywords in topics.items():
            found = self.find_keyword(tweet, keywords, found)
        best_keyword = max(found, key=len) if found else None
        if best_keyword:
            for key, value in topics.items():
                if best_keyword in value:
                    self.keyword = key
        else:
            self.keyword = None
   
    '''
    Helper method for find_topic
    Need to fix this to find the longest keyword
    '''
    def find_keyword(self, val, keywords, found):
        if type(val) is str: 
            for keyword in keywords:
                if self.find_string(keyword, val):
                    # All parts of keyword found
                    found.append(keyword)
        else:
            for key, value in val.items():
                self.find_keyword(value, keywords, found)
        return found

    def find_string(self, string, text):
        for word in string.split():
            if word not in text:
                return False
        return True

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
    #stream.fetch(cont=True)
    stream.start()       


