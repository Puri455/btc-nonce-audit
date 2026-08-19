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
#            V0.3             #
#                             #
###############################
    """
    print(logo)


def get_address_data(address):
    """Fetch address data from blockchain.info"""
    url = f"https://blockchain.info/rawaddr/{address}"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error fetching data: {e}")
        print("Please check your internet connection or the Bitcoin address.")
        sys.exit(1)

def extract_r_value(script):
    """Extract R value from script signature"""
    # R value is typically at position 10-74 in DER encoded signature
    if len(script) >= 74:
        return script[10:74]
    return None

def main():
    print_logo()
    print("WELCOME TO Reused R Scanner 0.3!\n")
    
    address = input("Enter the Bitcoin address to scan: ").strip()
    if not address:
        print("❌ Address cannot be empty!")
        sys.exit(1)
    
    print(f"📡 Fetching data for address: {address}")
    
    address_data = get_address_data(address)
    
    # Check if the response contains expected data
    if 'error' in address_data:
        print(f"❌ API Error: {address_data['error']}")
        sys.exit(1)
    
    # Handle different API response structures
    if 'n_tx' in address_data:
        num_txs = address_data['n_tx']
    elif 'txs' in address_data:
        num_txs = len(address_data['txs'])
    else:
        print("❌ Unexpected API response format. Cannot process transactions.")
        print("Raw response:", json.dumps(address_data, indent=2)[:500])
        sys.exit(1)
    
    print(f"\n✅ Data for address: {address}")
    print(f"📊 Number of transactions: {num_txs}\n")

    if num_txs == 0:
        print("ℹ️ No transactions found for this address.")
        sys.exit(0)

    inputs = []
    tx_details = []  # Store transaction details with their inputs
    
    print("🔄 Processing transactions...")
    
    for tx in tqdm(address_data['txs'], desc="Processing transactions", unit="tx"):
        print("\n" + "="*80)
        print(f"📝 Transaction hash: {tx.get('hash', 'N/A')}")
        print(f"📥 Number of inputs: {tx.get('vin_sz', 0)}")
        
        for idx, input_script in enumerate(tx.get('inputs', [])):
            script = input_script.get('script', '')
            if script and len(script) >= 74:
                inputs.append(script)
                r_value = extract_r_value(script)
                # Store transaction details for each input
                tx_details.append({
                    'tx_hash': tx.get('hash', 'Unknown'),
                    'input_index': idx,
                    'script': script,
                    'r_value': r_value,
                    'prev_out': input_script.get('prev_out', {}),
                    'sequence': input_script.get('sequence', 'N/A')
                })
    
    if len(inputs) < 2:
        print("\nℹ️ Not enough inputs to compare (need at least 2).")
        print("   Need transactions with multiple inputs to check for reused R values.")
        sys.exit(0)
    
    print("\n🔍 Comparing input scripts for reused R values...\n")
    
    alert_count = 0
    reused_pairs = []
    input_len = len(inputs)
    total_comparisons = (input_len - 1) * input_len // 2
    
    print(f"📊 Comparing {input_len} inputs ({total_comparisons} pairs)...")
    
    with tqdm(total=total_comparisons, desc="Comparing inputs", unit="cmp") as pbar:
        for i in range(input_len - 1):
            for j in range(i + 1, input_len):
                if inputs[i][10:74] == inputs[j][10:74]:
                    alert_count += 1
                    # Store pair information
                    reused_pairs.append({
                        'r_value': inputs[i][10:74],
                        'input1': tx_details[i],
                        'input2': tx_details[j],
                        'pair_number': alert_count
                    })
                pbar.update(1)

    print("\n" + "="*80)
    
    if alert_count == 0:
        print("✅ No Reused R values Found - Wallet seems safe!")
        print("   All transactions use unique R values.")
        print("="*80)
    else:
        print(f"⚠️  ALERT: Total reused R values found: {alert_count}")
        print(f"⚠️  WARNING: Wallet is NOT safe!")
        print("="*80)
        print("\n" + "="*80)
        print("📋 DETAILED REUSED R VALUE INFORMATION")
        print("="*80)
        print("\n")
        
        for pair_num, pair in enumerate(reused_pairs, 1):
            print(f"{'='*80}")
            print(f"🔴 REUSED R VALUE PAIR #{pair_num} OF {len(reused_pairs)}")
            print(f"{'='*80}")
            print(f"🔑 R Value (first 64 chars): {pair['r_value']}")
            print("\n" + "-"*40)
            print("📤 INPUT 1 DETAILS:")
            print("-"*40)
            print(f"  🏷️  Transaction Hash: {pair['input1']['tx_hash']}")
            print(f"  🔢 Input Index: {pair['input1']['input_index']}")
            print(f"  🔑 R Value: {pair['input1']['r_value']}")
            
            print("\n" + "-"*40)
            print("📥 INPUT 2 DETAILS:")
            print("-"*40)
            print(f"  🏷️  Transaction Hash: {pair['input2']['tx_hash']}")
            print(f"  🔢 Input Index: {pair['input2']['input_index']}")
            print(f"  🔑 R Value: {pair['input2']['r_value']}")
            
            print("\n" + "-"*40)
            print("⚠️  SECURITY ANALYSIS:")
            print("-"*40)
            print(f"  ⚠️  Same R value used in transactions:")
            print(f"     • {pair['input1']['tx_hash'][:20]}...")
            print(f"     • {pair['input2']['tx_hash'][:20]}...")
            print(f"  🔓 This means the same random nonce (R value) was reused")
            print(f"  💀 This is a CRITICAL security vulnerability!")
            print(f"  🎯 An attacker could potentially recover the private key")
            print(f"     using the two signatures with the same R value.")
            print("\n")
        
        print("="*80)
        print("🚨 URGENT SECURITY RECOMMENDATIONS:")
        print("="*80)
        print("  1. ❌ IMMEDIATELY STOP using this wallet!")
        print("  2. 🏃 Move ALL funds to a new, secure wallet NOW!")
        print("  3. 🔒 Generate a new wallet with a strong random seed")
        print("  4. 🗑️  Never reuse this address or its private key again")
        print("  5. ⚡ The private key may already be compromised")
        print("="*80)
        print("\n" + "="*80)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Scan interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")
        print("Please try again or check the address format.")
        sys.exit(1)
