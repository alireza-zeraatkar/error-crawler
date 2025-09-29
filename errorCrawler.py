# import libraries
import requests 
from bs4 import BeautifulSoup as bts
from urllib.parse import urljoin, urlparse
import os
import threading
import time

# make a session for requests
session = requests.session()

# primary link here
primary = 'https://nobitex.ir/'
primary_domain = urlparse(primary).netloc

# define errors
errors = [401, 403, 404, 500, 501, 503]

# make two lists
unseen = set()
seen = set()
crashed = {}

lock = threading.Lock()

# Function To see if link is in same website
def same_domain(link):
    try:
        return urlparse(link).netloc == primary_domain
    except:
        return False

# Function to extract links
def extract(link):
    try:
        req = session.get(link, timeout=10, allow_redirects=True)
        soup = bts(req.content, 'html.parser')
        new_links = []
        for i in soup.find_all('a', href=True):
            href = i['href']
            if href.startswith('http'):
                if same_domain(href) and href not in seen:
                    new_links.append(href)
            else:
                href = urljoin(link, href)
                if same_domain(href) and href not in seen:
                    new_links.append(href)
        with lock:
            unseen.update(new_links)
    except Exception as e:
        with lock:
            crashed[link] = f"Extraction Error: {str(e)}"

# Add primary link to unseen first
with lock:
    unseen.add(primary)

# Function to check links errors
def see(link):
    try:
        req = session.get(link, timeout=10, allow_redirects=True)
        if req.status_code in errors:
            with lock:
                crashed[link] = str(req.status_code)
        with lock:
            seen.add(link)
    except requests.exceptions.RequestException as e: 
        with lock:
            crashed[link] = f"Request Error: {str(e)}"
    except Exception as e:
        with lock:
            crashed[link] = f"Unexpected Error: {str(e)}"

    with open('broken_links.txt', 'w') as fl:
	    for link, error in crashed.items():
		    fl.write(f'{link}: \n     {error}\n\n')
def worker():
    while True:
        link = None
        
        with lock:
            if unseen:
                link = unseen.pop()
        
        if link:
            # Only process if we haven't seen it already and it's in our domain
            with lock:
                if link in seen:
                    continue
            
            extract(link)
            see(link)
        
            with lock:
                os.system('clear')
                print(f"Unseen: {len(unseen)}")
                print(f'Seen: {len(seen)}')
                print(f'Broken: {len(crashed)}')
                print(f'Active Threads: {threading.active_count() - 1}')
                print(f'Current: {link[:80]}...' if len(link) > 80 else f'Current: {link}')
        else:
            time.sleep(0.1)

# Create and start threads
threads = []
for i in range(5):
    thread = threading.Thread(target=worker, daemon=True) 
    thread.start()
    threads.append(thread)

# Keep main thread alive
try:
    while True:
        time.sleep(1)
        with lock:
            # Stop condition: if no more links to process
            if len(unseen) == 0 and len(seen) > 0:
                print("No more links to process")
                break
except KeyboardInterrupt:
    print("\nStopped by user")
