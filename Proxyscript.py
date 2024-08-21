import threading
import requests
import time
import colorama
from colorama import Fore, Style
import os
import re
from urllib.parse import urlparse
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

# Initialize colorama
colorama.init(autoreset=True)

# Function to test proxies with enhanced verification
def test_proxy(proxy, protocol, url, string_to_find, timeout_ms):
    try:
        proxies = {protocol.lower(): f"{protocol.lower()}://{proxy}"}
        response = requests.get(url, proxies=proxies, timeout=timeout_ms / 1000)
        if (response.status_code == 200 and 
            'text/html' in response.headers.get('Content-Type', '') and 
            string_to_find in response.text):
            return True
    except requests.exceptions.RequestException:
        pass
    return False

# Function to extract proxies from URL content
def extract_proxies_from_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        proxies = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}:\d{2,5}\b', response.text)
        return proxies
    except requests.exceptions.RequestException as e:
        print(f"{Fore.RED}Failed to fetch proxies from URL: {e}")
        return []

# Function to process multiple URLs
def extract_proxies_from_multiple_urls(file_path):
    all_proxies = set()
    with open(file_path, 'r') as file:
        urls = [line.strip() for line in file if line.strip()]
        for url in tqdm(urls, desc="Scraping URLs for proxies", unit="url"):
            proxies = extract_proxies_from_url(url)
            all_proxies.update(proxies)
    return list(all_proxies)

# Function to remove already checked proxies
def remove_checked_proxies(proxies, valid_file, failed_file):
    checked_proxies = set()
    for file in [valid_file, failed_file]:
        if os.path.exists(file):
            with open(file, 'r') as f:
                checked_proxies.update(line.strip() for line in f)
    return [proxy for proxy in proxies if proxy not in checked_proxies]

# Function to process each proxy
def process_proxy(proxy, protocol, url, string_to_find, timeout, valid_proxies, bandwidth_used):
    if test_proxy(proxy, protocol, url, string_to_find, timeout):
        with open('Socks4.txt', 'a') as valid_file:
            valid_file.write(f"{proxy}\n")
        valid_proxies.append(proxy)
    else:
        with open('failed-proxylist.txt', 'a') as failed_file:
            failed_file.write(f"{proxy}\n")
    bandwidth_used += len(proxy) * len(url)  # Simplified bandwidth calculation

# Main function
def main():
    url = "https://ziptasticapi.com/82945"
    string_to_find = "SUPERIOR"
    protocol = "socks4"
    threads = 2
    timeout = 1500

    # Load and clean proxies
    proxies = extract_proxies_from_multiple_urls('linkslist.txt')
    proxies = list(set(proxies))  # Remove duplicates
    proxies = remove_checked_proxies(proxies, 'Socks4.txt', 'failed-proxylist.txt')

    if not proxies:
        print(f"{Fore.RED}No valid proxies found.")
        time.sleep(3 * 3600)
        return

    valid_proxies = []
    bandwidth_used = 0

    # Start threads using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = [executor.submit(process_proxy, proxy, protocol, url, string_to_find, timeout, valid_proxies, bandwidth_used) for proxy in proxies]
        
        progress = tqdm(as_completed(futures), total=len(proxies), desc="Checking proxies", unit="proxy")
        for future in progress:
            future.result()

    # Display results
    print(f"{Fore.CYAN}\nTotal valid proxies: {len(valid_proxies)}")
    print(f"{Fore.CYAN}Bandwidth used: {bandwidth_used / (1024 * 1024):.2f} MB")

    # Sleep for 20 minutes before restarting
    print(f"{Fore.YELLOW}Sleeping for 20 min before restarting...")
    time.sleep(1200)
    main()

if __name__ == "__main__":
    main()
