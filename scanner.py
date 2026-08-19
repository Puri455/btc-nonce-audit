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
    """Fetch transaction data for a Bitcoin address using blockchain.info API"""
    url = f"https://blockchain.info/rawaddr/{address}"
    
    try:
        # Add headers to avoid being blocked
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        
        # Check if the request was successful
        if response.status_code == 429:
            print("\nRate limited! Please wait and try again.")
            print("Blockchain.info has rate limiting. Try a different address or wait a few minutes.")
            return None
            
        if response.status_code != 200:
            print(f"\nError: Received status code {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return None
            
        # Try to parse JSON
        try:
            return response.json()
        except json.JSONDecodeError:
            print("\nError: Invalid JSON response from API")
            print(f"Response preview: {response.text[:200]}")
            return None
            
    except requests.exceptions.Timeout:
        print("\nError: Request timed out. Please try again.")
        return None
    except requests.exceptions.ConnectionError:
        print("\nError: Could not connect to blockchain.info. Please check your internet connection.")
        return None
    except Exception as e:
        print(f"\nError fetching data: {str(e)}")
        return None

def get_address_from_user():
    """Get and validate Bitcoin address from user"""
    address = input("Enter the Bitcoin address to scan: ").strip()
    
    # Basic validation - Bitcoin addresses are typically 26-35 characters
    if not address or len(address) < 26 or len(address) > 35:
        print("Warning: This doesn't look like a valid Bitcoin address.")
        confirm = input("Continue anyway? (y/n): ").strip().lower()
        if confirm != 'y':
            return None
    
    return address

def main():
    print_logo()
    print("WELCOME TO Reused R Scanner 0.1!\n")
    
    address = get_address_from_user()
    if not address:
        print("Exiting...")
        sys.exit(0)
    
    print(f"\nFetching data for address: {address}")
    
    address_data = get_address_data(address)
    
    if not address_data:
        print("\nFailed to fetch data. Please check:")
        print("1. The address is correct")
        print("2. You have internet connection")
        print("3. The blockchain.info API is accessible")
        print("\nAlternative: Try a different Bitcoin address like: 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa (Genesis block address)")
        sys.exit(1)
    
    # Check if the address has transactions
    if 'n_tx' not in address_data:
        print("\nError: No transaction data found for this address.")
        print("The address may not exist or have no transactions.")
        sys.exit(1)
    
    num_txs = address_data['n_tx']
    
    print(f"\nData for address: {address}")
    print(f"Number of transactions: {num_txs}\n")
    
    if num_txs == 0:
        print("This address has no transactions. Nothing to scan!")
        sys.exit(0)
    
    inputs = []
    
    print("Processing transactions...")
    for tx in tqdm(address_data['txs'], desc="Processing transactions", unit="tx"):
        print(f"\nTransaction hash: {tx['hash']}")
        print(f"Number of inputs: {tx['vin_sz']}")
        
        for input_script in tx['inputs']:
            script = input_script.get('script', '')
            if script:
                inputs.append(script)
    
    if not inputs:
        print("\nNo input scripts found to compare!")
        sys.exit(0)
    
    print(f"\nComparing {len(inputs)} input scripts for reused R values...\n")
    
    alert_count = 0
    input_len = len(inputs)
    total_comparisons = (input_len - 1) * input_len // 2
    
    # Limit comparisons if there are too many inputs to avoid long processing
    if total_comparisons > 100000:
        print(f"Warning: {total_comparisons} comparisons needed. This may take a while...")
        continue_anyway = input("Continue? (y/n): ").strip().lower()
        if continue_anyway != 'y':
            print("Exiting...")
            sys.exit(0)
    
    with tqdm(total=total_comparisons, desc="Comparing inputs", unit="cmp") as pbar:
        for i in range(input_len - 1):
            for j in range(i + 1, input_len):
                # Check if the R values match (positions 10-74 in the script)
                # This is a simplified check - real R value extraction would be more complex
                if len(inputs[i]) > 74 and len(inputs[j]) > 74:
                    if inputs[i][10:74] == inputs[j][10:74]:
                        alert_count += 1
                pbar.update(1)
    
    print("\n" + "="*60)
    if alert_count == 0:
        print("✅ No Reused R values found. Wallet seems safe!")
    else:
        print(f"⚠️  Found {alert_count} reused R values. Wallet is potentially vulnerable!")
        print("⚠️  This means the same nonce was used for multiple signatures!")
    print("="*60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nScan interrupted by user. Exiting...")
        sys.exit(0)
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        sys.exit(1)
