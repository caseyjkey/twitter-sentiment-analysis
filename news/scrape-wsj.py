import requests        		# for downloading webpages
from bs4 import BeautifulSoup   # for webpage (BS) data structure
import re                       # for regular expressions
import csv                      # for exporting the scraped articles
import sys                      # for command-line url argument
from tqdm import tqdm           # for progress bar

'''
Determines the news source (WSJ, Yahoo! Finance)
Returns:
    "wsj"
    "yahoo"
    "unknown news source"
'''
def which_news_is(url):
    wsj = re.compile(r'.*(wsj\.com)+(.*)')
    yahoo = re.compile(r'.*(finance\.yahoo\.com)+(.*)')
    if wsj.search(url):
        return "wsj"
    if yahoo.search(url):
        return "yahoo"
    return "unknown news source"


argv = sys.argv
url = "https://www.wsj.com/news/markets/stocks" \
       if len(argv) == 1 else argv[1]
source = which_news_is(url)

'''
This method downloads a webpage and returns a BS data structure.
'''
def web_soup(url):
    # Fetch data from url
    response = requests.get(url)
    assert response.status_code == 200

    # Parse website data into bs4 data structure
    soup = BeautifulSoup(response.text,features="html.parser")
    return soup


'''
Extract WSJ links from the bs4 d.s.
'''
def link_soup(soup):
    if source == "wsj":
        return soup.find_all('a', {'href': re.compile(r'(http)+.*(wsj\.com\/articles\/)+(.*)')})
    elif source == "yahoo":
        return soup.find_all('a', {'href': re.compile(r'.*(\/news\/)+(.+)')})
    
    return ()

    
'''
Returns a set of links to articles given a webpage
'''
def get_links(url):	
    html = web_soup(url)
    links = link_soup(html) 
    link_set = set(links)
    link_list = []
    for link in link_set.copy():
        regex = re.compile('(<a class="image")+')
        if regex.search(str(link)):
            print("found image")
            link_set.remove(link)
    return link_set


'''
Saves Wall Street Journal articles as CSV file "wsj-news.csv"
'''
def save_wsj(links):
    print("Scraping now...")

    with open("wsj-news.csv", "a") as f:
        # Write headers if this is a fresh file
        if f.tell() == 0:
            header = ['title', 'article']
            writer = csv.DictWriter(f, fieldnames=header)
            writer.writeheader()
        
        # Write to file
        writer = csv.writer(f)
        for link in tqdm(links, disable=(len(links)<10)):
            # Extract article title
            title = link.text
            # Visit link to article
            article_soup = web_soup(link['href'])
            # Extract article snippet
            article_snippet = article_soup.find_all('div', {'class': 'wsj-snippet-body'})
            for snippet in article_snippet:
                article = snippet.text.replace("\n", " ")    
            # Write article to CSV file
            writer.writerow([title, article])

    print("...scraping complete.")


'''
Saves Yahoo Finance articles as CSV file "yahoo-news.csv"
'''
def save_yahoo(links):
    print("Scraping now...")

    with open("yahoo-news.csv", "a") as f:
        # Write column titles for a fresh CSV file
        if f.tell() == 0:
            header = ['title', 'article']
            writer = csv.DictWriter(f, fieldnames=header)
            writer.writeheader()

        # Write to file
        writer = csv.writer(f)
        for link in tqdm(links, disable=(len(links)<10)):
            break

    print("...scraping complete.")


if __name__ == "__main__":
    links = get_links(url)

    #for link in links:
     #   print(link.prettify())

    print("Found", len(links), "news articles.")
    save_yahoo(links) if source == "yahoo" else save_wsj(links)


