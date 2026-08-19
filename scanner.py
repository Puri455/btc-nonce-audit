#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import requests
import sys
import time
import hashlib
from tqdm import tqdm
from collections import defaultdict
from typing import Optional, List, Dict, Any, Tuple

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
#            V0.9             #
#                             #
###############################
    """
    print(logo)

def extract_r_s_from_script(script_hex: str) -> Optional[Dict[str, str]]:
    """
    Extract R and S values from Bitcoin script signature
    Handles the specific DER format used in Bitcoin transactions
    """
    if not script_hex or len(script_hex) < 20:
        return None
    
    try:
        # Clean the hex string
        script_hex = script_hex.strip()
        if len(script_hex) % 2 != 0:
            return None
            
        script_bytes = bytes.fromhex(script_hex)
        
        # Look for DER signature pattern
        if len(script_bytes) < 6:
            return None
        
        r_value = None
        s_value = None
        
        # Find R value (look for 0x02 marker)
        i = 0
        while i < len(script_bytes) - 2:
            if script_bytes[i] == 0x02:  # Integer marker
                if i + 1 < len(script_bytes):
                    r_len = script_bytes[i + 1]
                    r_start = i + 2
                    r_end = r_start + r_len
                    
                    if r_end <= len(script_bytes):
                        r_bytes = script_bytes[r_start:r_end]
                        # Remove leading zero if present (for positive numbers)
                        if len(r_bytes) > 32 and r_bytes[0] == 0x00:
                            r_bytes = r_bytes[1:]
                        if 0 < len(r_bytes) <= 33:
                            if not r_value:
                                r_value = r_bytes.hex()
                                i = r_end
                                continue
                            else:
                                # This is the S value
                                s_bytes = r_bytes
                                if len(s_bytes) > 32 and s_bytes[0] == 0x00:
                                    s_bytes = s_bytes[1:]
                                if 0 < len(s_bytes) <= 33:
                                    s_value = s_bytes.hex()
                                    break
            i += 1
        
        if r_value and s_value:
            return {'r': r_value, 's': s_value}
            
    except Exception:
        pass
    
    return None

def get_address_data(address: str, max_retries: int = 3) -> Dict[str, Any]:
    """Fetch address data from blockchain.info with retry logic"""
    url = f"https://blockchain.info/rawaddr/{address}"
    
    for attempt in range(max_retries):
        try:
            print(f"  Attempt {attempt + 1}/{max_retries}...")
            response = requests.get(url, timeout=30)
            
            if response.status_code == 429:  # Rate limited
                wait_time = 2 ** attempt
                print(f"⏳ Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
                
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                print(f"❌ Error fetching data: {e}")
                sys.exit(1)
            print(f"⚠️ Attempt {attempt + 1} failed, retrying...")
            time.sleep(2)
    
    return {}

def analyze_transactions(address: str, address_data: Dict[str, Any]) -> Tuple[List[Dict], Dict[str, int]]:
    """Analyze transactions and extract R values"""
    tx_details = []
    r_value_counter = defaultdict(int)
    
    print("\n" + "═"*80)
    print("📊 ANALYZING TRANSACTIONS")
    print("═"*80)
    
    txs = address_data.get('txs', [])
    num_txs = len(txs)
    
    if num_txs == 0:
        print("❌ No transactions found for this address")
        return [], {}
    
    print(f"📊 Processing {num_txs} transactions from wallet: {address}\n")
    
    for tx_idx, tx in enumerate(tqdm(txs, desc="Processing", unit="tx")):
        tx_hash = tx.get('hash', 'Unknown')
        vin_sz = tx.get('vin_sz', 0)
        time_val = tx.get('time', 0)
        
        # Show transaction header
        print(f"\n{'#'*80}")
        print(f"📝 TX: {tx_hash}")
        print(f"📊 Inputs: {vin_sz}")
        if time_val:
            print(f"🕐 Time: {time.ctime(time_val)}")
        print(f"{'#'*80}")
        
        # Process each input
        for idx, input_script in enumerate(tx.get('inputs', [])):
            script = input_script.get('script', '')
            
            # Skip if script is too short
            if len(script) < 20:
                continue
                
            # Extract R and S values
            der_parts = extract_r_s_from_script(script)
            
            if der_parts:
                r_value = der_parts['r']
                s_value = der_parts['s']
                
                print(f"  ✅ Input #{idx}:")
                print(f"     🔑 R: {r_value[:20]}... (full: {r_value})")
                print(f"     🔐 S: {s_value[:20]}... (full: {s_value})")
                
                # Get previous output info
                prev_out = input_script.get('prev_out', {})
                prev_addr = prev_out.get('addr', 'Unknown')
                prev_value = prev_out.get('value', 0)
                
                # Store transaction detail
                tx_detail = {
                    'tx_hash': tx_hash,
                    'tx_index': tx_idx,
                    'input_index': idx,
                    'script': script,
                    'r_value': r_value,
                    's_value': s_value,
                    'prev_out': prev_out,
                    'address': address,
                    'vin_sz': vin_sz,
                    'time': time_val,
                    'prev_addr': prev_addr,
                    'prev_value': prev_value
                }
                
                tx_details.append(tx_detail)
                r_value_counter[r_value] += 1
    
    # Show statistics
    print(f"\n{'='*80}")
    print("📊 ANALYSIS COMPLETE")
    print(f"{'='*80}")
    print(f"  ✅ Total inputs with R values: {len(tx_details)}")
    print(f"  🔑 Unique R values found: {len(r_value_counter)}")
    
    repeated = {k: v for k, v in r_value_counter.items() if v > 1}
    if repeated:
        print(f"  ⚠️ R values used multiple times: {len(repeated)}")
        for r_val, count in repeated.items():
            print(f"     → {r_val} used {count} times")
    else:
        print("  ✅ All R values appear to be unique")
    
    return tx_details, r_value_counter

def find_reused_r_values(tx_details: List[Dict]) -> List[Dict]:
    """Find reused R values"""
    r_value_groups = defaultdict(list)
    
    for detail in tx_details:
        r_val = detail.get('r_value')
        if r_val:
            r_value_groups[r_val].append(detail)
    
    reused_pairs = []
    for r_val, items in r_value_groups.items():
        if len(items) > 1:
            for i in range(len(items)):
                for j in range(i + 1, len(items)):
                    reused_pairs.append({
                        'r_value': r_val,
                        'input1': items[i],
                        'input2': items[j],
                        'total_uses': len(items),
                        'all_inputs': items
                    })
    
    return reused_pairs

def display_results(reused_pairs: List[Dict], address: str, num_txs: int, total_inputs: int):
    """Display detailed results"""
    if not reused_pairs:
        print("\n" + "="*80)
        print("✅ No Reused R values Found - Wallet appears safe!")
        print("="*80)
        return
    
    print("\n" + "="*80)
    print(f"⚠️  ALERT: {len(reused_pairs)} reused R value pairs found!")
    print("⚠️  WARNING: Wallet is NOT safe!")
    print("="*80)
    
    # Show wallet address
    print("\n" + "═"*80)
    print("🔴 VULNERABLE WALLET ADDRESS")
    print("═"*80)
    print(f"  💰 {address}")
    print("═"*80)
    
    # Group by R value
    r_value_summary = defaultdict(list)
    all_affected_txs = set()
    
    for pair in reused_pairs:
        r_value_summary[pair['r_value']].append(pair)
        all_affected_txs.add(pair['input1']['tx_hash'])
        all_affected_txs.add(pair['input2']['tx_hash'])
    
    # Summary
    print("\n" + "═"*80)
    print("📊 REUSED R VALUES SUMMARY")
    print("═"*80)
    for r_val, pairs in r_value_summary.items():
        total_uses = pairs[0]['total_uses']
        affected_txs = set()
        for p in pairs:
            affected_txs.add(p['input1']['tx_hash'])
            affected_txs.add(p['input2']['tx_hash'])
        print(f"\n  🔑 R: {r_val}")
        print(f"     • Used {total_uses} times in {len(affected_txs)} transactions")
        print(f"     • Creates {len(pairs)} vulnerable signature pairs")
    
    # Detailed pair information
    print("\n" + "═"*80)
    print("🔍 DETAILED REUSED R VALUE INFORMATION")
    print("═"*80)
    
    for pair_num, pair in enumerate(reused_pairs, 1):
        print(f"\n{'='*80}")
        print(f"🔴 REUSED R VALUE PAIR #{pair_num}")
        print(f"{'='*80}")
        
        print(f"\n🔑 REUSED R:")
        print(f"   {pair['r_value']}")
        print(f"   Used {pair['total_uses']} times total")
        print("─"*40)
        
        print("\n📍 INPUT 1:")
        print("─"*40)
        print(f"  💰 Wallet: {address}")
        print(f"  🏷️  TX: {pair['input1']['tx_hash']}")
        print(f"  🔢 Input: {pair['input1']['input_index']}")
        print(f"  🔑 R: {pair['input1']['r_value']}")
        print(f"  🔐 S: {pair['input1']['s_value']}")
        if pair['input1']['prev_addr'] != 'Unknown':
            print(f"  📤 From: {pair['input1']['prev_addr']}")
            print(f"  💰 Amount: {pair['input1']['prev_value'] / 100000000:.8f} BTC")
        
        print("\n📍 INPUT 2:")
        print("─"*40)
        print(f"  💰 Wallet: {address}")
        print(f"  🏷️  TX: {pair['input2']['tx_hash']}")
        print(f"  🔢 Input: {pair['input2']['input_index']}")
        print(f"  🔑 R: {pair['input2']['r_value']}")
        print(f"  🔐 S: {pair['input2']['s_value']}")
        if pair['input2']['prev_addr'] != 'Unknown':
            print(f"  📤 From: {pair['input2']['prev_addr']}")
            print(f"  💰 Amount: {pair['input2']['prev_value'] / 100000000:.8f} BTC")
        
        if pair['total_uses'] > 2:
            print("\n📋 ALL OCCURRENCES:")
            print("─"*40)
            for idx, inp in enumerate(pair['all_inputs'], 1):
                print(f"  {idx}. TX: {inp['tx_hash'][:40]}... | Input: {inp['input_index']}")
        
        print("\n" + "─"*40)
        print("⚠️  VULNERABILITY:")
        print("─"*40)
        print("  🔴 Same R value used in multiple signatures")
        print("  🔴 Private key can be calculated from these signatures!")
        print("  🔴 All funds in this wallet are at risk!")
        print("\n" + "▬"*40)
    
    # Summary
    print("\n" + "═"*80)
    print("📊 COMPREHENSIVE SUMMARY")
    print("═"*80)
    print(f"  🔴 Vulnerable Wallet: {address}")
    print(f"  📊 Total transactions: {num_txs}")
    print(f"  📊 Total inputs: {total_inputs}")
    print(f"  ⚠️  Reused pairs: {len(reused_pairs)}")
    
    unique_r_values = set()
    for pair in reused_pairs:
        unique_r_values.add(pair['r_value'])
    print(f"  🔑 Unique R values: {len(unique_r_values)}")
    
    affected_txs = set()
    for pair in reused_pairs:
        affected_txs.add(pair['input1']['tx_hash'])
        affected_txs.add(pair['input2']['tx_hash'])
    print(f"  📋 Affected transactions: {len(affected_txs)}")
    
    print("\n📋 AFFECTED TRANSACTIONS:")
    for idx, tx_hash in enumerate(sorted(affected_txs), 1):
        print(f"  {idx}. {tx_hash}")
    
    print("\n" + "═"*80)
    print("🚨 CRITICAL SECURITY RECOMMENDATIONS")
    print("═"*80)
    print(f"  ❌ Wallet {address} is COMPROMISED!")
    print("  🔴 Move all funds to a new, secure wallet IMMEDIATELY.")
    print("  🔴 The private key for this address IS COMPROMISED.")
    print("="*80)

def main():
    print_logo()
    print("WELCOME TO Reused R Scanner 0.9!\n")
    
    address = input("Enter the Bitcoin address to scan: ").strip()
    if not address:
        print("❌ Invalid address. Please try again.")
        sys.exit(1)
    
    print(f"\n📡 Fetching data for address: {address}")
    print("⏳ This may take a moment...")
    
    try:
        address_data = get_address_data(address)
        num_txs = address_data.get('n_tx', 0)
        
        if num_txs == 0:
            print(f"❌ No transactions found for address: {address}")
            sys.exit(1)
        
        print(f"\n📊 Address: {address}")
        print(f"📊 Total Transactions: {num_txs}")
        print("═"*80)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    
    tx_details, r_value_counter = analyze_transactions(address, address_data)
    
    if not tx_details:
        print("\n❌ No valid input scripts with R values found!")
        sys.exit(0)
    
    print(f"\n📊 Total inputs with R-values: {len(tx_details)}")
    print("\n🔍 Finding reused R values...\n")
    
    reused_pairs = find_reused_r_values(tx_details)
    display_results(reused_pairs, address, num_txs, len(tx_details))

if __name__ == "__main__":
    main()
    sys.exit()
