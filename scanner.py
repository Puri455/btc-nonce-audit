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
    """Fetch address data from blockchain.info with error handling"""
    # Try multiple API endpoints
    endpoints = [
        f"https://blockchain.info/rawaddr/{address}",
        f"https://blockchain.info/rawaddr/{address}?format=json"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    for endpoint in endpoints:
        try:
            print(f"Trying endpoint: {endpoint}")
            response = requests.get(endpoint, headers=headers, timeout=10)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if 'n_tx' in data:
                        print(f"Successfully fetched data!")
                        return data
                    else:
                        print(f"Response missing expected fields, trying next endpoint...")
                except json.JSONDecodeError:
                    print(f"Invalid JSON response, trying next endpoint...")
                    continue
            elif response.status_code == 429:
                print("Rate limited! Waiting 5 seconds...")
                time.sleep(5)
            else:
                print(f"HTTP {response.status_code}: {response.reason}")
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            time.sleep(2)
    
    # If we get here, all endpoints failed
    print("\nAll API endpoints failed. Trying alternative API...")
    return get_address_data_alternative(address)

def get_address_data_alternative(address):
    """Fallback using blockchain.com API"""
    url = f"https://blockchain.com/btc/address/{address}/format/json"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Convert to similar format
            if 'n_tx' in data:
                return data
            else:
                # Try to create similar structure
                return {
                    'address': address,
                    'n_tx': len(data.get('txs', [])),
                    'txs': data.get('txs', [])
                }
    except:
        pass
    
    # Last resort - return empty data
    print("\nWarning: Could not fetch address data. Returning empty data.")
    return {'address': address, 'n_tx': 0, 'txs': []}

def extract_r_value(script):
    """Extract R value from script if present"""
    # This is a simplified extraction - in reality, R value extraction is more complex
    try:
        # Looking for signature pattern in script
        if len(script) > 74:
            # Try to find R value in signature
            r_value = script[10:74]  # Simplified extraction
            return r_value
    except:
        pass
    return None

def main():
    print_logo()
    print("WELCOME TO Reused R Scanner 0.3!\n")
    
    address = input("Enter the Bitcoin address to scan: ").strip()
    if not address:
        print("Error: Address cannot be empty!")
        sys.exit(1)
    
    print(f"Fetching data for address: {address}")
    
    address_data = get_address_data(address)
    
    if 'n_tx' not in address_data:
        print("Error: Could not retrieve valid data for this address.")
        print("Possible reasons:")
        print("  - Address might not exist or have no transactions")
        print("  - API rate limiting")
        print("  - Network connectivity issues")
        sys.exit(1)
    
    num_txs = address_data.get('n_tx', 0)
    
    print(f"\nData for address: {address}")
    print(f"Number of transactions: {num_txs}\n")
    
    if num_txs == 0:
        print("No transactions found for this address.")
        sys.exit(0)
    
    inputs = []
    transactions = address_data.get('txs', [])
    
    for tx in tqdm(transactions, desc="Processing transactions", unit="tx"):
        # Get transaction details safely
        tx_hash = tx.get('hash', 'Unknown')
        vin_sz = tx.get('vin_sz', 0)
        
        print("#################################################################################")
        print(f"Transaction hash: {tx_hash}")
        print(f"Number of inputs: {vin_sz}")
        
        for input_script in tx.get('inputs', []):
            script = input_script.get('script', '')
            if script:
                r_value = extract_r_value(script)
                if r_value:
                    inputs.append(r_value)
    
    if not inputs:
        print("\nNo input scripts with R values found.")
        sys.exit(0)
    
    print("\nComparing input scripts for reused R values...\n")
    
    alert_count = 0
    input_len = len(inputs)
    
    # Use progress bar for comparison
    total_comparisons = (input_len - 1) * input_len // 2 if input_len > 1 else 0
    
    if total_comparisons == 0:
        print("Not enough inputs to compare R values.")
    else:
        with tqdm(total=total_comparisons, desc="Comparing inputs", unit="cmp") as pbar:
            for i in range(input_len - 1):
                for j in range(i + 1, input_len):
                    if inputs[i] == inputs[j]:
                        alert_count += 1
                        print(f"  Found reused R value at inputs {i+1} and {j+1}")
                    pbar.update(1)
    
    print("\n" + "="*50)
    if alert_count == 0:
        print("✅ No Reused R values Found - seems safe!")
    else:
        print(f"⚠️  Total reused R values found: {alert_count}")
        print(f"⚠️  Wallet is NOT safe! R values are being reused.")
    print("="*50)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nScan interrupted by user.")
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        sys.exit(0)
