import requests        		# for downloading webpages
from bs4 import BeautifulSoup   # for webpage (BS) data structure
import re                       # for regular expressions

'''
This method downloads a webpage and returns a BS data structure.
'''
def website_soup(url):
    response = requests.get(url)
    print("Response from", url, ":", response.status_code)
    soup = BeautifulSoup(response.text,features="html.parser")
    return soup

def link_soup(soup):
    return soup.find_all('a', {'href': re.compile(r'(http)+.*(wsj\.com\/articles\/)+(.*)')})

'''
Returns a set of links to articles given a webpage
'''
def get_links(url):
	
    html = website_soup(url)
    links = link_soup(html) 
    link_set = set(links)
    print("We begin with", len(link_set), "links")
    for link in links:
        regex = re.compile('(<a class="image")+')
        if regex.search(str(link)):
            print("found image")
            link_set.remove(link)
    print("After, we have", len(link_set), "links")
    return link_set


url = "https://www.wsj.com/articles/european-stocks-slip-after-gains-in-asia-11560844990"  
links = get_links(url)
         
