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
    url = f"https://blockchain.info/rawaddr/{address}"
    response = requests.get(url)
    return response.json()

def main():
    print_logo()
    print("WELCOME TO Reused R Scanner 0.3!\n")
    
    address = input("Enter the Bitcoin address to scan: ")
    print(f"Fetching data for address: {address}")
    
    address_data = get_address_data(address)
    num_txs = address_data['n_tx']
    
    print(f"\nData for address: {address}")
    print(f"Number of transactions: {num_txs}\n")

    inputs = []
    tx_details = []  # Store transaction details with their inputs
    
    for tx in tqdm(address_data['txs'], desc="Processing transactions", unit="tx"):
        print("#################################################################################")
        print(f"Transaction hash: {tx['hash']}")
        print(f"Number of inputs: {tx['vin_sz']}")
        
        for idx, input_script in enumerate(tx['inputs']):
            script = input_script.get('script', '')
            if script:
                inputs.append(script)
                # Store transaction details for each input
                tx_details.append({
                    'tx_hash': tx['hash'],
                    'input_index': idx,
                    'script': script,
                    'r_value': script[10:74] if len(script) >= 74 else None,
                    'prev_out': input_script.get('prev_out', {})
                })
    
    print("\nComparing input scripts for reused R values...\n")
    
    alert_count = 0
    reused_pairs = []
    input_len = len(inputs)
    
    with tqdm(total=(input_len - 1) * input_len // 2, desc="Comparing inputs", unit="cmp") as pbar:
        for i in range(input_len - 1):
            for j in range(i + 1, input_len):
                if inputs[i][10:74] == inputs[j][10:74]:
                    alert_count += 1
                    # Store pair information
                    reused_pairs.append({
                        'r_value': inputs[i][10:74],
                        'input1': tx_details[i],
                        'input2': tx_details[j]
                    })
                pbar.update(1)

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
        print("DETAILED REUSED R VALUE INFORMATION:")
        print("="*80)
        print("\n")
        
        for pair_num, pair in enumerate(reused_pairs, 1):
            print(f"{'='*80}")
            print(f"REUSED R VALUE PAIR #{pair_num}:")
            print(f"{'='*80}")
            print(f"R Value: {pair['r_value']}")
            print("\n" + "-"*40)
            print("INPUT 1 DETAILS:")
            print("-"*40)
            print(f"  Transaction Hash: {pair['input1']['tx_hash']}")
            print(f"  Input Index: {pair['input1']['input_index']}")
            print(f"  Script: {pair['input1']['script'][:100]}..." if len(pair['input1']['script']) > 100 else f"  Script: {pair['input1']['script']}")
            print(f"  R Value: {pair['input1']['r_value']}")
            
            print("\n" + "-"*40)
            print("INPUT 2 DETAILS:")
            print("-"*40)
            print(f"  Transaction Hash: {pair['input2']['tx_hash']}")
            print(f"  Input Index: {pair['input2']['input_index']}")
            print(f"  Script: {pair['input2']['script'][:100]}..." if len(pair['input2']['script']) > 100 else f"  Script: {pair['input2']['script']}")
            print(f"  R Value: {pair['input2']['r_value']}")
            
            print("\n" + "-"*40)
            print("📊 SUMMARY:")
            print("-"*40)
            print(f"  Same R value used in transaction: {pair['input1']['tx_hash']} and {pair['input2']['tx_hash']}")
            print(f"  This means the same random nonce (R value) was reused in two different transactions")
            print(f"  This is a critical security vulnerability that could lead to private key exposure!")
            print("\n")
        
        print("="*80)
        print("⚠️  SECURITY RECOMMENDATION:")
        print("="*80)
        print("  DO NOT use this wallet anymore!")
        print("  Move all funds to a new, secure wallet immediately.")
        print("  The private key for this address may be compromised.")
        print("="*80)

if __name__ == "__main__":
    main()
