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
#            V0.6             #
#                             #
###############################
    """
    print(logo)

def der_decode_length(data: bytes, pos: int) -> Tuple[int, int]:
    """Decode DER length field"""
    if pos >= len(data):
        return 0, pos
    
    if data[pos] < 0x80:
        return data[pos], pos + 1
    
    length_len = data[pos] & 0x7f
    if length_len > 4:  # Too long for our purposes
        return 0, pos + 1 + length_len
    
    length = 0
    for i in range(length_len):
        if pos + 1 + i >= len(data):
            return 0, pos + 1 + length_len
        length = (length << 8) + data[pos + 1 + i]
    
    return length, pos + 1 + length_len

def extract_r_value_from_script(script: str) -> Optional[str]:
    """Extract R value from script signature using proper DER parsing"""
    if not script:
        return None
    
    try:
        # Convert hex string to bytes
        if isinstance(script, str):
            if len(script) % 2 != 0:
                return None
            script_bytes = bytes.fromhex(script)
        else:
            script_bytes = script
        
        # Find DER sequence marker (0x30)
        for i in range(len(script_bytes) - 2):
            if script_bytes[i] == 0x30:  # DER sequence
                # Try to parse DER at this position
                try:
                    # Parse the sequence
                    _, pos = der_decode_length(script_bytes, i + 1)
                    if pos >= len(script_bytes):
                        continue
                    
                    # Look for integer marker (0x02) - this should be R
                    # Skip potential version or other fields
                    temp_pos = pos
                    while temp_pos < len(script_bytes) - 2:
                        if script_bytes[temp_pos] == 0x02:
                            r_len, r_pos = der_decode_length(script_bytes, temp_pos + 1)
                            if r_pos + r_len <= len(script_bytes):
                                r_value = script_bytes[r_pos:r_pos + r_len]
                                
                                # Remove leading zero if present (for positive numbers)
                                if len(r_value) > 32 and r_value[0] == 0x00:
                                    r_value = r_value[1:]
                                
                                # R value should be 32 bytes or less
                                if 0 < len(r_value) <= 32:
                                    return r_value.hex()
                        temp_pos += 1
                        
                except Exception:
                    continue
                    
    except Exception:
        return None
    
    return None

def parse_der_signature(script: str) -> Optional[Dict[str, str]]:
    """Parse DER signature to extract R and S values"""
    if not script:
        return None
    
    try:
        if isinstance(script, str):
            if len(script) % 2 != 0:
                return None
            script_bytes = bytes.fromhex(script)
        else:
            script_bytes = script
        
        # Find DER sequence
        for i in range(len(script_bytes) - 4):
            if script_bytes[i] == 0x30:
                try:
                    _, pos = der_decode_length(script_bytes, i + 1)
                    if pos >= len(script_bytes):
                        continue
                    
                    # Parse R value
                    r_value = None
                    s_value = None
                    current_pos = pos
                    
                    # Look for R (first integer)
                    while current_pos < len(script_bytes) - 2:
                        if script_bytes[current_pos] == 0x02:
                            r_len, r_pos = der_decode_length(script_bytes, current_pos + 1)
                            if r_pos + r_len <= len(script_bytes):
                                r_bytes = script_bytes[r_pos:r_pos + r_len]
                                if len(r_bytes) > 32 and r_bytes[0] == 0x00:
                                    r_bytes = r_bytes[1:]
                                if 0 < len(r_bytes) <= 32:
                                    r_value = r_bytes.hex()
                                    current_pos = r_pos + r_len
                                    break
                        current_pos += 1
                    
                    # Look for S value (second integer)
                    while current_pos < len(script_bytes) - 2:
                        if script_bytes[current_pos] == 0x02:
                            s_len, s_pos = der_decode_length(script_bytes, current_pos + 1)
                            if s_pos + s_len <= len(script_bytes):
                                s_bytes = script_bytes[s_pos:s_pos + s_len]
                                if len(s_bytes) > 32 and s_bytes[0] == 0x00:
                                    s_bytes = s_bytes[1:]
                                if 0 < len(s_bytes) <= 32:
                                    s_value = s_bytes.hex()
                                    break
                        current_pos += 1
                    
                    if r_value and s_value:
                        return {'r': r_value, 's': s_value}
                        
                except Exception:
                    continue
                    
    except Exception:
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

def analyze_transactions(address: str, address_data: Dict[str, Any]) -> Tuple[List[str], List[Dict]]:
    """Analyze transactions and extract R values with proper parsing"""
    inputs = []
    tx_details = []
    found_r_values = set()
    
    print("\n" + "═"*80)
    print("📊 ANALYZING TRANSACTIONS")
    print("═"*80)
    
    # Get transactions
    txs = address_data.get('txs', [])
    num_txs = len(txs)
    
    if num_txs == 0:
        print("❌ No transactions found for this address")
        return inputs, tx_details
    
    print(f"📊 Processing {num_txs} transactions...")
    
    for tx_idx, tx in enumerate(tqdm(txs, desc="Processing transactions", unit="tx")):
        tx_hash = tx.get('hash', 'Unknown')
        vin_sz = tx.get('vin_sz', 0)
        
        # Process each input
        for idx, input_script in enumerate(tx.get('inputs', [])):
            script = input_script.get('script', '')
            
            # Parse DER signature
            der_parts = parse_der_signature(script)
            if der_parts and der_parts.get('r'):
                r_value = der_parts['r']
                
                # Store input data
                inputs.append(script)
                tx_details.append({
                    'tx_hash': tx_hash,
                    'tx_index': tx_idx,
                    'input_index': idx,
                    'script': script,
                    'r_value': r_value,
                    's_value': der_parts.get('s', ''),
                    'prev_out': input_script.get('prev_out', {}),
                    'address': address  # Store wallet address
                })
                
                if r_value not in found_r_values:
                    found_r_values.add(r_value)
                    # Show first 10 R values found
                    if len(found_r_values) <= 10:
                        print(f"  🔑 Found R value: {r_value[:20]}... (TX: {tx_hash[:20]}...)")
    
    print(f"\n✅ Found {len(found_r_values)} unique R values across {len(inputs)} inputs")
    return inputs, tx_details

def find_reused_r_values(inputs: List[str], tx_details: List[Dict]) -> List[Dict]:
    """Find reused R values and return detailed information"""
    # Group by R value
    r_value_groups = defaultdict(list)
    
    for i, detail in enumerate(tx_details):
        r_val = detail.get('r_value')
        if r_val:
            r_value_groups[r_val].append({
                'index': i,
                'tx_detail': detail
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
                        'input2': items[j]['tx_detail'],
                        'total_uses': len(items)
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
    
    # Group by R value to show which R values are reused
    r_value_summary = defaultdict(list)
    for pair in reused_pairs:
        r_value_summary[pair['r_value']].append(pair)
    
    print("\n" + "═"*80)
    print("📊 SUMMARY OF REUSED R VALUES")
    print("═"*80)
    for r_val, pairs in r_value_summary.items():
        total_uses = pairs[0]['total_uses']
        affected_txs = set()
        for p in pairs:
            affected_txs.add(p['input1']['tx_hash'])
            affected_txs.add(p['input2']['tx_hash'])
        print(f"\n  🔑 R Value: {r_val}")
        print(f"     • Used {total_uses} times across {len(affected_txs)} transactions")
        print(f"     • {len(pairs)} vulnerable pairs found")
    
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
        print(f"📊 Used {pair['total_uses']} times total")
        print("─"*40)
        
        # Input 1
        print("\n📍 INPUT 1:")
        print("─"*40)
        print(f"  🏷️  Transaction Hash: {pair['input1']['tx_hash']}")
        print(f"  🔢 Input Index: {pair['input1']['input_index']}")
        print(f"  💰 Wallet: {address}")
        r_val1 = pair['input1']['r_value']
        print(f"  🔑 R Value: {r_val1}")
        if pair['input1'].get('s_value'):
            print(f"  🔐 S Value: {pair['input1']['s_value'][:20]}...")
        
        # Input 2
        print("\n📍 INPUT 2:")
        print("─"*40)
        print(f"  🏷️  Transaction Hash: {pair['input2']['tx_hash']}")
        print(f"  🔢 Input Index: {pair['input2']['input_index']}")
        print(f"  💰 Wallet: {address}")
        r_val2 = pair['input2']['r_value']
        print(f"  🔑 R Value: {r_val2}")
        if pair['input2'].get('s_value'):
            print(f"  🔐 S Value: {pair['input2']['s_value'][:20]}...")
        
        # Vulnerability explanation
        print("\n" + "─"*40)
        print("⚠️  VULNERABILITY DETAILS:")
        print("─"*40)
        print(f"  🔴 Same R value used in multiple transactions from wallet: {address}")
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
    print(f"  • Vulnerable Wallet: {address}")
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
    print(f"  ❌ Wallet {address} is COMPROMISED!")
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
    print("WELCOME TO Reused R Scanner 0.6!\n")
    
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
    inputs, tx_details = analyze_transactions(address, address_data)
    
    if not inputs:
        print("\n❌ No valid input scripts with R values found!")
        sys.exit(0)
    
    print(f"\n📊 Total inputs with R-values extracted: {len(inputs)}")
    print("\n🔍 Comparing input scripts for reused R values...\n")
    
    # Find reused R values
    reused_pairs = find_reused_r_values(inputs, tx_details)
    
    # Display results
    display_results(reused_pairs, address, num_txs, len(inputs))

if __name__ == "__main__":
    main()
    sys.exit()
