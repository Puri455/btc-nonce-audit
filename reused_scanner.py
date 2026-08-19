import json
import requests
import sys
from tqdm import tqdm

# ANSI color codes for terminal output
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

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


def main():
    print_logo()
    print("WELCOME TO Reused R Scanner 0.5!\n")
    
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
        # Print transaction details with colored hash
        print("\n" + "="*80)
        print(f"{Colors.CYAN}Transaction hash:{Colors.END} {Colors.YELLOW}{tx.get('hash', 'N/A')}{Colors.END}")
        print(f"Number of inputs: {tx.get('vin_sz', 0)}")
        
        for idx, input_script in enumerate(tx.get('inputs', [])):
            script = input_script.get('script', '')
            if script and len(script) >= 74:
                inputs.append(script)
                # Store transaction details for each input
                tx_details.append({
                    'tx_hash': tx.get('hash', 'Unknown'),
                    'input_index': idx,
                    'script': script,
                    'r_value': script[10:74] if len(script) >= 74 else None,
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
                    # Store detailed information about each reused R value
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
        print(f"{Colors.GREEN}✅ No Reused R values Found, seems safe!{Colors.END}")
        print("="*80)
    else:
        print(f"{Colors.RED}⚠️  ALERT: Total reused R values found: {alert_count}{Colors.END}")
        print(f"{Colors.RED}⚠️  WARNING: Wallet is NOT safe!{Colors.END}")
        print("="*80)
        
        # ========== DETAILED OUTPUT SECTION WITH COLORS ==========
        print("\n" + "="*80)
        print(f"{Colors.BOLD}{Colors.RED}📋 FULL DETAILS OF EACH REUSED R VALUE{Colors.END}")
        print("="*80)
        print("\n")
        
        # Display each reused R value pair in detail
        for pair_num, pair in enumerate(reused_pairs, 1):
            print(f"{'='*80}")
            print(f"{Colors.RED}🔴 REUSED R VALUE PAIR #{pair_num} of {len(reused_pairs)}{Colors.END}")
            print(f"{'='*80}")
            
            print(f"\n{Colors.BOLD}🔑 THE REUSED R VALUE:{Colors.END}")
            print(f"   {Colors.YELLOW}{pair['r_value']}{Colors.END}")
            
            print(f"\n{Colors.BOLD}📤 INPUT 1 (Index #{pair['index1']}):{Colors.END}")
            print(f"   Transaction: {Colors.RED}{pair['input1']['tx_hash']}{Colors.END}")
            print(f"   Input Index: {pair['input1']['input_index']}")
            print(f"   R Value: {Colors.YELLOW}{pair['input1']['r_value']}{Colors.END}")
            print(f"   Script: {pair['input1']['script'][:100]}..." if len(pair['input1']['script']) > 100 else f"   Script: {pair['input1']['script']}")
            
            print(f"\n{Colors.BOLD}📥 INPUT 2 (Index #{pair['index2']}):{Colors.END}")
            print(f"   Transaction: {Colors.RED}{pair['input2']['tx_hash']}{Colors.END}")
            print(f"   Input Index: {pair['input2']['input_index']}")
            print(f"   R Value: {Colors.YELLOW}{pair['input2']['r_value']}{Colors.END}")
            print(f"   Script: {pair['input2']['script'][:100]}..." if len(pair['input2']['script']) > 100 else f"   Script: {pair['input2']['script']}")
            
            print(f"\n{Colors.RED}⚠️  SECURITY RISK:{Colors.END}")
            print(f"   The same R value is used in:")
            print(f"   • {Colors.RED}{pair['input1']['tx_hash']}{Colors.END}")
            print(f"   • {Colors.RED}{pair['input2']['tx_hash']}{Colors.END}")
            print(f"   {Colors.RED}This is a CRITICAL vulnerability that can expose the private key!{Colors.END}")
            print(f"   🎯 An attacker can calculate the private key from these two signatures.")
            
            print(f"\n{Colors.BOLD}🔗 Transaction Links:{Colors.END}")
            print(f"   {Colors.CYAN}https://www.blockchain.com/btc/tx/{pair['input1']['tx_hash']}{Colors.END}")
            print(f"   {Colors.CYAN}https://www.blockchain.com/btc/tx/{pair['input2']['tx_hash']}{Colors.END}")
            print("\n")
        
        # Summary of all findings
        print("="*80)
        print(f"{Colors.BOLD}📊 SUMMARY OF FINDINGS:{Colors.END}")
        print("="*80)
        print(f"   Total Reused R Values Found: {Colors.RED}{alert_count}{Colors.END}")
        print(f"   Total Inputs Analyzed: {len(inputs)}")
        print(f"   Total Comparisons Made: {total_comparisons}")
        print(f"\n   {Colors.BOLD}Affected Transactions:{Colors.END}")
        for pair in reused_pairs:
            print(f"   {Colors.RED}• {pair['input1']['tx_hash']}{Colors.END}")
            print(f"   {Colors.RED}• {pair['input2']['tx_hash']}{Colors.END}")
        
        # Security Recommendations
        print("\n" + "="*80)
        print(f"{Colors.BOLD}{Colors.RED}🚨 URGENT SECURITY RECOMMENDATIONS:{Colors.END}")
        print("="*80)
        print(f"   {Colors.RED}1. ❌ IMMEDIATELY STOP using this wallet!{Colors.END}")
        print(f"   {Colors.RED}2. 🏃 Move ALL funds to a new, secure wallet NOW!{Colors.END}")
        print(f"   {Colors.YELLOW}3. 🔒 Generate a new wallet with a strong random seed{Colors.END}")
        print(f"   {Colors.YELLOW}4. 🗑️  Never reuse this address or its private key again{Colors.END}")
        print(f"   {Colors.RED}5. ⚡ The private key may already be compromised{Colors.END}")
        print("="*80)

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
