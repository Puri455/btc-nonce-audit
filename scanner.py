import json
import requests
import sys
import time
from tqdm import tqdm
import binascii
from urllib.parse import urlencode

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
#            V0.4             #
#                             #
###############################
    """
    print(logo)

class BitcoinScanner:
    def __init__(self):
        self.apis = [
            {
                'name': 'Blockchain.info',
                'url': 'https://blockchain.info/rawaddr/{address}',
                'rate_limit': 3,  # seconds between requests
                'last_request': 0
            },
            {
                'name': 'Blockcypher',
                'url': 'https://api.blockcypher.com/v1/btc/main/addrs/{address}',
                'rate_limit': 1,
                'last_request': 0
            }
        ]
        self.current_api_index = 0
        
    def make_request_with_retry(self, url, max_retries=3, delay=5):
        """Make HTTP request with retry logic"""
        for attempt in range(max_retries):
            try:
                time.sleep(2)  # Base delay between requests
                response = requests.get(url, timeout=30)
                
                if response.status_code == 429:
                    wait_time = delay * (attempt + 1)
                    print(f"Rate limited. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                    
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(delay * (attempt + 1))
                else:
                    raise
        return None

    def get_address_data(self, address):
        """Fetch address data with fallback APIs"""
        # Try primary API
        try:
            print(f"Fetching data using Blockchain.info...")
            url = f"https://blockchain.info/rawaddr/{address}?limit=100"
            data = self.make_request_with_retry(url)
            
            if data and 'txs' in data:
                print(f"✓ Successfully fetched data from Blockchain.info")
                return data
                
        except Exception as e:
            print(f"✗ Blockchain.info failed: {e}")
        
        # Try Blockcypher as fallback
        try:
            print(f"Fetching data using Blockcypher...")
            url = f"https://api.blockcypher.com/v1/btc/main/addrs/{address}"
            data = self.make_request_with_retry(url)
            
            if data and 'txs' in data:
                print(f"✓ Successfully fetched data from Blockcypher")
                # Convert Blockcypher format to match expected format
                return self.convert_blockcypher_data(data, address)
                
        except Exception as e:
            print(f"✗ Blockcypher failed: {e}")
        
        # Try alternative API methods
        try:
            print("Trying alternative blockchain explorer...")
            url = f"https://blockchain.info/rawaddr/{address}?offset=0&limit=50"
            data = self.make_request_with_retry(url)
            
            if data and 'txs' in data:
                print(f"✓ Successfully fetched data")
                return data
                
        except Exception as e:
            print(f"✗ Alternative fetch failed: {e}")
        
        # Try using Sochain API
        try:
            print("Trying Sochain API...")
            url = f"https://sochain.com/api/v2/address/BTC/{address}"
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    print(f"✓ Successfully fetched data from Sochain")
                    return self.convert_sochain_data(data, address)
                    
        except Exception as e:
            print(f"✗ Sochain API failed: {e}")
        
        raise Exception("All APIs failed. Please try again later or use a different address.")

    def convert_blockcypher_data(self, data, address):
        """Convert Blockcypher format to match blockchain.info format"""
        converted = {
            'address': address,
            'n_tx': data.get('total_tx', 0),
            'txs': []
        }
        
        for tx in data.get('txs', []):
            converted_tx = {
                'hash': tx.get('hash', ''),
                'vin_sz': len(tx.get('inputs', [])),
                'inputs': []
            }
            
            for input_data in tx.get('inputs', []):
                script = input_data.get('script', '')
                if script:
                    # Check if script is hex, if not, convert from ascii
                    if not all(c in '0123456789abcdefABCDEF' for c in script):
                        # Try to convert from base64 or other format
                        try:
                            script_bytes = input_data.get('script', '').encode()
                            script = script_bytes.hex()
                        except:
                            script = ''
                    
                    converted_tx['inputs'].append({'script': script})
            
            converted['txs'].append(converted_tx)
        
        return converted

    def convert_sochain_data(self, data, address):
        """Convert Sochain format to match blockchain.info format"""
        converted = {
            'address': address,
            'n_tx': data['data'].get('total_txs', 0),
            'txs': []
        }
        
        # Sochain doesn't give full transaction details in basic address query
        # We need to fetch each transaction separately
        txs = data['data'].get('txs', [])
        print(f"Found {len(txs)} transactions. Fetching details for each...")
        
        for tx_hash in tqdm(txs, desc="Fetching transaction details", unit="tx"):
            try:
                tx_url = f"https://sochain.com/api/v2/tx/BTC/{tx_hash}"
                tx_response = requests.get(tx_url, timeout=10)
                
                if tx_response.status_code == 200:
                    tx_data = tx_response.json()
                    if tx_data.get('status') == 'success':
                        tx_detail = tx_data['data']
                        converted_tx = {
                            'hash': tx_hash,
                            'vin_sz': len(tx_detail.get('inputs', [])),
                            'inputs': []
                        }
                        
                        for input_data in tx_detail.get('inputs', []):
                            # Extract script from input
                            script = input_data.get('script_hex', '')
                            if script:
                                converted_tx['inputs'].append({'script': script})
                        
                        converted['txs'].append(converted_tx)
                
                time.sleep(0.5)  # Rate limit
                
            except Exception as e:
                print(f"Failed to fetch tx {tx_hash}: {e}")
                continue
        
        return converted

def extract_r_from_script(script_hex):
    """
    Extract R value from a Bitcoin script signature (DER format)
    Returns the R value as a hex string or None if not found
    """
    try:
        # Remove any whitespace
        script_hex = script_hex.strip()
        
        # If it's not hex, try to decode
        if not all(c in '0123456789abcdefABCDEF' for c in script_hex):
            return None
            
        # Convert hex to bytes
        script_bytes = bytes.fromhex(script_hex)
        
        # Look for DER signature pattern
        i = 0
        while i < len(script_bytes):
            # Check for push operation (0x47, 0x48, 0x49 for signatures)
            if script_bytes[i] in [0x47, 0x48, 0x49]:
                sig_len = script_bytes[i]
                i += 1
                
                # Check if we have enough bytes for a signature
                if i + sig_len <= len(script_bytes):
                    sig = script_bytes[i:i+sig_len]
                    
                    # Check if it starts with DER sequence marker
                    if sig[0] == 0x30:
                        # Parse DER signature
                        pos = 2  # Skip 0x30 and length byte
                        
                        # Check for integer marker for R
                        if pos < len(sig) and sig[pos] == 0x02:
                            pos += 1  # Skip 0x02
                            if pos < len(sig):
                                r_len = sig[pos]
                                pos += 1  # Skip length byte
                                
                                # Extract R value
                                if pos + r_len <= len(sig):
                                    r_value = sig[pos:pos+r_len]
                                    
                                    # Remove leading zeros if present
                                    while len(r_value) > 1 and r_value[0] == 0x00:
                                        r_value = r_value[1:]
                                    
                                    return r_value.hex()
                break
            i += 1
            
        return None
        
    except (ValueError, IndexError, binascii.Error):
        return None

def main():
    print_logo()
    print("WELCOME TO Reused R Scanner 0.4!\n")
    
    scanner = BitcoinScanner()
    
    while True:
        address = input("Enter the Bitcoin address to scan (or 'quit' to exit): ").strip()
        
        if address.lower() == 'quit':
            print("Goodbye!")
            sys.exit(0)
            
        if not address:
            print("Please enter a valid address.")
            continue
            
        print(f"\nFetching data for address: {address}")
        
        try:
            address_data = scanner.get_address_data(address)
            
            if not address_data:
                print("Failed to fetch address data. Please try again.")
                continue
                
            num_txs = address_data.get('n_tx', 0)
            
            print(f"\n✓ Address: {address}")
            print(f"✓ Number of transactions: {num_txs}")
            print(f"✓ Total transactions found: {len(address_data.get('txs', []))}\n")
            
            if num_txs == 0:
                print("No transactions found for this address.")
                continue
            
            # Process transactions
            all_scripts = []
            tx_info = []
            
            for tx in tqdm(address_data.get('txs', []), desc="Processing transactions", unit="tx"):
                print(f"\nTransaction: {tx.get('hash', 'Unknown')[:20]}...")
                print(f"Inputs: {tx.get('vin_sz', 0)}")
                
                for input_script in tx.get('inputs', []):
                    script = input_script.get('script', '')
                    if script:
                        all_scripts.append(script)
                        tx_info.append({
                            'tx_hash': tx.get('hash', 'Unknown'),
                            'script': script
                        })
            
            if not all_scripts:
                print("\nNo input scripts found in transactions.")
                continue
            
            # Extract R values
            print(f"\nExtracting R values from {len(all_scripts)} input scripts...")
            r_values = []
            
            for script_info in tqdm(tx_info, desc="Extracting R values", unit="script"):
                r_val = extract_r_from_script(script_info['script'])
                if r_val:
                    r_values.append({
                        'tx_hash': script_info['tx_hash'],
                        'r_value': r_val
                    })
            
            print(f"\n✓ Valid R values extracted: {len(r_values)} out of {len(all_scripts)}")
            
            if not r_values:
                print("\nNo valid R values could be extracted from signatures.")
                print("This could mean:")
                print("  - The transactions use non-standard signature formats")
                print("  - The address has no spendable inputs")
                print("  - The data format is not supported")
                continue
            
            # Find duplicate R values
            print("\n🔍 Comparing R values for reuse...")
            
            seen = {}
            duplicates_found = []
            
            for r_data in r_values:
                r_val = r_data['r_value']
                if r_val in seen:
                    duplicates_found.append({
                        'r_value': r_val,
                        'tx1': seen[r_val]['tx_hash'],
                        'tx2': r_data['tx_hash']
                    })
                else:
                    seen[r_val] = {
                        'tx_hash': r_data['tx_hash']
                    }
            
            # Display results
            print("\n" + "="*80)
            if duplicates_found:
                print(f"⚠️  TOTAL REUSED R VALUES FOUND: {len(duplicates_found)}")
                print("="*80)
                
                for i, dup in enumerate(duplicates_found, 1):
                    print(f"\n--- Duplicate #{i} ---")
                    print(f"R Value: {dup['r_value'][:20]}...")
                    print(f"Transaction 1: {dup['tx1']}")
                    print(f"Transaction 2: {dup['tx2']}")
                
                print("\n" + "="*80)
                print("🔴 WARNING: Reused R values detected!")
                print("This wallet is VULNERABLE to private key extraction!")
                print("="*80)
            else:
                print("✅ No duplicate R values found!")
                print("The wallet appears to be safe from R-value reuse attacks.")
                print("="*80)
            
            # Ask if user wants to scan another address
            print("\n" + "="*80)
            print("Scan complete!")
            print("="*80 + "\n")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Please try again with a different address or try again later.")
            continue

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nScan interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        sys.exit(1)
