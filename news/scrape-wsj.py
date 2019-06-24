import requests        		# for downloading webpages
from bs4 import BeautifulSoup   # for webpage (BS) data structure
import re                       # for regular expressions
import csv                      # for exporting the scraped articles
import sys                      # for command-line url argument
from tqdm import tqdm           # for progress bar

argv = sys.argv
url = "https://www.wsj.com/news/markets/stocks" \
       if len(argv) == 1 else argv[1]

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
    return soup.find_all('a', {'href': re.compile(r'(http)+.*(wsj\.com\/articles\/)+(.*)')})

'''
Returns a set of links to articles given a webpage
'''
def get_links(url):	
    html = web_soup(url)
    links = link_soup(html) 
    link_set = set(links)
    print("We begin with", len(link_set), "links")
    link_list = []
    for link in link_set.copy():
        regex = re.compile('(<a class="image")+')
        if regex.search(str(link)):
            print("found image")
            link_set.remove(link)
    print("After, we have", len(link_set), "links")
    return link_set


links = get_links(url)

def links-tqdm(links):
    
    

with open("news-articles.csv", "a") as f:
    if f.tell() == 0:
        header = ['title', 'article']
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
    
    writer = csv.writer(f)
    for link, num in zip(links, tqdm(range(len(links)))):
        #writer.writerow(link.text, 
        title = link.text
        article_soup = web_soup(link['href'])
        article_snippet = article_soup.find_all('div', {'class': 'wsj-snippet-body'})
        for snippet in article_snippet:
            article = snippet.text.replace("\n", " ")    
        writer.writerow([title, article])
