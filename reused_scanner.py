import json
import requests
import sys
from tqdm import tqdm
from collections import defaultdict

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
#            V0.5             #
#                             #
###############################
    """
    print(logo)


def get_address_data(address):
    url = f"https://blockchain.info/rawaddr/{address}"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching data: {e}")
        sys.exit(1)

def extract_r_value(script):
    """Extract R value from script signature (positions 10-74)"""
    if len(script) >= 74:
        return script[10:74]
    return None

def analyze_transactions(address_data):
    """Analyze transactions and extract R values"""
    inputs = []
    tx_details = []
    
    print("\n" + "═"*80)
    print("📊 ANALYZING TRANSACTIONS")
    print("═"*80)
    
    for tx in tqdm(address_data.get('txs', []), desc="Processing transactions", unit="tx"):
        tx_hash = tx.get('hash', 'Unknown')
        vin_sz = tx.get('vin_sz', 0)
        
        # Show transaction info (but not too verbose)
        if vin_sz > 0:
            print(f"\n📋 TX: {tx_hash[:20]}... | Inputs: {vin_sz}")
        
        for idx, input_script in enumerate(tx.get('inputs', [])):
            script = input_script.get('script', '')
            r_value = extract_r_value(script)
            
            if r_value:
                inputs.append(script)
                tx_details.append({
                    'tx_hash': tx_hash,
                    'input_index': idx,
                    'script': script,
                    'r_value': r_value,
                    'prev_out': input_script.get('prev_out', {})
                })
                print(f"  ✓ Input #{idx}: R-value extracted: {r_value[:20]}...")
    
    return inputs, tx_details

def find_reused_r_values(inputs, tx_details):
    """Find reused R values and return detailed information"""
    # Group by R value
    r_value_groups = defaultdict(list)
    
    for i, script in enumerate(inputs):
        r_val = extract_r_value(script)
        if r_val:
            r_value_groups[r_val].append({
                'index': i,
                'tx_detail': tx_details[i]
            })
    
    # Find reused R values (groups with more than 1)
    reused_pairs = []
    for r_val, items in r_value_groups.items():
        if len(items) > 1:
            # Create all pairs from this group
            for i in range(len(items)):
                for j in range(i + 1, len(items)):
                    reused_pairs.append({
                        'r_value': r_val,
                        'input1': items[i]['tx_detail'],
                        'input2': items[j]['tx_detail']
                    })
    
    return reused_pairs

def display_results(reused_pairs, num_txs, total_inputs):
    """Display detailed results"""
    if not reused_pairs:
        print("\n" + "="*80)
        print("✅ No Reused R values Found, seems safe!")
        print("="*80)
        return
    
    print("\n" + "="*80)
    print(f"⚠️  ALERT: Total reused R values found: {len(reused_pairs)}")
    print("⚠️  WARNING: Wallet is not safe!")
    print("="*80)
    
    print("\n" + "═"*80)
    print("🔍 DETAILED REUSED R VALUE INFORMATION")
    print("═"*80)
    
    # Show each pair
    for pair_num, pair in enumerate(reused_pairs, 1):
        print(f"\n{'='*80}")
        print(f"🔴 REUSED R VALUE PAIR #{pair_num}")
        print(f"{'='*80}")
        
        # R Value
        print(f"\n🔑 R VALUE: {pair['r_value']}")
        print("─"*40)
        
        # Input 1
        print("\n📍 INPUT 1:")
        print("─"*40)
        print(f"  🏷️  Transaction Hash: {pair['input1']['tx_hash']}")
        print(f"  🔢 Input Index: {pair['input1']['input_index']}")
        r_val1 = pair['input1']['r_value']
        print(f"  🔑 R Value: {r_val1}")
        
        # Show script (truncated if too long)
        script1 = pair['input1']['script']
        if len(script1) > 100:
            print(f"  📝 Script: {script1[:100]}...")
        else:
            print(f"  📝 Script: {script1}")
        
        # Input 2
        print("\n📍 INPUT 2:")
        print("─"*40)
        print(f"  🏷️  Transaction Hash: {pair['input2']['tx_hash']}")
        print(f"  🔢 Input Index: {pair['input2']['input_index']}")
        r_val2 = pair['input2']['r_value']
        print(f"  🔑 R Value: {r_val2}")
        
        # Show script (truncated if too long)
        script2 = pair['input2']['script']
        if len(script2) > 100:
            print(f"  📝 Script: {script2[:100]}...")
        else:
            print(f"  📝 Script: {script2}")
        
        # Vulnerability explanation
        print("\n" + "─"*40)
        print("⚠️  VULNERABILITY DETAILS:")
        print("─"*40)
        print(f"  🔴 Same R value used in two different transactions")
        print(f"  🔴 Transaction 1: {pair['input1']['tx_hash'][:30]}...")
        print(f"  🔴 Transaction 2: {pair['input2']['tx_hash'][:30]}...")
        print("  ⚠️  The same random nonce (R) was reused")
        print("  ⚠️  This is a CRITICAL security vulnerability!")
        print("  ⚠️  Private key can be calculated from these two signatures!")
        print("  ⚠️  All funds in this wallet are at risk!")
        
        print("\n" + "─"*40)
        print("📊 MATCH DETAILS:")
        print("─"*40)
        print(f"  ✅ R Value Match: {r_val1 == r_val2}")
        print(f"  🔢 Input positions: {pair['input1']['input_index']} and {pair['input2']['input_index']}")
        
        print("\n" + "▬"*40)
    
    # Summary Statistics
    print("\n" + "═"*80)
    print("📊 SUMMARY STATISTICS")
    print("═"*80)
    print(f"  • Total transactions analyzed: {num_txs}")
    print(f"  • Total inputs extracted: {total_inputs}")
    print(f"  • Reused R value pairs found: {len(reused_pairs)}")
    
    # Count unique R values
    unique_r_values = set()
    for pair in reused_pairs:
        unique_r_values.add(pair['r_value'])
    print(f"  • Unique R values reused: {len(unique_r_values)}")
    
    # List affected transactions
    affected_txs = set()
    for pair in reused_pairs:
        affected_txs.add(pair['input1']['tx_hash'])
        affected_txs.add(pair['input2']['tx_hash'])
    print(f"  • Affected transactions: {len(affected_txs)}")
    
    print("\n" + "═"*80)
    print("🚨 CRITICAL SECURITY RECOMMENDATIONS")
    print("═"*80)
    print("  ❌ DO NOT use this wallet anymore!")
    print("  🔴 Move all funds to a new, secure wallet IMMEDIATELY.")
    print("  🔴 The private key for this address IS COMPROMISED.")
    print("  🔴 Any funds in this wallet are at risk of being stolen.")
    print("  🔴 This is a well-known vulnerability (Nonce Reuse)")
    print("="*80)
    
    # Show affected transaction list
    print("\n" + "═"*80)
    print("📋 AFFECTED TRANSACTIONS")
    print("═"*80)
    for idx, tx_hash in enumerate(sorted(affected_txs), 1):
        print(f"  {idx}. {tx_hash}")
    print("═"*80)

def main():
    print_logo()
    print("WELCOME TO Reused R Scanner 0.5!\n")
    
    address = input("Enter the Bitcoin address to scan: ").strip()
    if not address:
        print("❌ Invalid address. Please try again.")
        sys.exit(1)
    
    print(f"\n📡 Fetching data for address: {address}")
    print("⏳ Please wait, this may take a moment...")
    
    try:
        address_data = get_address_data(address)
        num_txs = address_data.get('n_tx', 0)
        
        print(f"\n📊 Address: {address}")
        print(f"📊 Total Transactions: {num_txs}")
        print("═"*80)
        
    except Exception as e:
        print(f"❌ Error processing address data: {e}")
        sys.exit(1)
    
    # Analyze transactions
    inputs, tx_details = analyze_transactions(address_data)
    
    if not inputs:
        print("\n❌ No valid input scripts with R values found!")
        sys.exit(0)
    
    print(f"\n📊 Total inputs with R-values extracted: {len(inputs)}")
    print("\n🔍 Comparing input scripts for reused R values...\n")
    
    # Find reused R values
    reused_pairs = find_reused_r_values(inputs, tx_details)
    
    # Display results
    display_results(reused_pairs, num_txs, len(inputs))

if __name__ == "__main__":
    main()
    sys.exit()
