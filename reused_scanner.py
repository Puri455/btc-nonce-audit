import json
import requests
import sys
import time
from tqdm import tqdm

def print_logo():
    logo = r"""
  ______   _______   __      __  _______   ________  ______  
 /      \ /       \ /  \    /  |/       \ /        |/      \ 
/$$$$$$  |$$$$$$$  |$$  \  /$$/ $$$$$$$  |$$$$$$$$//$$$$$$  |
$$ |  $$/ $$ |__$$ | $$  \/$$/  $$ |__$$ |   $$ |  $$ |  $$ |
$$ |      $$    $$<   $$  $$/   $$    $$/    $$ |  $$ |  $$ |
$$ |   __ $$$$$$$  |   $$$$/    $$$$$$$/     $$ |  $$ |  $$ |
$$ \__/  |$$ |  $$ |    $$ |    $$ |         $$ |  $$ \__$$ |
$$    $$/ $$ |  $$ |    $$ |    $$ |         $$ |  $$    $$/ 
 $$$$$$/  $$/   $$/     $$/     $$/          $$/    $$$$$$/                                                 
  ______   _______   ________  __    __                      
 /      \ /       \ /        |/  |  /  |                     
/$$$$$$  |$$$$$$$  |$$$$$$$$/ $$ |  $$ |                     
$$ |__$$ |$$ |__$$ |$$ |__    $$  \/$$/                      
$$    $$ |$$    $$/ $$    |    $$  $$<                       
$$$$$$$$ |$$$$$$$/  $$$$$/      $$$$  \                      
$$ |  $$ |$$ |      $$ |_____  $$ /$$  |                     
$$ |  $$ |$$ |      $$       |$$ |  $$ |                     
$$/   $$/ $$/       $$$$$$$$/ $$/   $$/

###############################
#                             #
#        CryptoAppex          #
# BTC Reused R Value Scanner  #
#            Tool             #
#            V0.2             #
#                             #
###############################
    """
    print(logo)

def get_address_data(address):
    url = f"https://blockchain.info/rawaddr/{address}"
    
    # Add headers to avoid being blocked
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        print(f"Fetching data from: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        
        # Check if request was successful
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            print("⚠️  Rate limited by Blockchain.info. Waiting 10 seconds...")
            time.sleep(10)
            # Retry once
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Failed after retry. Status: {response.status_code}")
                return None
        else:
            print(f"❌ Error: Status code {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
        return None

def main():
    print_logo()
    print("WELCOME TO Reused R Scanner 0.2!\n")
    
    address = input("Enter the Bitcoin address to scan: ").strip()
    if not address:
        print("❌ No address entered. Exiting.")
        return
    
    print(f"Fetching data for address: {address}")
    
    address_data = get_address_data(address)
    
    if not address_data:
        print("\n❌ Failed to fetch data. Possible reasons:")
        print("  - Rate limited (try again in a minute)")
        print("  - Invalid Bitcoin address")
        print("  - Network connection issue")
        print("\n💡 Alternative: Try using a different API or wait a moment.")
        return
    
    # Check if address_data contains expected fields
    if 'n_tx' not in address_data:
        print("❌ Unexpected API response format. Trying to continue...")
        print(f"Response keys: {list(address_data.keys())}")
    
    num_txs = address_data.get('n_tx', 0)
    print(f"\nData for address: {address}")
    print(f"Number of transactions: {num_txs}\n")

    if num_txs == 0:
        print("ℹ️  No transactions found for this address.")
        return

    # Store transaction data with their R values
    tx_r_values = []
    
    for tx in tqdm(address_data['txs'], desc="Processing transactions", unit="tx"):
        print("#################################################################################")
        print(f"Transaction hash: {tx['hash']}")
        print(f"Number of inputs: {tx['vin_sz']}")
        
        for input_script in tx['inputs']:
            script = input_script.get('script', '')
            if script:
                # Extract R value from script (positions 10:74)
                r_value = script[10:74] if len(script) >= 74 else None
                tx_r_values.append({
                    'tx_hash': tx['hash'],
                    'r_value': r_value,
                    'script': script
                })
    
    if not tx_r_values:
        print("\nℹ️  No input scripts found to analyze.")
        return
    
    print(f"\nAnalyzing {len(tx_r_values)} input scripts for reused R values...\n")
    
    # Find reused R values and group them by R value
    reused_r_map = {}
    alert_count = 0
    input_len = len(tx_r_values)
    
    # Only compare if we have at least 2 inputs
    if input_len > 1:
        with tqdm(total=(input_len - 1) * input_len // 2, 
                  desc="Comparing inputs", unit="cmp") as pbar:
            for i in range(input_len - 1):
                for j in range(i + 1, input_len):
                    if tx_r_values[i]['r_value'] and tx_r_values[j]['r_value']:
                        if tx_r_values[i]['r_value'] == tx_r_values[j]['r_value']:
                            r_val = tx_r_values[i]['r_value']
                            if r_val not in reused_r_map:
                                reused_r_map[r_val] = []
                            if tx_r_values[i]['tx_hash'] not in reused_r_map[r_val]:
                                reused_r_map[r_val].append(tx_r_values[i]['tx_hash'])
                            if tx_r_values[j]['tx_hash'] not in reused_r_map[r_val]:
                                reused_r_map[r_val].append(tx_r_values[j]['tx_hash'])
                            alert_count += 1
                    pbar.update(1)
    else:
        print("ℹ️  Only 1 input found. Need at least 2 to compare.")
        return

    # Display results
    if alert_count == 0:
        print("\n" + "="*60)
        print("✅ No Reused R values Found - Wallet seems safe!")
        print("="*60)
    else:
        print("\n" + "="*60)
        print(f"⚠️  TOTAL REUSED R VALUES FOUND: {alert_count}")
        print("="*60)
        print("\n🔴 WARNING: Wallet is NOT safe! Private key could be compromised!\n")
        
        print("-"*60)
        print("DETAILED RESULTS:")
        print("-"*60)
        
        for idx, (r_value, tx_list) in enumerate(reused_r_map.items(), 1):
            print(f"\n🔹 Reused R Value #{idx}: {r_value[:20]}...{r_value[-10:] if r_value else ''}")
            print(f"   Found in {len(tx_list)} transaction(s):")
            for tx_hash in tx_list:
                print(f"   → Transaction ID: {tx_hash}")
        print("\n" + "="*60)
        print("⚠️  ACTION REQUIRED: Move funds to a new secure wallet immediately!")
        print("="*60)

if __name__ == "__main__":
    main()
