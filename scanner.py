#!/usr/bin/env python3
"""
BTC Reused R Value Scanner
CryptoAppex Tool V0.3
"""

import sys
import json
import time

# Try importing required modules
try:
    import requests
except ImportError:
    print("Error: 'requests' module not found.")
    print("Please install it using: pip install requests")
    sys.exit(1)

try:
    from tqdm import tqdm
except ImportError:
    print("Error: 'tqdm' module not found.")
    print("Please install it using: pip install tqdm")
    sys.exit(1)

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
#            V0.3             #
#                             #
###############################
    """
    print(logo)

def get_address_data(address):
    """Fetch address data from blockchain.info with error handling"""
    endpoint = f"https://blockchain.info/rawaddr/{address}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        print(f"Fetching data from: {endpoint}")
        response = requests.get(endpoint, headers=headers, timeout=30)
        
        if response.status_code == 200:
            try:
                data = response.json()
                if 'n_tx' in data:
                    print("✓ Successfully fetched data!")
                    return data
                else:
                    print("✗ Response missing expected fields")
                    return None
            except json.JSONDecodeError:
                print("✗ Invalid JSON response")
                return None
        elif response.status_code == 429:
            print("✗ Rate limited! Please wait a moment and try again.")
            return None
        else:
            print(f"✗ HTTP {response.status_code}: {response.reason}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"✗ Request error: {e}")
        return None

def extract_r_value(script):
    """Extract R value from script if present"""
    try:
        # This is a simplified extraction - adjust based on actual script format
        if script and len(script) > 74:
            # Extract potential R value from signature
            r_value = script[10:74]
            return r_value
    except:
        pass
    return None

def main():
    print_logo()
    print("WELCOME TO Reused R Scanner 0.3!\n")
    
    # Get address input
    address = input("Enter the Bitcoin address to scan: ").strip()
    if not address:
        print("Error: Address cannot be empty!")
        sys.exit(1)
    
    print(f"\nScanning address: {address}")
    print("-" * 50)
    
    # Fetch address data
    address_data = get_address_data(address)
    
    if not address_data:
        print("\nFailed to fetch address data. Possible reasons:")
        print("  - Address might not exist or have no transactions")
        print("  - API is rate limiting or temporarily unavailable")
        print("  - Network connectivity issues")
        print("\nTip: Try again in a few minutes, or use a different address.")
        sys.exit(1)
    
    num_txs = address_data.get('n_tx', 0)
    print(f"\nAddress: {address}")
    print(f"Number of transactions: {num_txs}")
    print("-" * 50)
    
    if num_txs == 0:
        print("No transactions found for this address.")
        sys.exit(0)
    
    # Process transactions
    inputs = []
    transactions = address_data.get('txs', [])
    
    print("\nProcessing transactions...")
    for tx in tqdm(transactions, desc="Progress", unit="tx"):
        tx_hash = tx.get('hash', 'Unknown')
        vin_sz = tx.get('vin_sz', 0)
        
        print(f"\nTransaction: {tx_hash[:20]}...")
        print(f"Inputs: {vin_sz}")
        
        for input_script in tx.get('inputs', []):
            script = input_script.get('script', '')
            if script:
                r_value = extract_r_value(script)
                if r_value:
                    inputs.append(r_value)
                    print(f"  ✓ R value extracted")
    
    print(f"\nTotal input scripts processed: {len(inputs)}")
    
    if len(inputs) < 2:
        print("\nNot enough inputs to compare R values (need at least 2).")
        sys.exit(0)
    
    # Compare R values
    print("\nComparing R values for reuse...")
    alert_count = 0
    input_len = len(inputs)
    total_comparisons = (input_len - 1) * input_len // 2
    
    with tqdm(total=total_comparisons, desc="Comparing", unit="cmp") as pbar:
        for i in range(input_len - 1):
            for j in range(i + 1, input_len):
                if inputs[i] == inputs[j]:
                    alert_count += 1
                pbar.update(1)
    
    # Results
    print("\n" + "=" * 50)
    print("SCAN RESULTS")
    print("=" * 50)
    
    if alert_count == 0:
        print("✓ No Reused R values found!")
        print("✓ The wallet appears to be SAFE.")
    else:
        print(f"⚠️  Found {alert_count} reused R values!")
        print(f"⚠️  The wallet is NOT SAFE!")
        print("⚠️  R values are being reused, which could compromise private keys.")
    print("=" * 50)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nScan interrupted by user.")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
    finally:
        sys.exit(0)
