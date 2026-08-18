import json
import requests
import sys
from tqdm import tqdm
import time

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
    """Fetch address data from blockchain.info with proper error handling"""
    url = f"https://blockchain.info/rawaddr/{address}"
    
    try:
        # Add a user-agent to avoid being blocked
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        
        # Check if response is successful
        if response.status_code == 404:
            print(f"Error: Address '{address}' not found on blockchain.info")
            return None
        elif response.status_code == 429:
            print("Error: Rate limit exceeded. Please wait a few minutes and try again.")
            return None
        elif response.status_code != 200:
            print(f"Error: HTTP {response.status_code} - {response.reason}")
            return None
        
        # Check if response is empty
        if not response.text or response.text.strip() == '':
            print("Error: Empty response from server")
            return None
        
        # Try to parse JSON
        try:
            return response.json()
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON response from server")
            print(f"Response preview: {response.text[:200]}...")
            return None
            
    except requests.exceptions.ConnectionError:
        print("Error: Network connection failed. Please check your internet connection.")
        return None
    except requests.exceptions.Timeout:
        print("Error: Request timed out. The server might be slow or unreachable.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error: {str(e)}")
        return None

def main():
    print_logo()
    print("WELCOME TO Reused R Scanner 0.1!\n")
    
    address = input("Enter the Bitcoin address to scan: ").strip()
    
    # Basic validation
    if not address or len(address) < 26:
        print("Error: Invalid Bitcoin address format")
        return
    
    print(f"Fetching data for address: {address}")
    
    address_data = get_address_data(address)
    
    if address_data is None:
        print("Failed to fetch address data. Exiting...")
        return
    
    # Check if the response has the expected structure
    if 'n_tx' not in address_data:
        print("Error: Unexpected response structure from server")
        print(f"Response keys: {list(address_data.keys())}")
        return
    
    num_txs = address_data['n_tx']
    
    print(f"\nData for address: {address}")
    print(f"Number of transactions: {num_txs}\n")
    
    if num_txs == 0:
        print("No transactions found for this address.")
        return
    
    # Check if 'txs' exists and is a list
    if 'txs' not in address_data or not isinstance(address_data['txs'], list):
        print("Error: No transaction data found in response")
        return
    
    inputs = []
    for tx in tqdm(address_data['txs'], desc="Processing transactions", unit="tx"):
        print("#################################################################################")
        print(f"Transaction hash: {tx.get('hash', 'Unknown')}")
        print(f"Number of inputs: {tx.get('vin_sz', 0)}")
        
        # Process inputs
        for input_script in tx.get('inputs', []):
            script = input_script.get('script', '')
            if script and len(script) > 74:  # Ensure script is long enough for comparison
                inputs.append(script)
    
    print(f"\nTotal input scripts collected: {len(inputs)}")
    
    if len(inputs) < 2:
        print("Not enough input scripts to compare for R value reuse.")
        return
    
    print("Comparing input scripts for reused R values...\n")
    
    alert_count = 0
    input_len = len(inputs)
    total_comparisons = (input_len - 1) * input_len // 2
    
    with tqdm(total=total_comparisons, desc="Comparing inputs", unit="cmp") as pbar:
        for i in range(input_len - 1):
            for j in range(i + 1, input_len):
                # Extract the R value (assuming it's at positions 10-74 in the script)
                # Note: This is a simplified comparison and might need adjustment
                # based on actual script structure
                try:
                    r_value_i = inputs[i][10:74] if len(inputs[i]) > 74 else None
                    r_value_j = inputs[j][10:74] if len(inputs[j]) > 74 else None
                    
                    if r_value_i and r_value_j and r_value_i == r_value_j:
                        alert_count += 1
                except IndexError:
                    # Skip if script is too short
                    pass
                pbar.update(1)
    
    print("\n" + "="*60)
    if alert_count == 0:
        print("✓ No Reused R values found. Wallet seems safe!")
    else:
        print(f"✗ Total reused R values found: {alert_count}")
        print("⚠️  WARNING: Wallet is not safe!")
    print("="*60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nScan interrupted by user. Exiting...")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
    finally:
        sys.exit(0)

    sys.exit()
