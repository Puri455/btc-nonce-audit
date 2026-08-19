#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import requests
import sys
import time
import hashlib
import re
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
#            V0.8             #
#                             #
###############################
    """
    print(logo)

def extract_r_from_der(script_hex: str) -> Optional[Dict[str, str]]:
    """
    Extract R and S values from Bitcoin script signature (DER format)
    This handles the specific format used in Bitcoin transactions
    """
    if not script_hex or len(script_hex) < 20:
        return None
    
    try:
        # Clean the hex string
        script_hex = script_hex.strip()
        if len(script_hex) % 2 != 0:
            return None
            
        script_bytes = bytes.fromhex(script_hex)
        
        # Look for DER signature pattern: 0x30 (sequence) followed by length
        # Bitcoin signatures are typically 70-73 bytes
        if len(script_bytes) < 8:
            return None
            
        # Find the DER sequence start
        der_start = -1
        for i in range(len(script_bytes) - 2):
            if script_bytes[i] == 0x30:  # DER Sequence marker
                # Check if this is a valid signature (typical length 70-73)
                if i + 1 < len(script_bytes):
                    der_len = script_bytes[i + 1]
                    if 0x44 <= der_len <= 0x49:  # 68-73 bytes
                        der_start = i
                        break
        
        if der_start == -1:
            # Try without length check
            for i in range(len(script_bytes) - 2):
                if script_bytes[i] == 0x30:
                    der_start = i
                    break
        
        if der_start == -1:
            return None
            
        # Parse the DER sequence
        pos = der_start + 2  # Skip 0x30 and length
        if pos >= len(script_bytes):
            return None
            
        r_value = None
        s_value = None
        
        # Find R value (first integer marker 0x02)
        for i in range(pos, len(script_bytes) - 2):
            if script_bytes[i] == 0x02:  # Integer marker
                if i + 1 < len(script_bytes):
                    r_len = script_bytes[i + 1]
                    r_start = i + 2
                    r_end = r_start + r_len
                    
                    if r_end <= len(script_bytes):
                        r_bytes = script_bytes[r_start:r_end]
                        # Remove leading zero if present
                        if len(r_bytes) > 32 and r_bytes[0] == 0x00:
                            r_bytes = r_bytes[1:]
                        if 0 < len(r_bytes) <= 33:
                            r_value = r_bytes.hex()
                            pos = r_end
                            break
        
        if not r_value:
            return None
            
        # Find S value (second integer marker 0x02)
        for i in range(pos, len(script_bytes) - 2):
            if script_bytes[i] == 0x02:  # Integer marker
                if i + 1 < len(script_bytes):
                    s_len = script_bytes[i + 1]
                    s_start = i + 2
                    s_end = s_start + s_len
                    
                    if s_end <= len(script_bytes):
                        s_bytes = script_bytes[s_start:s_end]
                        # Remove leading zero if present
                        if len(s_bytes) > 32 and s_bytes[0] == 0x00:
                            s_bytes = s_bytes[1:]
                        if 0 < len(s_bytes) <= 33:
                            s_value = s_bytes.hex()
                            break
        
        if r_value and s_value:
            return {'r': r_value, 's': s_value}
            
    except Exception as e:
        # Silently fail for individual scripts
        pass
    
    return None

def get_address_data(address: str, max_retries: int = 3) -> Dict[str, Any]:
    """Fetch address data from blockchain.info with retry logic"""
    url = f"https://blockchain.info/rawaddr/{address}"
    
    for attempt in range(max_retries):
        try:
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
            time.sleep(1)
    
    return {}

def analyze_transactions(address: str, address_data: Dict[str, Any]) -> Tuple[List[Dict], Dict[str, int]]:
    """Analyze transactions and extract R values with proper parsing"""
    tx_details = []
    r_value_counter = defaultdict(int)
    r_value_txs = defaultdict(list)
    
    print("\n" + "═"*80)
    print("📊 ANALYZING TRANSACTIONS")
    print("═"*80)
    
    # Get transactions
    txs = address_data.get('txs', [])
    num_txs = len(txs)
    
    if num_txs == 0:
        print("❌ No transactions found for this address")
        return [], {}
    
    print(f"📊 Processing {num_txs} transactions from wallet: {address}")
    print("═"*40)
    
    for tx_idx, tx in enumerate(tqdm(txs, desc="Processing transactions", unit="tx")):
        tx_hash = tx.get('hash', 'Unknown')
        vin_sz = tx.get('vin_sz', 0)
        time_val = tx.get('time', 0)
        
        # Show transaction header
        print(f"\n{'#'*80}")
        print(f"Transaction hash: {tx_hash}")
        print(f"Number of inputs: {vin_sz}")
        if time_val:
            print(f"Time: {time.ctime(time_val)}")
        print(f"{'#'*80}")
        
        # Process each input
        for idx, input_script in enumerate(tx.get('inputs', [])):
            script = input_script.get('script', '')
            
            # Skip if script is too short
            if len(script) < 20:
                continue
                
            # Parse DER signature
            der_parts = extract_r_from_der(script)
            
            if der_parts:
                r_value = der_parts['r']
                s_value = der_parts['s']
                
                # Show found R value
                print(f"  ✅ Input #{idx}: R-value found: {r_value[:20]}...")
                print(f"     S-value: {s_value[:20]}...")
                
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
                r_value_txs[r_value].append(tx_detail)
    
    # Show statistics
    print(f"\n{'='*80}")
    print(f"📊 ANALYSIS COMPLETE")
    print(f"{'='*80}")
    print(f"  ✅ Total inputs analyzed: {len(tx_details)}")
    print(f"  🔑 Unique R values found: {len(r_value_counter)}")
    
    # Find repeated R values
    repeated = {k: v for k, v in r_value_counter.items() if v > 1}
    if repeated:
        print(f"  ⚠️ R values used multiple times: {len(repeated)}")
        for r_val, count in repeated.items():
            print(f"     → {r_val[:20]}... used {count} times")
    else:
        print("  ✅ All R values appear to be unique")
    
    return tx_details, r_value_counter

def find_reused_r_values(tx_details: List[Dict]) -> List[Dict]:
    """Find reused R values and return detailed information"""
    # Group by R value
    r_value_groups = defaultdict(list)
    
    for detail in tx_details:
        r_val = detail.get('r_value')
        if r_val:
            r_value_groups[r_val].append(detail)
    
    # Find reused R values (groups with more than 1)
    reused_pairs = []
    for r_val, items in r_value_groups.items():
        if len(items) > 1:
            # Create all pairs from this group
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
    
    # Show wallet address prominently
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
    
    # Summary of reused R values
    print("\n" + "═"*80)
    print("📊 REUSED R VALUES SUMMARY")
    print("═"*80)
    for r_val, pairs in r_value_summary.items():
        total_uses = pairs[0]['total_uses']
        affected_txs = set()
        for p in pairs:
            affected_txs.add(p['input1']['tx_hash'])
            affected_txs.add(p['input2']['tx_hash'])
        print(f"\n  🔑 R VALUE: {r_val}")
        print(f"     • Used {total_uses} times in {len(affected_txs)} transactions")
        print(f"     • Creates {len(pairs)} vulnerable signature pairs")
        print(f"     • First seen in TX: {pairs[0]['input1']['tx_hash'][:40]}...")
    
    # Detailed pair information
    print("\n" + "═"*80)
    print("🔍 DETAILED REUSED R VALUE INFORMATION")
    print("═"*80)
    
    for pair_num, pair in enumerate(reused_pairs, 1):
        print(f"\n{'='*80}")
        print(f"🔴 REUSED R VALUE PAIR #{pair_num}")
        print(f"{'='*80}")
        
        # R Value
        print(f"\n🔑 REUSED R VALUE:")
        print(f"   {pair['r_value']}")
        print(f"   Used {pair['total_uses']} times total")
        print("─"*40)
        
        # Input 1
        print("\n📍 INPUT 1:")
        print("─"*40)
        print(f"  💰 Wallet Address: {address}")
        print(f"  🏷️  Transaction Hash: {pair['input1']['tx_hash']}")
        print(f"  🔢 Input Index: {pair['input1']['input_index']}")
        print(f"  📊 Total Inputs in TX: {pair['input1']['vin_sz']}")
        print(f"  🔑 R Value: {pair['input1']['r_value']}")
        print(f"  🔐 S Value: {pair['input1']['s_value']}")
        if pair['input1']['prev_addr'] != 'Unknown':
            print(f"  📤 From Address: {pair['input1']['prev_addr']}")
            print(f"  💰 Amount: {pair['input1']['prev_value'] / 100000000:.8f} BTC")
        if pair['input1']['time']:
            print(f"  🕐 Time: {time.ctime(pair['input1']['time'])}")
        
        # Input 2
        print("\n📍 INPUT 2:")
        print("─"*40)
        print(f"  💰 Wallet Address: {address}")
        print(f"  🏷️  Transaction Hash: {pair['input2']['tx_hash']}")
        print(f"  🔢 Input Index: {pair['input2']['input_index']}")
        print(f"  📊 Total Inputs in TX: {pair['input2']['vin_sz']}")
        print(f"  🔑 R Value: {pair['input2']['r_value']}")
        print(f"  🔐 S Value: {pair['input2']['s_value']}")
        if pair['input2']['prev_addr'] != 'Unknown':
            print(f"  📤 From Address: {pair['input2']['prev_addr']}")
            print(f"  💰 Amount: {pair['input2']['prev_value'] / 100000000:.8f} BTC")
        if pair['input2']['time']:
            print(f"  🕐 Time: {time.ctime(pair['input2']['time'])}")
        
        # Show all occurrences of this R value
        if pair['total_uses'] > 2:
            print("\n📋 ALL OCCURRENCES OF THIS R VALUE:")
            print("─"*40)
            all_inputs = pair['all_inputs']
            for idx, inp in enumerate(all_inputs, 1):
                print(f"  {idx}. TX: {inp['tx_hash'][:40]}... | Input: {inp['input_index']} | R: {inp['r_value'][:20]}...")
        
        # Vulnerability explanation
        print("\n" + "─"*40)
        print("⚠️  VULNERABILITY DETAILS:")
        print("─"*40)
        print(f"  🔴 Same R value used in multiple signatures")
        print(f"  🔴 Transaction 1: {pair['input1']['tx_hash'][:40]}...")
        print(f"  🔴 Transaction 2: {pair['input2']['tx_hash'][:40]}...")
        print(f"  🔴 Both signatures from wallet: {address}")
        print("  ⚠️  The same random nonce (R) was reused")
        print("  ⚠️  This is a CRITICAL security vulnerability!")
        print("  ⚠️  Private key can be calculated from these two signatures!")
        print("  ⚠️  All funds in this wallet are at risk!")
        
        print("\n" + "▬"*40)
    
    # Summary Statistics
    print("\n" + "═"*80)
    print("📊 COMPREHENSIVE SUMMARY")
    print("═"*80)
    print(f"  🔴 Vulnerable Wallet: {address}")
    print(f"  📊 Total transactions analyzed: {num_txs}")
    print(f"  📊 Total inputs extracted: {total_inputs}")
    print(f"  ⚠️  Reused R value pairs found: {len(reused_pairs)}")
    
    # Count unique R values
    unique_r_values = set()
    for pair in reused_pairs:
        unique_r_values.add(pair['r_value'])
    print(f"  🔑 Unique R values reused: {len(unique_r_values)}")
    
    # List affected transactions
    affected_txs = set()
    for pair in reused_pairs:
        affected_txs.add(pair['input1']['tx_hash'])
        affected_txs.add(pair['input2']['tx_hash'])
    print(f"  📋 Affected transactions: {len(affected_txs)}")
    
    # Show all affected transactions with details
    print("\n" + "═"*80)
    print("📋 ALL AFFECTED TRANSACTIONS")
    print("═"*80)
    for idx, tx_hash in enumerate(sorted(affected_txs), 1):
        # Find details for this transaction
        tx_details = []
        for pair in reused_pairs:
            if pair['input1']['tx_hash'] == tx_hash:
                tx_details.append(pair['input1'])
            if pair['input2']['tx_hash'] == tx_hash:
                tx_details.append(pair['input2'])
        if tx_details:
            detail = tx_details[0]
            print(f"  {idx}. {tx_hash}")
            print(f"      Inputs: {detail['vin_sz']} | Time: {time.ctime(detail['time']) if detail['time'] else 'Unknown'}")
            print(f"      R values used: {', '.join(set([d['r_value'][:20] + '...' for d in tx_details]))}")
    print("═"*80)
    
    print("\n" + "═"*80)
    print("🚨 CRITICAL SECURITY RECOMMENDATIONS")
    print("═"*80)
    print(f"  ❌ Wallet {address} is COMPROMISED!")
    print("  ❌ DO NOT use this wallet anymore!")
    print("  🔴 Move all funds to a new, secure wallet IMMEDIATELY.")
    print("  🔴 The private key for this address IS COMPROMISED.")
    print("  🔴 Any funds in this wallet are at risk of being stolen.")
    print("  🔴 This is a well-known vulnerability (Nonce Reuse)")
    print("  🔴 Attackers can calculate your private key using these signatures")
    print("="*80)

def main():
    print_logo()
    print("WELCOME TO Reused R Scanner 0.8!\n")
    
    address = input("Enter the Bitcoin address to scan: ").strip()
    if not address:
        print("❌ Invalid address. Please try again.")
        sys.exit(1)
    
    print(f"\n📡 Fetching data for address: {address}")
    print("⏳ Please wait, this may take a moment...")
    
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
        print(f"❌ Error processing address data: {e}")
        sys.exit(1)
    
    # Analyze transactions
    tx_details, r_value_counter = analyze_transactions(address, address_data)
    
    if not tx_details:
        print("\n❌ No valid input scripts with R values found!")
        sys.exit(0)
    
    print(f"\n📊 Total inputs with R-values extracted: {len(tx_details)}")
    print("\n🔍 Finding reused R values...\n")
    
    # Find reused R values
    reused_pairs = find_reused_r_values(tx_details)
    
    # Display results
    display_results(reused_pairs, address, num_txs, len(tx_details))

if __name__ == "__main__":
    main()
    sys.exit()
