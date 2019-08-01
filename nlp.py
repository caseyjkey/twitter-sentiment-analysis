import re
import requests
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer 
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

def tokenize(text):
    return tokens_re.findall(text)

# Extract tokens from tweet text portions
def preprocess(text, lowercase=False):
    tokens = tokenize(text)
    if lowercase:
        tokens = [token if emoticon_re.search(token) else token.lower() for token in tokens]
    return tokens


def update_freq_db(tweet):
    create_freq_db("tweet_freqs")

# --------------------------------------------

# Sentiment Alg credit to Chris "shirosaidev" Park
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
    sentiment_url = get_sentiment_from_url(text)

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
