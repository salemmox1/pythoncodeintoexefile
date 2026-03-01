import os
import random
import subprocess
import threading
import time
import requests
import ipaddress
import re
import argparse
import sys
from colorama import Fore, init, Style, Back

init(autoreset=True)

G = Fore.GREEN
R = Fore.RED
Y = Fore.YELLOW
CY = Fore.CYAN
W = Fore.WHITE
B = Fore.BLUE
MAG = Fore.MAGENTA
LC = Fore.LIGHTCYAN_EX
LB = Fore.LIGHTBLUE_EX
LR = Fore.LIGHTRED_EX
LG = Fore.LIGHTGREEN_EX
LY = Fore.LIGHTYELLOW_EX
LM = Fore.LIGHTMAGENTA_EX
LW = Fore.LIGHTWHITE_EX
LBK = Fore.LIGHTBLACK_EX
BK = Fore.BLACK
RE = Style.RESET_ALL

COMPANIES = {
    "1": {"name": "Amazon AWS (3.x)", "prefix": "3"},
    "2": {"name": "Amazon AWS (52.x)", "prefix": "52"},
    "3": {"name": "Microsoft Azure", "prefix": "13"},
    "4": {"name": "Google Cloud", "prefix": "34"},
    "5": {"name": "Akamai / Cloud (122.x)", "prefix": "122"},
    "6": {"name": "Global Networks (2.x)", "prefix": "2"},
    "7": {"name": "DigitalOcean", "prefix": "104"},
    "8": {"name": "Oracle Cloud", "prefix": "140"}
}

COMMON_COUNTRIES = {
    "ARAB": {"sa": "SAUDI ARABIA", "eg": "Egypt", "ae": "UAE", "kw": "Kuwait", "ma": "Morocco", "dz": "Algeria", "iq": "Iraq", "jo": "Jordan"},
    "EUROPE": {"de": "GERMANY", "fr": "FRANCE", "nl": "Netherlands", "it": "Italy", "es": "Spain", "tr": "Turkey", "gb": "UK"},
    "AMERICA": {"us": "USA", "ca": "Canada", "br": "Brazil", "mx": "Mexico", "ar": "Argentina"},
    "ASIA/EURASIA": {"ru": "RUSSIA", "cn": "China", "in": "India", "jp": "Japan", "kr": "South Korea", "sg": "Singapore", "my": "Malaysia"}
}

def n(r, g, b):
    return f"\033[38;2;{r};{g};{b}m"
    OR = n(255, 128, 0)
    
def goodbye():
    print(f"\n\n{MAG}[{W}!{MAG}] {G}GOODBYE PEER... {W} Drive safely ;){RE}")
    time.sleep(1)
    sys.exit(0)

def show_how_to_use():
    print(f"\n{LC}================ HOW TO USE THE TOOL ================")
    print(f"{W}1. Manual Mode: {G}Just run 'nl-master' and follow menus.")
    print(f"{W}2. CLI Mode Examples:")
    print(f"   {Y}- Quick Country Scan: {CY}nl-master -c eg -b 24 -p")
    print(f"   {Y}- Save as CIDR (Fast): {CY}nl-master -c eg -b all -ty cidr")
    print(f"   {Y}- Pattern Logic:     {CY}nl-master --pattern 156.x.x.x -p")
    print(f"   {Y}- Global (Auto):     {CY}nl-master --global_scan 52 -l 5000 -p")
    print(f"{W}3. Flags Meaning:")
    print(f"   {B}-c / --country : {W}ISO Code (eg, us, sa)")
    print(f"   {B}-b / --block   : {W}CIDR Mask (8, 24, 16) or 'all'")
    print(f"   {B}-ty / --type   : {W}Save mode ('cidr' for blocks, 'ip' for individuals)")
    print(f"   {B}-l / --limit   : {W}IPs per block / Total for Global")
    print(f"   {B}-p / --ping    : {W}Enable alive check")
    print(f"   {B}-t / --threads : {W}Speed of check (default 150)")
    print(f"{LC}===================================================={RE}\n")

def show_countries_menu():
    print(f"\n{MAG}================ {W}POPULAR COUNTRY CODES {MAG}================")
    for region, countries in COMMON_COUNTRIES.items():
        print(f"\n{Y}[-] {region}:")
        count = 0
        for code, name in countries.items():
            color = G if name in ["SAUDI ARABIA", "GERMANY", "FRANCE", "USA", "RUSSIA"] else LC
            print(f"    {B}[{code}] {color}{name.ljust(15)}", end="")
            count += 1
            if count % 3 == 0: print()
        print()
    print(f"\n{CY}TIP: You can use ANY ISO country code (e.g., 'ca' for Canada, 'fr' for France)")
    print(f"{CY}LINK: https://www.iso.org/obp/ui/#search")
    print(f"\n{MAG}===================================================={RE}")

def fetch_country_ips(country_ids, specific_blocks=None):
    all_cidrs = []
    ids = [i.strip().lower() for i in country_ids.split(',')]
    target_blocks = None
    if specific_blocks and str(specific_blocks).lower() != 'all':
        target_blocks = [f"/{b.strip()}" for b in str(specific_blocks).split(',')]
    for country_id in ids:
        url = f"https://raw.githubusercontent.com/ipverse/country-ip-blocks/master/country/{country_id}/ipv4-aggregated.txt"
        print(f"{LC}[*] Connecting to ipverse for {country_id.upper()}...{RE}")
        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                cidrs = [line.strip() for line in response.text.splitlines() if line.strip() and not line.startswith("#")]
                if target_blocks:
                    cidrs = [c for c in cidrs if any(c.endswith(b) for b in target_blocks)]
                all_cidrs.extend(cidrs)
            else:
                print(f"{R}[!] Error: Data not found for '{country_id}'.{RE}")
        except:
            print(f"{R}[!] Connection Failed for {country_id}!{RE}")
    return all_cidrs

def extract_sample_ips(cidr_list, limit_input):
    ips = []
    is_all = str(limit_input).lower() == "all"
    print(f"{Y}[*] Extracting IPs from blocks (May take time for large ranges)...{RE}")
    for block in cidr_list:
        try:
            network = ipaddress.ip_network(block)
            count = 0
            for ip in network.hosts():
                ips.append(str(ip))
                if not is_all:
                    count += 1
                    if count >= int(limit_input): break
        except: continue
    return ips

def ping_check(ip):
    try:
        res = subprocess.call(['ping', '-c', '1', '-W', '1', ip] if os.name != 'nt' else ['ping', '-n', '1', '-w', '1000', ip], 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return res == 0
    except: return False

def filter_alive_ips(ip_list, threads_count=150):
    alive_count = 0
    total = len(ip_list)
    processed = 0
    start_time = time.time()
    open("IP.txt", "w").close()
    print(f"\n{LC}>>> {W}STARTING FILTER ON {Y}{total} {W}IPs {LC}<<<{RE}")
    lock = threading.Lock()
    def worker(ips):
        nonlocal processed, alive_count
        for ip in ips:
            status = ping_check(ip)
            with lock:
                processed += 1
                if status:
                    alive_count += 1
                    with open("IP.txt", "a") as f: f.write(ip + "\n")
                if processed % 10 == 0 or processed == total:
                    elapsed = time.time() - start_time
                    speed = processed / elapsed if elapsed > 0 else 1
                    remaining = total - processed
                    eta = remaining / speed
                    eta_str = f"{int(eta//60)}m {int(eta%60)}s" if eta > 60 else f"{int(eta)}s"
                    print(f"\r{LB}[{W}{processed}{LB}/{W}{total}{LB}] {LC}ALIVE: {G}{alive_count} {LB}| {Y}ETA: {eta_str} {RE}", end="", flush=True)
    chunks = [ip_list[i::threads_count] for i in range(threads_count)]
    threads = []
    for chunk in chunks:
        if not chunk: continue
        t = threading.Thread(target=worker, args=(chunk,))
        t.daemon = True
        t.start()
        threads.append(t)
    for t in threads: t.join()
    print(f"\n\n{Back.GREEN}{W} DONE {RE} {G}FINISHED. {W}{alive_count} {G}IPs SAVED TO IP.txt.{RE}")

def generate_pattern_ips(pattern):
    def expand_part(part):
        options = []
        if 'x' in part:
            for digit in range(10):
                new_part = part.replace('x', str(digit), 1)
                options.extend(expand_part(new_part))
            return options
        else:
            try:
                val = int(part)
                return [str(val)] if 0 <= val <= 255 else []
            except: return []
    parts = pattern.split('.')
    if len(parts) != 4: return []
    try:
        p1, p2, p3, p4 = expand_part(parts[0]), expand_part(parts[1]), expand_part(parts[2]), expand_part(parts[3])
        return list(set([f"{i}.{j}.{k}.{l}" for i in p1 for j in p2 for k in p3 for l in p4]))
    except: return []

def masscan_converter():
    options = {"1": "IP", "2": "CIDR", "3": "IP:PORT"}
    print(f"\n{Y}CONVERT FROM:{RE}")
    for k, v in options.items(): print(f"{B}[{k}] {LC}{v}{RE}")
    from_choice = input(f"\n{LC}SELECT: {W}").strip()
    if from_choice not in options: return []
    print(f"\n{Y}CONVERT TO:{RE}")
    for k, v in options.items():
        if k != from_choice: print(f"{B}[{k}] {LC}{v}{RE}")
    to_choice = input(f"\n{LC}SELECT: {W}").strip()
    file_name = input(f"\n{W}SOURCE FILE: {RE}").strip()
    if not os.path.exists(file_name): return []
    with open(file_name, "r") as f: lines = [l.strip() for l in f.readlines() if l.strip()]
    results = []
    if to_choice == '2':
        print(f"\n{CY}[1] {W}Manual Mask")
        print(f"{CY}[2] {W}Smart Aggregation")
        sub_mode = input(f"{LC}SUB-MODE: {W}").strip()
        if sub_mode == '2':
            raw_ips = []
            for line in lines:
                found = re.findall(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", line)
                if found: raw_ips.append(ipaddress.ip_address(found[0]))
            results = [str(net) for net in ipaddress.collapse_addresses(raw_ips)]
            return results
    if from_choice == '1':
        if to_choice == '2':
            mask = input(f"{W}TARGET MASK: {RE}").strip()
            for ip in lines:
                try: results.append(str(ipaddress.ip_network(f"{ip}/{mask}", strict=False)))
                except: continue
        elif to_choice == '3':
            port = input(f"{W}PORT: {RE}").strip()
            results = [f"{ip}:{port}" for ip in lines]
    return list(set(results))

def main():
    try:
        parser = argparse.ArgumentParser(description="NL Master Generator - CLI Mode", add_help=False)
        parser.add_argument("-c", "--country", help="Country ISO code(s)")
        parser.add_argument("-b", "--block", help="Specific block (8, 24, 16) or 'all'")
        parser.add_argument("-l", "--limit", help="IPs per block / Total for Global")
        parser.add_argument("-ty", "--type", choices=['cidr', 'ip'], help="Save as CIDR blocks or single IPs")
        parser.add_argument("--pattern", nargs='?', const='ASK', help="IP Pattern (e.g. 156.x.x.x)")
        parser.add_argument("--global_scan", nargs='?', const='ASK', help="Start Global Scan with prefix")
        parser.add_argument("-t", "--threads", type=int, default=150)
        parser.add_argument("-p", "--ping", action="store_true")
        parser.add_argument("--how", action="store_true")
        parser.add_argument("-h", "--help", action="help")
        
        args, unknown = parser.parse_known_args()

        if args.how:
            show_how_to_use()
            sys.exit()

        target_ips = []

        if args.country or args.pattern or args.global_scan:
            if args.global_scan:
                prefix = args.global_scan
                if prefix == 'ASK':
                    prefix = input(f"{W}GLOBAL PREFIX (e.g. 156): {RE}").strip()
                
                count_input = args.limit
                if not count_input:
                    count_input = input(f"{W}IPS TO GENERATE (e.g. 5000 or all): {RE}").strip().lower()
                
                if count_input == 'all':
                    num_to_gen = 16777216
                else:
                    try: num_to_gen = int(count_input)
                    except: num_to_gen = 5000
                target_ips = [f"{prefix}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}" for _ in range(num_to_gen)]
            
            elif args.country:
                block_val = args.block if args.block else input(f"{W}SPECIFIC BLOCK (or Enter for all): {RE}").strip()
                cidrs = fetch_country_ips(args.country, block_val if block_val else "all")
                if not cidrs: sys.exit()
                
                save_type = args.type
                if not save_type:
                    print(f"\n{Y}[1] Save as CIDR Blocks (Recommended for 'all' to avoid hanging)")
                    print(f"{Y}[2] Extract Single IPs")
                    choice = input(f"{LC}CHOICE: {W}").strip()
                    save_type = 'cidr' if choice == '1' else 'ip'
                
                if save_type == 'cidr':
                    with open("IP.txt", "w") as f:
                        for line in cidrs: f.write(line + "\n")
                    print(f"{G}[SUCCESS] {len(cidrs)} Blocks saved to IP.txt.{RE}")
                    sys.exit()
                else:
                    limit_val = args.limit if args.limit else input(f"{W}IPs per block (or all): {RE}").strip()
                    target_ips = extract_sample_ips(cidrs, limit_val if limit_val else "all")
            
            elif args.pattern:
                p_val = args.pattern
                if p_val == 'ASK': p_val = input(f"{W}PATTERN (use x): {RE}").strip()
                target_ips = generate_pattern_ips(p_val)
            
            if target_ips:
                if args.ping: filter_alive_ips(target_ips, args.threads)
                else:
                    with open("IP.txt", "w") as f:
                        for ip in target_ips: f.write(ip + "\n")
                    print(f"{G}[SUCCESS] {len(target_ips)} IPs saved to IP.txt{RE}")
            sys.exit()

        while True:
            os.system('clear' if os.name != 'nt' else 'cls')
            print(f"{MAG}###{CY}###{G}###{Y}###{B}###{R}###{MAG}###{CY}###{G}###{Y}###{B}###{R}###{MAG}###{CY}###{G}###{Y}###{B}")
            print(f"{MAG}#      {LY}NL MASTER GENERATOR - {LW}ULTIMATE v8.5{B}      #")
            print(f"{CY}#    {LC}(Full 0-255 Range & ipverse Support){G}       #")
            print(f"{MAG}###{CY}###{G}###{Y}###{B}###{R}###{MAG}###{CY}###{G}###{Y}###{B}###{R}###{MAG}###{CY}###{G}###{Y}###{B}{RE}\n")
            print(f"{G}[1] {LBK}Reference IP (Neighbors Scan)")
            print(f"{G}[2] {G}Company Networks (Massive Blocks)")
            print(f"{G}[3] {Y}Target by Country (Real ipverse Data)")
            print(f"{G}[4] {B}DEEP GLOBAL SCAN (Full 16.7M IPs)")
            print(f"{G}[5] {CY}SMART PATTERN (Logic X Engine)")
            print(f"{G}[6] {LC}MASSCAN/IP CONVERTER (File Tool)")
            print(f"{G}[7] {LY}HOW TO USE / CLI EXAMPLES")
            print(f"{G}[0] {LR}EXIT TOOL{LR}")
            
            mode_choice = input(f"\n{LC}MODE >> {W}").strip().lower()

            if mode_choice in ['0', 'exit']:
                goodbye()

            if mode_choice == '1':
                ref_ip = input(f"{W}IP: {RE}").strip()
                count_in = input(f"{W}COUNT (or all): {RE}").strip().lower()
                parts = ref_ip.split('.')
                prefix = f"{parts[0]}.{parts[1]}.{parts[2]}."
                target_ips = [f"{prefix}{i}" for i in range(256)] if count_in == 'all' else [f"{prefix}{i}" for i in range(int(count_in))]
            elif mode_choice == '2':
                for k, v in COMPANIES.items(): print(f"{B}[{k}] {LC}{v['name']}{RE}")
                choices = input(f"\n{Y}SELECT ID: {W}").strip()
                count_in = input(f"{W}IPs PER CO: {RE}").strip().lower()
                for c in choices:
                    if c in COMPANIES:
                        p = COMPANIES[c]['prefix']
                        target_num = 10000 if count_in == 'all' else int(count_in)
                        for _ in range(target_num):
                            target_ips.append(f"{p}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}")
            elif mode_choice == '3':
                show_countries_menu()
                c_codes = input(f"{W}ENTER COUNTRY CODE(S): {RE}").lower().strip()
                s_blocks = input(f"{W}SPECIFIC BLOCK (or Enter for all): {RE}").strip()
                cidrs = fetch_country_ips(c_codes, s_blocks if s_blocks else "all")
                if cidrs:
                    print(f"\n{Y}[1] Save as CIDR Blocks")
                    print(f"{Y}[2] Extract Single IPs")
                    choice = input(f"{LC}CHOICE: {W}").strip()
                    if choice == '1':
                        with open("IP.txt", "w") as f:
                            for line in cidrs: f.write(line + "\n")
                        print(f"{G}[SUCCESS] {len(cidrs)} Blocks saved to IP.txt.{RE}"); time.sleep(2); continue
                    else:
                        limit_in = input(f"{W}IPs per block (or all): {RE}").strip().lower()
                        target_ips = extract_sample_ips(cidrs, limit_in)
            elif mode_choice == '4':
                prefix = input(f"{W}STARTING PREFIX (e.g. 156): {RE}").strip()
                count = input(f"{W}IPS TO GENERATE (or all for 20k): {RE}").strip().lower()
                num = 16,777,216 if count == 'all' else int(count)
                target_ips = [f"{prefix}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}" for _ in range(num)]
            elif mode_choice == '5':
                pattern = input(f"{W}PATTERN (use x): {RE}").strip()
                target_ips = generate_pattern_ips(pattern)
            elif mode_choice == '6':
                target_ips = masscan_converter()
            elif mode_choice == '7':
                show_how_to_use()
                input(f"\n{Y}Press Enter to return...{RE}"); continue

            if target_ips:
                print(f"\n{LC}[*] {W}IPS IN BUFFER: {Y}{len(target_ips)}{RE}")
                verify = input(f"{MAG}PING VERIFICATION? (y/n): {W}").lower()
                if verify == 'y': filter_alive_ips(target_ips)
                else:
                    with open("IP.txt", "w") as f:
                        for ip in target_ips: f.write(ip + "\n")
                    print(f"\n{Back.GREEN}{W} SUCCESS {RE} {G}SAVED TO IP.txt{RE}")
                input(f"\n{Y}Press Enter to return to menu...{RE}")
                target_ips = []

    except KeyboardInterrupt:
        goodbye()
    except EOFError:
        goodbye()

if __name__ == "__main__":
    main()
