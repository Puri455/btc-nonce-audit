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
    """Fetch transaction data for a Bitcoin address with error handling"""
    url = f"https://blockchain.info/rawaddr/{address}"
    
    # Headers to avoid being blocked
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json'
    }
    
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            print(f"Fetching data (Attempt {attempt + 1}/{max_retries})...")
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                print(f"⚠️  Rate limited. Waiting {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                print(f"❌ Error: Status {response.status_code}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                continue
                
        except requests.exceptions.RequestException as e:
            print(f"⚠️  Connection error: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            continue
    
    print("❌ Failed to fetch data after multiple attempts.")
    return None

def extract_r_value(script):
    """Extract R value from script signature"""
    if not script or len(script) < 74:
        return None
    try:
        return script[10:74]
    except:
        return None

def main():
    print_logo()
    print("WELCOME TO Reused R Scanner 0.2!\n")
    
    address = input("Enter the Bitcoin address to scan: ").strip()
    if not address:
        print("❌ No address entered.")
        return
    
    print(f"Fetching data for address: {address}")
    address_data = get_address_data(address)
    
    if not address_data:
        print("\n❌ Failed to get data. Please check:")
        print("  - Bitcoin address is valid")
        print("  - Internet connection is working")
        print("  - Try again in a few minutes")
        return
    
    if 'n_tx' not in address_data:
        print("❌ Invalid response from API.")
        return
    
    num_txs = address_data['n_tx']
    print(f"\nData for address: {address}")
    print(f"Number of transactions: {num_txs}\n")
    
    if num_txs == 0:
        print("ℹ️  No transactions found for this address.")
        return

    # Store transactions with their R values and hashes
    tx_data = []
    
    for tx in tqdm(address_data['txs'], desc="Processing transactions", unit="tx"):
        print("\n" + "="*80)
        print(f"📝 Transaction hash: {tx['hash']}")
        print(f"📊 Number of inputs: {tx['vin_sz']}")
        
        for input_script in tx['inputs']:
            script = input_script.get('script', '')
            if script:
                r_value = extract_r_value(script)
                if r_value:
                    tx_data.append({
                        'tx_hash': tx['hash'],
                        'r_value': r_value,
                        'script': script
                    })
    
    if not tx_data:
        print("\nℹ️  No valid input scripts found to analyze.")
        return
    
    print(f"\n📊 Found {len(tx_data)} input scripts to analyze.")
    print("🔍 Comparing for reused R values...\n")
    
    # Find reused R values
    reused_map = {}
    alert_count = 0
    input_len = len(tx_data)
    
    if input_len > 1:
        total_cmp = (input_len - 1) * input_len // 2
        with tqdm(total=total_cmp, desc="Comparing inputs", unit="cmp") as pbar:
            for i in range(input_len - 1):
                for j in range(i + 1, input_len):
                    if tx_data[i]['r_value'] and tx_data[j]['r_value']:
                        if tx_data[i]['r_value'] == tx_data[j]['r_value']:
                            r_val = tx_data[i]['r_value']
                            if r_val not in reused_map:
                                reused_map[r_val] = []
                            # Add unique transaction hashes
                            if tx_data[i]['tx_hash'] not in reused_map[r_val]:
                                reused_map[r_val].append(tx_data[i]['tx_hash'])
                            if tx_data[j]['tx_hash'] not in reused_map[r_val]:
                                reused_map[r_val].append(tx_data[j]['tx_hash'])
                            alert_count += 1
                    pbar.update(1)
    else:
        print("ℹ️  Only 1 input found. Need at least 2 to compare.")
        return

    # Display results
    print("\n" + "="*80)
    print("SCAN RESULTS")
    print("="*80)
    
    if alert_count == 0:
        print("\n✅ No Reused R values Found!")
        print("✅ Wallet appears to be SAFE!")
        print("\n💡 Keep up good security practices:")
        print("   • Use updated wallet software")
        print("   • Ensure unique R values for each transaction")
        print("   • Keep private keys secure")
    else:
        print(f"\n⚠️  TOTAL REUSED R VALUES FOUND: {alert_count}")
        print("🔴 WARNING: Wallet is NOT SAFE!")
        print("🔴 Private key could be compromised!\n")
        
        print("-"*80)
        print("📋 DETAILED RESULTS:")
        print("-"*80)
        
        for idx, (r_value, tx_list) in enumerate(reused_map.items(), 1):
            print(f"\n🔹 Reused R Value #{idx}:")
            print(f"   R Value (partial): {r_value[:20]}...{r_value[-10:] if len(r_value) > 20 else ''}")
            print(f"   Found in {len(tx_list)} transaction(s):")
            for tx_hash in tx_list:
                print(f"   → Transaction ID: {tx_hash}")
        
        print("\n" + "="*80)
        print("⚠️  URGENT ACTION REQUIRED:")
        print("  1. Move ALL funds to a NEW secure wallet IMMEDIATELY!")
        print("  2. DO NOT use this address or its private key again")
        print("  3. Create a new wallet with proper random number generation")
        print("  4. Consider this private key as COMPROMISED")
        print("="*80)
    
    print("\n" + "-"*80)
    print("📊 SUMMARY STATISTICS:")
    print(f"   Total transactions analyzed: {num_txs}")
    print(f"   Total inputs processed: {len(tx_data)}")
    print(f"   Reused R values detected: {alert_count}")
    print(f"   Unique R values found: {len(reused_map)}")
    print("-"*80)
    
    print("\n✨ Scan complete!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Scan interrupted by user.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("Please try again or report this issue.")
    finally:
        sys.exit(0)
