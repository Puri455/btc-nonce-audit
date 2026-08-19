import json
import requests
import sys
from tqdm import tqdm
import base64
import binascii

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

def extract_r_from_script(script_hex):
    """
    Extract R value from a Bitcoin script signature (DER format)
    Returns the R value as a hex string or None if not found
    """
    try:
        # Remove any whitespace and ensure it's hex
        script_hex = script_hex.strip()
        
        # If it's not hex, try to decode from base64 or other formats
        if not all(c in '0123456789abcdefABCDEF' for c in script_hex):
            return None
            
        # Convert hex to bytes
        script_bytes = bytes.fromhex(script_hex)
        
        # Look for DER signature pattern
        # DER signature: 0x30 [length] 0x02 [r_len] [r] 0x02 [s_len] [s]
        # We need to find the start of the signature in the script
        
        # Common patterns for signatures in scripts
        # Push data operations: 0x47 (71 bytes) or 0x48 (72 bytes) or 0x49 (73 bytes)
        # followed by the signature
        
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
                        # Skip sequence header
                        pos = 2  # Skip 0x30 and length byte
                        
                        # Check for integer marker for R
                        if sig[pos] == 0x02:
                            pos += 1  # Skip 0x02
                            r_len = sig[pos]
                            pos += 1  # Skip length byte
                            
                            # Extract R value
                            r_value = sig[pos:pos+r_len]
                            
                            # Remove leading zeros if present (but keep at least one byte)
                            while len(r_value) > 1 and r_value[0] == 0x00:
                                r_value = r_value[1:]
                            
                            return r_value.hex()
                break
            i += 1
            
        return None
        
    except (ValueError, IndexError, binascii.Error):
        return None

def get_address_data(address):
    """Fetch transaction data for a Bitcoin address"""
    url = f"https://blockchain.info/rawaddr/{address}"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

def extract_input_scripts(tx):
    """Extract all input scripts from a transaction"""
    scripts = []
    for input_script in tx.get('inputs', []):
        script = input_script.get('script', '')
        if script:
            scripts.append(script)
    return scripts

def compare_r_values(r_values):
    """Compare R values and find duplicates"""
    seen = {}
    duplicates = []
    
    for idx, r_val in enumerate(r_values):
        if r_val is not None:
            if r_val in seen:
                duplicates.append((seen[r_val], idx, r_val))
            else:
                seen[r_val] = idx
    
    return duplicates

def main():
    print_logo()
    print("WELCOME TO Reused R Scanner 0.3!\n")
    
    address = input("Enter the Bitcoin address to scan: ").strip()
    print(f"Fetching data for address: {address}")
    
    address_data = get_address_data(address)
    if not address_data:
        print("Failed to fetch address data. Please check the address and try again.")
        sys.exit(1)
    
    num_txs = address_data.get('n_tx', 0)
    
    print(f"\nData for address: {address}")
    print(f"Number of transactions: {num_txs}\n")
    
    all_scripts = []
    tx_info = []
    
    # Process transactions
    for tx in tqdm(address_data.get('txs', []), desc="Processing transactions", unit="tx"):
        print("\n" + "="*80)
        print(f"Transaction hash: {tx.get('hash', 'Unknown')}")
        print(f"Number of inputs: {tx.get('vin_sz', 0)}")
        
        scripts = extract_input_scripts(tx)
        if scripts:
            all_scripts.extend(scripts)
            # Store which transaction each script belongs to
            for script in scripts:
                tx_info.append({
                    'tx_hash': tx.get('hash', 'Unknown'),
                    'script': script
                })
    
    if not all_scripts:
        print("\nNo input scripts found in transactions.")
        sys.exit(0)
    
    print(f"\nTotal input scripts found: {len(all_scripts)}")
    
    # Extract R values from all scripts
    print("\nExtracting R values from signatures...")
    r_values = []
    
    for script_info in tqdm(tx_info, desc="Extracting R values", unit="script"):
        r_val = extract_r_from_script(script_info['script'])
        r_values.append({
            'tx_hash': script_info['tx_hash'],
            'r_value': r_val,
            'script': script_info['script']
        })
    
    # Count valid R values extracted
    valid_r_values = [r for r in r_values if r['r_value'] is not None]
    print(f"Valid R values extracted: {len(valid_r_values)} out of {len(r_values)}")
    
    if not valid_r_values:
        print("\nNo valid R values could be extracted from signatures.")
        print("This could mean:")
        print("  - The transactions use non-standard signature formats")
        print("  - The address has no spendable inputs")
        print("  - The data format is not supported")
        sys.exit(0)
    
    # Find duplicate R values
    print("\nComparing R values for reuse...\n")
    
    seen = {}
    duplicates_found = []
    
    for idx, r_data in enumerate(valid_r_values):
        r_val = r_data['r_value']
        if r_val in seen:
            duplicates_found.append({
                'r_value': r_val,
                'tx1': seen[r_val]['tx_hash'],
                'tx2': r_data['tx_hash'],
                'script1': seen[r_val]['script'],
                'script2': r_data['script']
            })
        else:
            seen[r_val] = {
                'tx_hash': r_data['tx_hash'],
                'script': r_data['script'],
                'index': idx
            }
    
    # Display results
    if duplicates_found:
        print(f"⚠️  TOTAL REUSED R VALUES FOUND: {len(duplicates_found)}\n")
        print("="*80)
        print("DETAILED RESULTS:")
        print("="*80)
        
        for i, dup in enumerate(duplicates_found, 1):
            print(f"\n--- Duplicate #{i} ---")
            print(f"R Value: {dup['r_value'][:20]}...")
            print(f"Transaction 1: {dup['tx1']}")
            print(f"Transaction 2: {dup['tx2']}")
            print("-"*40)
        
        print("\n" + "="*80)
        print("🔴 WARNING: Reused R values detected!")
        print("This wallet is VULNERABLE to private key extraction!")
        print("="*80)
    else:
        print("✅ No duplicate R values found!")
        print("The wallet appears to be safe from R-value reuse attacks.")
    
    print("\nScan complete.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nScan interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        sys.exit(1)
