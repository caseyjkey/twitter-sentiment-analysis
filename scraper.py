import requests        		# for downloading webpages
from bs4 import BeautifulSoup   # for webpage (BS) data structure
import re                       # for regular expressions

'''
This method downloads a webpage and returns a BS data structure.
'''
def load_website(url):
    source = requests.get(url).text
    soup = BeautifulSoup(source)
    return soup
'''
Returns a set of links to articles given a webpage
'''
def article_links(soup):
    return soup.get_all('a', {'href': re.compile(r'(http)+.*(wsj\.com\/articles\/)+(.*)')})
'''
textSoup = load_website("https://www.wsj.com/articles/european-stocks-slip-after-gains-in-asia-11560844990")  
links = article_links(textSoup)
'''
url = "https://www.wsj.com/articles/european-stocks-slip-after-gains-in-asia-11560844990"
response = requests.get(url)
print("Response from", url, ":", response.status_code)
soup = BeautifulSoup(response.text) 
links = soup.find_all('a', {'href': re.compile(r'(http)+.*(wsj\.com\/articles\/)+(.*)')})


print(links)
