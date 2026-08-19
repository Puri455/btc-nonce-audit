import json
import requests
import sys
import time
from tqdm import tqdm
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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

def create_session_with_retries():
    """Create a requests session with retry logic"""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def get_address_data_blockchain_info(address):
    """Try blockchain.info API"""
    url = f"https://blockchain.info/rawaddr/{address}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            print("  ⚠️  Rate limited by blockchain.info")
            return None
        else:
            print(f"  ⚠️  blockchain.info returned status {response.status_code}")
            return None
    except Exception as e:
        print(f"  ⚠️  blockchain.info error: {str(e)[:50]}")
        return None

def get_address_data_blockcypher(address):
    """Try blockcypher.com API (more generous rate limits)"""
    url = f"https://api.blockcypher.com/v1/btc/main/addrs/{address}"
    
    try:
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            # Convert blockcypher format to match blockchain.info format
            return {
                'address': address,
                'n_tx': data.get('n_tx', 0),
                'total_received': data.get('total_received', 0),
                'total_sent': data.get('total_sent', 0),
                'balance': data.get('balance', 0),
                'txs': data.get('txs', [])
            }
        else:
            print(f"  ⚠️  blockcypher returned status {response.status_code}")
            return None
    except Exception as e:
        print(f"  ⚠️  blockcypher error: {str(e)[:50]}")
        return None

def get_address_data_mempool(address):
    """Try mempool.space API (open source, good rate limits)"""
    url = f"https://mempool.space/api/address/{address}"
    
    try:
        # First get address info
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            # Get transaction details
            tx_url = f"https://mempool.space/api/address/{address}/txs"
            tx_response = requests.get(tx_url, timeout=30)
            
            txs = []
            if tx_response.status_code == 200:
                txs = tx_response.json()
            
            return {
                'address': address,
                'n_tx': len(txs),
                'total_received': data.get('chain_stats', {}).get('received', 0) + data.get('mempool_stats', {}).get('received', 0),
                'total_sent': data.get('chain_stats', {}).get('sent', 0) + data.get('mempool_stats', {}).get('sent', 0),
                'balance': data.get('chain_stats', {}).get('balance', 0) + data.get('mempool_stats', {}).get('balance', 0),
                'txs': txs
            }
        else:
            print(f"  ⚠️  mempool.space returned status {response.status_code}")
            return None
    except Exception as e:
        print(f"  ⚠️  mempool.space error: {str(e)[:50]}")
        return None

def get_address_data(address):
    """Try multiple APIs to get address data"""
    print("\nAttempting to fetch data from multiple APIs...")
    
    # Try mempool.space first (best rate limits)
    print("  📡 Trying mempool.space...")
    data = get_address_data_mempool(address)
    if data and data.get('n_tx', 0) > 0:
        print("  ✅ Successfully fetched data from mempool.space")
        return data
    
    # Try blockcypher
    print("  📡 Trying blockcypher...")
    time.sleep(1)  # Small delay between API calls
    data = get_address_data_blockcypher(address)
    if data and data.get('n_tx', 0) > 0:
        print("  ✅ Successfully fetched data from blockcypher")
        return data
    
    # Try blockchain.info as last resort
    print("  📡 Trying blockchain.info...")
    time.sleep(1)
    data = get_address_data_blockchain_info(address)
    if data and data.get('n_tx', 0) > 0:
        print("  ✅ Successfully fetched data from blockchain.info")
        return data
    
    print("\n❌ All API attempts failed!")
    return None

def get_address_from_user():
    """Get and validate Bitcoin address from user"""
    print("\nExamples of valid Bitcoin addresses:")
    print("  - 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa (Genesis block)")
    print("  - 1LbpBu1oph1VG1hEZpB2CbBq6oF5AuptF1")
    print("  - 1FeexV6bAHb8ybZjqQMjJrcCrHGW9sb6uF (Large transaction)\n")
    
    address = input("Enter the Bitcoin address to scan: ").strip()
    
    # Basic validation
    if not address:
        print("❌ Address cannot be empty.")
        return None
    
    # Check if it looks like a Bitcoin address
    valid_prefixes = ['1', '3', 'bc1']
    if not any(address.startswith(prefix) for prefix in valid_prefixes):
        print("⚠️  Warning: This doesn't look like a standard Bitcoin address.")
        confirm = input("Continue anyway? (y/n): ").strip().lower()
        if confirm != 'y':
            return None
    
    return address

def extract_r_value(script):
    """Extract R value from input script (simplified)"""
    try:
        # This is a simplified extraction - real R extraction would need proper parsing
        # Looking for signature pattern in the script
        if len(script) > 140:  # Minimum length for a signature
            # In Bitcoin scripts, R is typically at positions 6-38 of the signature
            # But this is highly simplified and might not work for all transactions
            return script[10:74]  # As used in original script
    except:
        pass
    return None

def main():
    print_logo()
    print("WELCOME TO Reused R Scanner 0.3!\n")
    print("This tool checks for reused nonce (R) values in Bitcoin transactions.")
    print("A reused R value can compromise the private key of the wallet.\n")
    
    address = get_address_from_user()
    if not address:
        print("\nExiting...")
        sys.exit(0)
    
    print(f"\n🔍 Fetching data for address: {address}")
    
    address_data = get_address_data(address)
    
    if not address_data:
        print("\n❌ Failed to fetch data. Please check:")
        print("  1. The address is correct and has transactions")
        print("  2. You have internet connection")
        print("  3. Try a different address like: 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
        print("\n💡 Tip: The address must have at least one transaction to scan.")
        sys.exit(1)
    
    # Check if the address has transactions
    num_txs = address_data.get('n_tx', 0)
    
    print(f"\n📊 Data for address: {address}")
    print(f"📊 Number of transactions: {num_txs}")
    print(f"📊 Balance: {address_data.get('balance', 0) / 100000000:.8f} BTC")
    
    if num_txs == 0:
        print("\n❌ This address has no transactions. Nothing to scan!")
        print("Try an address with transaction history.")
        sys.exit(0)
    
    # Process transactions
    inputs = []
    processed_txs = 0
    
    print("\n🔄 Processing transactions...")
    for tx in tqdm(address_data['txs'], desc="Processing transactions", unit="tx"):
        processed_txs += 1
        tx_hash = tx.get('hash', 'unknown')
        vin_sz = tx.get('vin_sz', 0)
        
        # Get inputs from the transaction
        tx_inputs = tx.get('inputs', [])
        
        for input_script in tx_inputs:
            script = input_script.get('script', '')
            if script:
                r_value = extract_r_value(script)
                if r_value:
                    inputs.append({
                        'script': script,
                        'r_value': r_value,
                        'tx_hash': tx_hash
                    })
    
    if not inputs:
        print("\n❌ No input scripts found to compare!")
        print("This might mean the transactions don't have readable input scripts.")
        sys.exit(0)
    
    print(f"\n📊 Found {len(inputs)} input scripts to analyze")
    
    # Compare R values
    print("\n🔍 Comparing input scripts for reused R values...\n")
    
    reused_count = 0
    input_len = len(inputs)
    total_comparisons = (input_len - 1) * input_len // 2
    
    # Check if we have too many comparisons
    if total_comparisons > 50000:
        print(f"⚠️  Warning: {total_comparisons} comparisons needed. This may take a moment...")
    
    # Compare R values
    r_values = {}
    reused_pairs = []
    
    for i in range(input_len):
        r_val = inputs[i]['r_value']
        if r_val in r_values:
            r_values[r_val].append(i)
        else:
            r_values[r_val] = [i]
    
    # Count reused R values
    for r_val, indices in r_values.items():
        if len(indices) > 1:
            reused_count += len(indices) - 1
            reused_pairs.append((r_val, indices))
    
    print("\n" + "="*60)
    if reused_count == 0:
        print("✅ No Reused R values found. Wallet seems safe!")
        print("✅ The nonces used in this wallet are unique.")
    else:
        print(f"⚠️  Found {reused_count} reused R values across {len(reused_pairs)} different R values!")
        print("⚠️  This wallet is potentially vulnerable to private key extraction!")
        print("\n🔍 Details of reused R values:")
        for r_val, indices in reused_pairs[:5]:  # Show first 5
            print(f"  - R value reused in {len(indices)} inputs")
            for idx in indices[:3]:  # Show first 3 occurrences
                tx_hash = inputs[idx]['tx_hash']
                print(f"    • Transaction: {tx_hash[:20]}...")
        if len(reused_pairs) > 5:
            print(f"  ... and {len(reused_pairs) - 5} more reused R patterns")
    print("="*60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Scan interrupted by user. Exiting...")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
