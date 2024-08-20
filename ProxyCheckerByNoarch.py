import threading
import requests
import time
import colorama
from colorama import Fore, Style
import os
import configparser
import signal
import re
from urllib.parse import urlparse
from tqdm import tqdm  # Progress bar

# Initialize colorama
colorama.init(autoreset=True)

# Template for the config file
CONFIG_TEMPLATE = """
[settings]
url = https://example.com
string_to_find = ExampleString
"""

# Function to handle exit gracefully
def graceful_exit(signum, frame):
    print(f"{Fore.YELLOW}\nRestarting the script or type 'exit' to exit.")
    if input().strip().lower() == 'exit':
        exit(0)
    else:
        main()

# Function to load the config file
def load_config():
    config = configparser.ConfigParser()
    if not os.path.exists('config.ini'):
        with open('config.ini', 'w') as config_file:
            config_file.write(CONFIG_TEMPLATE)
        print(f"{Fore.YELLOW}Config file created. Please edit 'config.ini' and run the script again.")
        exit(0)

    config.read('config.ini')
    return config['settings']['url'], config['settings']['string_to_find']

# Function to test proxies
def test_proxy(proxy, protocol, url, string_to_find, timeout_ms):
    try:
        proxies = {protocol.lower(): f"{protocol.lower()}://{proxy}"}
        response = requests.get(url, proxies=proxies, timeout=timeout_ms/1000)
        if string_to_find in response.text:
            return True
    except requests.exceptions.RequestException:
        pass
    return False

# Function to check if input is a URL
def is_url(input_string):
    try:
        result = urlparse(input_string)
        return all([result.scheme, result.netloc])
    except ValueError:
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

# Main function
def main():
    # Handle graceful exit
    signal.signal(signal.SIGINT, graceful_exit)

    # Load config
    url, string_to_find = load_config()

    # User inputs
    threads = input(f"{Fore.CYAN}Enter the number of threads (1-250) [default: 20]: ").strip()
    threads = int(threads) if threads.isdigit() and 1 <= int(threads) <= 250 else 20
    
    timeout = input(f"{Fore.CYAN}Enter timeout in ms [default: 500ms]: ").strip()
    timeout = int(timeout) if timeout.isdigit() and int(timeout) > 0 else 500

    proxylist_input = input(f"{Fore.CYAN}Enter path to proxylist or URL: ").strip()

    # Protocol selection
    protocols = [
        "connect", "http", "https", "socks4", "socks5", 
        "socks4 & socks5", "HTTP, HTTPS & SOCKS4 & Socks5"
    ]
    print(f"{Fore.CYAN}Select protocol to test for:")
    for i, protocol in enumerate(protocols, 1):
        print(f"{Fore.GREEN}{i}. {protocol}")
    
    protocol_choice = input(f"{Fore.CYAN}Enter choice [default: 3]: ").strip()
    protocol_choice = int(protocol_choice) if protocol_choice.isdigit() and 1 <= int(protocol_choice) <= len(protocols) else 3
    protocol = protocols[protocol_choice - 1].split(' ')[0]

    # Load proxies from file or URL
    if is_url(proxylist_input):
        proxies = extract_proxies_from_url(proxylist_input)
    elif proxylist_input.lower() == 'linkslist.txt':
        proxies = extract_proxies_from_multiple_urls(proxylist_input)
    else:
        if not os.path.exists(proxylist_input):
            print(f"{Fore.RED}Proxylist file does not exist!")
            exit(0)
        with open(proxylist_input, 'r') as file:
            proxies = [line.strip() for line in file if line.strip()]

    proxies = list(set(proxies))  # Remove duplicates
    proxies = [proxy for proxy in proxies if ':80' not in proxy]  # Filter out port 80

    if not proxies:
        print(f"{Fore.RED}No valid proxies found.")
        exit(0)

    valid_proxies = []
    bandwidth_used = 0
    online_proxies_count = 0

    # Function to process each proxy
    def process_proxy(proxy):
        nonlocal bandwidth_used, online_proxies_count
        # Skip proxies with port 80
        if ':80' in proxy:
            return
        if test_proxy(proxy, protocol, url, string_to_find, timeout):
            valid_proxies.append(proxy)
            online_proxies_count += 1
        bandwidth_used += len(proxy) * len(url)

    # Start threads
    threads_list = []
    progress = tqdm(total=len(proxies), desc="Checking proxies", unit="proxy")
    for proxy in proxies:
        thread = threading.Thread(target=process_proxy, args=(proxy,))
        threads_list.append(thread)
        thread.start()

        while len(threading.enumerate()) > threads:
            time.sleep(0.1)
        
        # Update progress bar description
        progress.set_description(f"Checking proxies - Online: {online_proxies_count}")
        progress.update(1)

    # Wait for all threads to finish
    for thread in threads_list:
        thread.join()

    progress.close()

    # Save valid proxies to file
    if valid_proxies:
        with open('proxylist-validated-online.txt', 'w') as file:
            for proxy in valid_proxies:
                file.write(f"{proxy}\n")
        print(f"{Fore.GREEN}Valid proxies saved to 'proxylist-validated-online.txt'")
    else:
        print(f"{Fore.RED}No valid proxies found. Nothing was saved.")

    print(f"{Fore.CYAN}\nTotal valid proxies: {len(valid_proxies)}")
    print(f"{Fore.CYAN}Bandwidth used: {bandwidth_used} bytes")
    print(f"{Fore.YELLOW}Script finished. Restarting the script or type 'exit' to exit.")
    if input().strip().lower() == 'exit':
        exit(0)
    else:
        main()

if __name__ == "__main__":
    main()
