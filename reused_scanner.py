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
    """Fetch transaction data for a Bitcoin address"""
    url = f"https://blockchain.info/rawaddr/{address}"
    
    # Headers to avoid being blocked
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive'
    }
    
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            print(f"Fetching data for address: {address} (Attempt {attempt + 1}/{max_retries})")
            response = requests.get(url, headers=headers, timeout=30)
            
            # Check if request was successful
            if response.status_code == 200:
                try:
                    return response.json()
                except json.JSONDecodeError:
                    print("❌ Invalid JSON response. Retrying...")
                    time.sleep(retry_delay)
                    continue
                    
            elif response.status_code == 429:
                print(f"⚠️  Rate limited by Blockchain.info. Waiting {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                continue
                
            elif response.status_code == 404:
                print("❌ Address not found. Please check the address and try again.")
                return None
                
            else:
                print(f"❌ Error: Status code {response.status_code}")
                print(f"Response: {response.text[:200]}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                return None
                
        except requests.exceptions.Timeout:
            print(f"⚠️  Connection timeout. Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
            continue
            
        except requests.exceptions.ConnectionError:
            print(f"⚠️  Connection error. Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
            continue
            
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                continue
            return None
    
    print("❌ Max retries exceeded. Please try again later.")
    return None

def extract_r_value(script):
    """Extract R value from script signature"""
    if not script or len(script) < 74:
        return None
    
    # The R value is typically at positions 10:74 in the script
    # This is a simplified extraction - adjust based on actual script format
    try:
        # Look for the signature pattern
        r_value = script[10:74]
        return r_value if r_value else None
    except:
        return None

def main():
    print_logo()
    print("WELCOME TO Reused R Scanner 0.2!\n")
    print("="*60)
    print("This tool scans Bitcoin transactions for reused R values")
    print("which could indicate a security vulnerability.")
    print("="*60)
    print()
    
    address = input("Enter the Bitcoin address to scan: ").strip()
    if not address:
        print("❌ No address entered. Exiting.")
        return
    
    # Validate address format (basic check)
    if not address or len(address) < 20:
        print("❌ Invalid Bitcoin address format.")
        return
    
    address_data = get_address_data(address)
    
    if not address_data:
        print("\n" + "="*60)
        print("❌ Failed to fetch data. Possible reasons:")
        print("  - Rate limited (try again in a few minutes)")
        print("  - Invalid Bitcoin address")
        print("  - Network connection issue")
        print("  - API is temporarily down")
        print("\n💡 Tips:")
        print("  - Wait a moment and try again")
        print("  - Verify the Bitcoin address is correct")
        print("  - Try a different address")
        print("="*60)
        return
    
    # Check if address_data contains expected fields
    if 'n_tx' not in address_data:
        print("❌ Unexpected API response format.")
        print(f"Response keys: {list(address_data.keys())}")
        return
    
    num_txs = address_data.get('n_tx', 0)
    print(f"\n" + "="*60)
    print(f"📊 Data for address: {address}")
    print(f"📝 Number of transactions: {num_txs}")
    print("="*60 + "\n")

    if num_txs == 0:
        print("ℹ️  No transactions found for this address.")
        return

    # Store transaction data with their R values
    tx_r_values = []
    processed_txs = 0
    
    print("Processing transactions...")
    for tx in tqdm(address_data['txs'], desc="Processing", unit="tx"):
        processed_txs += 1
        
        # Get transaction hash
        tx_hash = tx.get('hash', 'Unknown')
        
        # Get inputs
        inputs = tx.get('inputs', [])
        if not inputs:
            continue
            
        for input_script in inputs:
            script = input_script.get('script', '')
            if script:
                r_value = extract_r_value(script)
                if r_value:
                    tx_r_values.append({
                        'tx_hash': tx_hash,
                        'r_value': r_value,
                        'script': script[:100]  # Store beginning of script
                    })
    
    if not tx_r_values:
        print("\nℹ️  No input scripts with R values found to analyze.")
        return
    
    print(f"\n📊 Analyzed {len(tx_r_values)} input scripts from {processed_txs} transactions.")
    print("Comparing for reused R values...\n")
    
    # Find reused R values and group them by R value
    reused_r_map = {}
    alert_count = 0
    input_len = len(tx_r_values)
    
    # Only compare if we have at least 2 inputs
    if input_len > 1:
        # Create a progress bar for comparison
        total_comparisons = (input_len - 1) * input_len // 2
        with tqdm(total=total_comparisons, desc="Comparing", unit="cmp") as pbar:
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
        print("ℹ️  Only 1 input found. Need at least 2 to compare for reused R values.")
        return

    # Display results
    print("\n" + "="*60)
    print("SCAN RESULTS")
    print("="*60)
    
    if alert_count == 0:
        print("✅ No Reused R values Found!")
        print("✅ Wallet appears to be safe!")
        print("\n💡 Good security practices:")
        print("  - Continue using unique R values for each transaction")
        print("  - Use updated wallet software")
        print("  - Keep your private keys secure")
    else:
        print(f"⚠️  TOTAL REUSED R VALUES FOUND: {alert_count}")
        print("🔴 WARNING: Wallet is NOT safe!")
        print("🔴 Private key could be compromised!\n")
        
        print("-"*60)
        print("DETAILED RESULTS:")
        print("-"*60)
        
        for idx, (r_value, tx_list) in enumerate(reused_r_map.items(), 1):
            print(f"\n🔹 Reused R Value #{idx}:")
            print(f"   R Value: {r_value[:20]}...{r_value[-10:] if r_value else ''}")
            print(f"   Found in {len(tx_list)} transaction(s):")
            for tx_hash in tx_list:
                print(f"   → Transaction ID: {tx_hash}")
        
        print("\n" + "="*60)
        print("⚠️  ACTION REQUIRED:")
        print("  1. Move ALL funds to a new secure wallet IMMEDIATELY")
        print("  2. DO NOT use this address anymore")
        print("  3. Create a new wallet with proper random number generation")
        print("  4. Consider the compromised private key as exposed")
        print("="*60)
    
    print("\n" + "-"*60)
    print("📊 Summary:")
    print(f"   Total transactions analyzed: {num_txs}")
    print(f"   Total inputs processed: {len(tx_r_values)}")
    print(f"   Reused R values detected: {alert_count}")
    print("-"*60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Scan interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("Please try again or report this issue.")
        sys.exit(1)
    finally:
        print("\nThank you for using BTC Reused R Scanner!")
        sys.exit(0)
