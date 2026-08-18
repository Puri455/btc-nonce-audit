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
#            V0.3             #
#                             #
###############################
    """
    print(logo)

def get_address_data(address):
    # Try multiple API endpoints
    urls = [
        f"https://blockchain.info/rawaddr/{address}?cors=true",
        f"https://api.blockcypher.com/v1/btc/main/addrs/{address}",
        f"https://chain.api.btc.com/v3/address/{address}"
    ]
    
    for url in urls:
        try:
            print(f"Trying API: {url.split('/')[2]}...")
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                # Check if we got valid data
                if data and 'txs' in data:
                    print(f"✓ Successfully fetched data from {url.split('/')[2]}")
                    return data
                elif data and 'txs' in data.get('data', {}):
                    # Handle BlockCypher response format
                    print(f"✓ Successfully fetched data from {url.split('/')[2]}")
                    return data
            elif response.status_code == 429:
                print("Rate limited. Waiting 3 seconds...")
                time.sleep(3)
                continue
            else:
                print(f"API returned status {response.status_code}, trying next...")
                continue
        except Exception as e:
            print(f"Error with {url.split('/')[2]}: {str(e)[:50]}...")
            continue
    
    # If all APIs fail, try with user-agent
    print("\nTrying with custom headers...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    try:
        response = requests.get(
            f"https://blockchain.info/rawaddr/{address}",
            headers=headers,
            timeout=15
        )
        if response.status_code == 200:
            return response.json()
    except:
        pass
    
    # If still failing, try alternative blockchain explorer
    print("\nTrying alternative API...")
    try:
        response = requests.get(
            f"https://blockstream.info/api/address/{address}",
            timeout=10
        )
        if response.status_code == 200:
            # Convert blockstream format to match expected format
            data = response.json()
            return {'txs': data.get('txs', []), 'n_tx': len(data.get('txs', []))}
    except:
        pass
    
    print("\n❌ ERROR: Could not fetch data from any API.")
    print("Possible reasons:")
    print("1. The Bitcoin address might be invalid")
    print("2. API rate limits reached (wait a few minutes)")
    print("3. No internet connection")
    print("4. The address has no transactions")
    sys.exit(1)

def main():
    print_logo()
    print("WELCOME TO Reused R Scanner 0.3!\n")
    
    address = input("Enter the Bitcoin address to scan: ").strip()
    print(f"Fetching data for address: {address}")
    
    address_data = get_address_data(address)
    
    # Handle different API response formats
    if 'n_tx' in address_data:
        num_txs = address_data['n_tx']
        txs = address_data['txs']
    elif 'data' in address_data and 'n_tx' in address_data['data']:
        num_txs = address_data['data']['n_tx']
        txs = address_data['data']['txs']
    elif 'txs' in address_data:
        num_txs = len(address_data['txs'])
        txs = address_data['txs']
    else:
        print("❌ Unexpected data format from API")
        sys.exit(1)
    
    print(f"\nData for address: {address}")
    print(f"Number of transactions: {num_txs}\n")
    
    if num_txs == 0:
        print("No transactions found for this address.")
        sys.exit(0)

    # Store transaction data with their R values
    tx_r_values = []
    
    print("Processing transactions...")
    for tx in tqdm(txs, desc="Processing transactions", unit="tx"):
        print("\n" + "="*80)
        print(f"Transaction hash: {tx['hash']}")
        print(f"Number of inputs: {tx.get('vin_sz', 0)}")
        
        # Handle different input formats
        if 'inputs' in tx:
            input_list = tx['inputs']
        elif 'vin' in tx:
            input_list = tx['vin']
        else:
            continue
            
        for input_script in input_list:
            script = input_script.get('script', '')
            if script and len(script) >= 74:
                # Extract R value from script (positions 10:74)
                r_value = script[10:74]
                tx_r_values.append({
                    'tx_hash': tx['hash'],
                    'r_value': r_value,
                    'script': script
                })
    
    if len(tx_r_values) < 2:
        print("\nNot enough inputs to compare R values.")
        sys.exit(0)
    
    print("\nComparing input scripts for reused R values...\n")
    
    # Find reused R values and group them by R value
    reused_r_map = {}
    alert_count = 0
    input_len = len(tx_r_values)
    
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
    
    # Display results
    print("\n" + "="*80)
    print("SCAN RESULTS")
    print("="*80)
    
    if alert_count == 0:
        print("\n✅ No Reused R values Found - Wallet seems safe!")
        print("✅ The private key for this address appears to be secure.")
    else:
        print(f"\n⚠️  TOTAL REUSED R VALUES FOUND: {alert_count}")
        print("⚠️  WARNING: Wallet is NOT safe! Private key could be compromised!")
        print("\n" + "="*80)
        print("DETAILED RESULTS:")
        print("="*80)
        
        for idx, (r_value, tx_list) in enumerate(reused_r_map.items(), 1):
            print(f"\n🔹 Reused R Value #{idx}:")
            print(f"   R Value (partial): {r_value[:20]}...{r_value[-10:]}")
            print(f"   Found in {len(tx_list)} transaction(s):")
            for tx_hash in tx_list:
                print(f"   → TXID: {tx_hash}")
        
        print("\n" + "="*80)
        print("⚠️  ACTION REQUIRED:")
        print("   1. IMMEDIATELY move all funds to a new secure wallet")
        print("   2. The private key for this address is compromised")
        print("   3. Do NOT send any more funds to this address")
        print("="*80)
    
    print(f"\nTotal transactions analyzed: {num_txs}")
    print(f"Total inputs analyzed: {len(tx_r_values)}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nScan interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ An error occurred: {str(e)}")
        sys.exit(1)
    sys.exit(0)
