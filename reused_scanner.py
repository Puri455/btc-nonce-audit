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
    if len(script) >= 74:
        return script[10:74]
    return None

def print_detailed_results(reused_pairs, total_inputs, total_comparisons):
    """Print detailed information about reused R values"""
    
    print("\n" + "="*80)
    print("📋 FULL DETAILS OF REUSED R VALUES")
    print("="*80)
    print("\n")
    
    # Summary
    print("📊 SCAN SUMMARY:")
    print("-"*80)
    print(f"   Total Reused R Values Found: {len(reused_pairs)}")
    print(f"   Total Inputs Analyzed: {total_inputs}")
    print(f"   Total Comparisons Made: {total_comparisons}")
    print("-"*80)
    print("\n")
    
    # Detailed breakdown of each R value reuse
    for pair_num, pair in enumerate(reused_pairs, 1):
        print(f"{'='*80}")
        print(f"🔴 REUSED R VALUE PAIR #{pair_num} of {len(reused_pairs)}")
        print(f"{'='*80}")
        
        # R Value Details
        print(f"\n🔑 REUSED R VALUE:")
        print(f"   Value (hex): {pair['r_value']}")
        print(f"   Length: {len(pair['r_value'])} characters")
        if len(pair['r_value']) > 20:
            print(f"   Preview: {pair['r_value'][:20]}... (truncated)")
        print(f"   Full Value: {pair['r_value']}")
        
        # INPUT 1 Details
        print(f"\n📤 INPUT 1 (Index #{pair['index1']}):")
        print("-"*60)
        print(f"   Transaction Hash: {pair['input1']['tx_hash']}")
        print(f"   Input Index: {pair['input1']['input_index']}")
        print(f"   R Value: {pair['input1']['r_value']}")
        print(f"   Script Length: {len(pair['input1']['script'])} bytes")
        print(f"   Full Script: {pair['input1']['script']}")
        
        # INPUT 2 Details
        print(f"\n📥 INPUT 2 (Index #{pair['index2']}):")
        print("-"*60)
        print(f"   Transaction Hash: {pair['input2']['tx_hash']}")
        print(f"   Input Index: {pair['input2']['input_index']}")
        print(f"   R Value: {pair['input2']['r_value']}")
        print(f"   Script Length: {len(pair['input2']['script'])} bytes")
        print(f"   Full Script: {pair['input2']['script']}")
        
        # Security Risk Assessment
        print(f"\n⚠️  SECURITY RISK ASSESSMENT:")
        print("-"*60)
        if pair['input1']['tx_hash'] == pair['input2']['tx_hash']:
            print("   🔴 CRITICAL: Same transaction!")
            print("   🔴 Multiple inputs in the same transaction using same R value")
        else:
            print("   🔴 CRITICAL: Different transactions!")
            print("   🔴 Same R value used across multiple transactions")
        
        print(f"   📍 Transaction 1: {pair['input1']['tx_hash']}")
        print(f"   📍 Transaction 2: {pair['input2']['tx_hash']}")
        print(f"   🔓 This means the same random nonce (R value) was reused")
        print(f"   💀 This is a CRITICAL security vulnerability!")
        print(f"   🎯 An attacker could potentially recover the private key")
        print(f"   📐 Mathematical attack formula:")
        print(f"      Private Key = (k1 - k2) / (s1 - s2) mod n")
        print(f"      where k is the R value (nonce) used in both signatures")
        
        # Transaction links
        print(f"\n🔗 TRANSACTION LINKS:")
        print("-"*60)
        print(f"   Tx1: https://www.blockchain.com/btc/tx/{pair['input1']['tx_hash']}")
        print(f"   Tx2: https://www.blockchain.com/btc/tx/{pair['input2']['tx_hash']}")
        
        # Specific vulnerability details
        print(f"\n🔐 VULNERABILITY DETAILS:")
        print("-"*60)
        print(f"   Both transactions use the same R value: {pair['r_value'][:30]}...")
        print(f"   The R value is the 'nonce' used in ECDSA signatures")
        print(f"   Reusing a nonce allows private key recovery through:")
        print(f"   1. Using the two signatures (r, s1) and (r, s2)")
        print(f"   2. The private key d = (s1*k - z1) / r")
        print(f"   3. This is a well-known vulnerability in Bitcoin")
        print(f"   ⚡ Risk Level: EXTREME - Private key is likely compromised")
        
        print("\n" + "-"*60)
        print(f"🔴 RECOMMENDED ACTION: DO NOT USE THIS WALLET!")
        print("-"*60)
        print("\n")
    
    # FINAL RECOMMENDATIONS
    print("="*80)
    print("🚨 URGENT SECURITY RECOMMENDATIONS:")
    print("="*80)
    print("\n  1. ❌ IMMEDIATELY STOP using this wallet!")
    print("  2. 🏃 Move ALL funds to a new, secure wallet NOW!")
    print("  3. 🔒 Generate a new wallet with a strong random seed")
    print("  4. 🗑️  Never reuse this address or its private key again")
    print("  5. ⚡ The private key may already be compromised")
    print("  6. 🔐 Use deterministic nonces (RFC 6979) in the future")
    print("  7. 📝 Report this vulnerability if you're not the owner")
    print("\n" + "="*80)

def main():
    print_logo()
    print("WELCOME TO Reused R Scanner 0.4!\n")
    
    # Get address input
    try:
        address = input("Enter the Bitcoin address to scan: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n\n❌ Input cancelled.")
        sys.exit(1)
    
    if not address:
        print("❌ Address cannot be empty!")
        sys.exit(1)
    
    print(f"📡 Fetching data for address: {address}")
    
    try:
        address_data = get_address_data(address)
    except Exception as e:
        print(f"❌ Failed to fetch data: {e}")
        sys.exit(1)
    
    # Check if we got valid data
    if not address_data:
        print("❌ No data received from API")
        sys.exit(1)
    
    # Check for API error
    if 'error' in address_data:
        print(f"❌ API Error: {address_data['error']}")
        sys.exit(1)
    
    # Handle different API response structures
    if 'n_tx' in address_data:
        num_txs = address_data['n_tx']
    elif 'txs' in address_data:
        num_txs = len(address_data['txs'])
    else:
        print("⚠️  Unexpected API response format")
        print(f"Response keys: {list(address_data.keys())}")
        if 'txs' in address_data:
            num_txs = len(address_data['txs'])
        else:
            print("❌ Cannot find transaction data in API response")
            print("Raw response (first 500 chars):")
            print(json.dumps(address_data, indent=2)[:500])
            sys.exit(1)
    
    print(f"\n✅ Data for address: {address}")
    print(f"📊 Number of transactions: {num_txs}\n")

    if num_txs == 0:
        print("ℹ️ No transactions found for this address.")
        sys.exit(0)

    inputs = []
    tx_details = []
    
    print("🔄 Processing transactions...")
    
    # Process transactions with progress bar
    tx_list = address_data.get('txs', [])
    if not tx_list:
        print("❌ No transactions found in the response")
        sys.exit(1)
    
    for tx in tqdm(tx_list, desc="Processing transactions", unit="tx"):
        print("\n" + "="*80)
        print(f"📝 Transaction hash: {tx.get('hash', 'N/A')}")
        print(f"📥 Number of inputs: {tx.get('vin_sz', 0)}")
        
        for idx, input_script in enumerate(tx.get('inputs', [])):
            script = input_script.get('script', '')
            if script and len(script) >= 74:
                inputs.append(script)
                r_value = extract_r_value(script)
                tx_details.append({
                    'tx_hash': tx.get('hash', 'Unknown'),
                    'input_index': idx,
                    'script': script,
                    'r_value': r_value,
                    'prev_out': input_script.get('prev_out', {})
                })
    
    if len(inputs) < 2:
        print("\nℹ️ Not enough inputs to compare (need at least 2).")
        sys.exit(0)
    
    print("\n🔍 Comparing input scripts for reused R values...\n")
    
    alert_count = 0
    reused_pairs = []
    input_len = len(inputs)
    total_comparisons = (input_len - 1) * input_len // 2
    
    with tqdm(total=total_comparisons, desc="Comparing inputs", unit="cmp") as pbar:
        for i in range(input_len - 1):
            for j in range(i + 1, input_len):
                if inputs[i][10:74] == inputs[j][10:74]:
                    alert_count += 1
                    reused_pairs.append({
                        'r_value': inputs[i][10:74],
                        'input1': tx_details[i],
                        'input2': tx_details[j],
                        'index1': i,
                        'index2': j
                    })
                pbar.update(1)

    print("\n" + "="*80)
    
    if alert_count == 0:
        print("✅ No Reused R values Found, seems safe!")
        print("="*80)
    else:
        print(f"⚠️  ALERT: Total reused R values found: {alert_count}")
        print(f"⚠️  WARNING: Wallet is NOT safe!")
        print("="*80)
        
        # Print detailed information about each reused R value
        print_detailed_results(reused_pairs, len(inputs), total_comparisons)
        
        # Brief summary
        print("\n" + "="*80)
        print("📊 QUICK SUMMARY:")
        print("="*80)
        print(f"   Total Reused R Values: {alert_count}")
        print(f"   Affected Inputs: {len(reused_pairs) * 2}")
        print("   Transactions with reused R values:")
        for pair in reused_pairs:
            print(f"   • {pair['input1']['tx_hash']}")
            print(f"   • {pair['input2']['tx_hash']}")

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
