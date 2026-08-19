import json
import requests
import sys
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
#            V0.4             #
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

def main():
    print_logo()
    print("WELCOME TO Reused R Scanner 0.4!\n")
    
    address = input("Enter the Bitcoin address to scan: ").strip()
    if not address:
        print("❌ Invalid address. Please try again.")
        sys.exit(1)
        
    print(f"📡 Fetching data for address: {address}")
    
    try:
        address_data = get_address_data(address)
        num_txs = address_data.get('n_tx', 0)
        
        print(f"\n📊 Data for address: {address}")
        print(f"📊 Number of transactions: {num_txs}\n")
    except Exception as e:
        print(f"❌ Error processing address data: {e}")
        sys.exit(1)

    inputs = []
    tx_details = []  # Store transaction details with their inputs
    
    print("📝 Processing transactions...\n")
    
    for tx in tqdm(address_data.get('txs', []), desc="Processing transactions", unit="tx"):
        print("\n" + "═"*80)
        print(f"📋 Transaction hash: {tx.get('hash', 'Unknown')}")
        print(f"📋 Number of inputs: {tx.get('vin_sz', 0)}")
        print("═"*80)
        
        for idx, input_script in enumerate(tx.get('inputs', [])):
            script = input_script.get('script', '')
            if script and len(script) >= 74:
                inputs.append(script)
                # Store transaction details for each input
                tx_details.append({
                    'tx_hash': tx.get('hash', 'Unknown'),
                    'input_index': idx,
                    'script': script,
                    'r_value': script[10:74],
                    'prev_out': input_script.get('prev_out', {})
                })
                print(f"  ✓ Input #{idx}: R-value extracted: {script[10:74][:20]}...")
    
    if not inputs:
        print("\n❌ No valid input scripts found with R values to compare!")
        sys.exit(0)
    
    print(f"\n📊 Total inputs with R-values extracted: {len(inputs)}")
    print("\n🔍 Comparing input scripts for reused R values...\n")
    
    alert_count = 0
    reused_pairs = []
    input_len = len(inputs)
    
    # Use a dictionary to track R values for better performance
    r_value_map = {}
    
    for i in range(input_len):
        r_val = inputs[i][10:74]
        if r_val in r_value_map:
            r_value_map[r_val].append(i)
        else:
            r_value_map[r_val] = [i]
    
    # Process only R values that appear more than once
    for r_val, indices in r_value_map.items():
        if len(indices) > 1:
            # This R value is reused
            for k in range(len(indices)):
                for l in range(k + 1, len(indices)):
                    alert_count += 1
                    reused_pairs.append({
                        'r_value': r_val,
                        'input1': tx_details[indices[k]],
                        'input2': tx_details[indices[l]]
                    })

    if alert_count == 0:
        print("\n" + "="*80)
        print("✅ No Reused R values Found, seems safe!")
        print("="*80)
    else:
        print("\n" + "="*80)
        print(f"⚠️  ALERT: Total reused R values found: {alert_count}")
        print("⚠️  WARNING: Wallet is not safe!")
        print("="*80)
        print("\n" + "="*80)
        print("🔍 DETAILED REUSED R VALUE INFORMATION:")
        print("="*80)
        print("\n" + "▬"*80)
        
        for pair_num, pair in enumerate(reused_pairs, 1):
            print(f"\n{'='*80}")
            print(f"🔴 REUSED R VALUE PAIR #{pair_num}")
            print(f"{'='*80}")
            print(f"🔑 R Value: {pair['r_value']}")
            
            print("\n" + "─"*40)
            print("📍 INPUT 1 DETAILS:")
            print("─"*40)
            print(f"  🏷️  Transaction Hash: {pair['input1']['tx_hash']}")
            print(f"  🔢 Input Index: {pair['input1']['input_index']}")
            print(f"  📝 Script: {pair['input1']['script'][:100]}..." if len(pair['input1']['script']) > 100 else f"  📝 Script: {pair['input1']['script']}")
            print(f"  🔑 R Value: {pair['input1']['r_value']}")
            
            print("\n" + "─"*40)
            print("📍 INPUT 2 DETAILS:")
            print("─"*40)
            print(f"  🏷️  Transaction Hash: {pair['input2']['tx_hash']}")
            print(f"  🔢 Input Index: {pair['input2']['input_index']}")
            print(f"  📝 Script: {pair['input2']['script'][:100]}..." if len(pair['input2']['script']) > 100 else f"  📝 Script: {pair['input2']['script']}")
            print(f"  🔑 R Value: {pair['input2']['r_value']}")
            
            print("\n" + "─"*40)
            print("⚠️  VULNERABILITY SUMMARY:")
            print("─"*40)
            print(f"  🔴 Same R value used in transaction:")
            print(f"     • {pair['input1']['tx_hash'][:20]}...")
            print(f"     • {pair['input2']['tx_hash'][:20]}...")
            print(f"  ⚠️  This means the same random nonce (R value) was reused")
            print(f"  ⚠️  This is a CRITICAL security vulnerability!")
            print(f"  ⚠️  Private key can be calculated from these two signatures!")
            print("  " + "▬"*40)
        
        print("\n" + "="*80)
        print("🚨 CRITICAL SECURITY RECOMMENDATIONS:")
        print("="*80)
        print("  ❌ DO NOT use this wallet anymore!")
        print("  🔴 Move all funds to a new, secure wallet IMMEDIATELY.")
        print("  🔴 The private key for this address IS COMPROMISED.")
        print("  🔴 Any funds in this wallet are at risk of being stolen.")
        print("="*80)
        print("\n" + "▬"*80)
        print("📊 SUMMARY STATISTICS:")
        print("▬"*80)
        print(f"  • Total transactions analyzed: {num_txs}")
        print(f"  • Total inputs extracted: {len(inputs)}")
        print(f"  • Reused R value pairs found: {alert_count}")
        print(f"  • Unique R values reused: {len([r for r, i in r_value_map.items() if len(i) > 1])}")
        print("▬"*80)

if __name__ == "__main__":
    main()
    sys.exit()
