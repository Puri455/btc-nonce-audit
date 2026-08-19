#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import requests
import sys
import time
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
#      (full-history fix)     #
###############################
    """
    print(logo)


def extract_r_s_from_der(script_hex: str) -> Optional[Dict[str, str]]:
    """
    Extract R and S values from a Bitcoin scriptSig's DER-encoded ECDSA signature.
    Walks the ASN.1 structure explicitly instead of scanning for byte markers,
    which avoids false matches on multisig / redeem scripts that contain
    several 0x30 / 0x02 bytes that are NOT part of the signature.
    """
    if not script_hex or len(script_hex) < 20:
        return None

    script_hex = script_hex.strip()
    if len(script_hex) % 2 != 0:
        return None

    try:
        script_bytes = bytes.fromhex(script_hex)
    except ValueError:
        return None

    n = len(script_bytes)
    i = 0
    while i < n - 1:
        if script_bytes[i] == 0x30:
            seq_len = script_bytes[i + 1]
            seq_start = i + 2
            seq_end = seq_start + seq_len

            # Must fit inside the script and look like a plausible DER sig
            if seq_end <= n and 8 <= seq_len <= 0x49:
                pos = seq_start
                try:
                    if script_bytes[pos] != 0x02:
                        i += 1
                        continue
                    r_len = script_bytes[pos + 1]
                    r_start = pos + 2
                    r_end = r_start + r_len
                    if r_end > seq_end:
                        i += 1
                        continue
                    r_bytes = script_bytes[r_start:r_end]

                    pos = r_end
                    if script_bytes[pos] != 0x02:
                        i += 1
                        continue
                    s_len = script_bytes[pos + 1]
                    s_start = pos + 2
                    s_end = s_start + s_len
                    if s_end > seq_end:
                        i += 1
                        continue
                    s_bytes = script_bytes[s_start:s_end]

                    # Strip leading 0x00 padding used for positive-integer encoding
                    if len(r_bytes) > 32 and r_bytes[0] == 0x00:
                        r_bytes = r_bytes[1:]
                    if len(s_bytes) > 32 and s_bytes[0] == 0x00:
                        s_bytes = s_bytes[1:]

                    if 0 < len(r_bytes) <= 33 and 0 < len(s_bytes) <= 33:
                        return {'r': r_bytes.hex(), 's': s_bytes.hex()}
                except IndexError:
                    pass
        i += 1

    return None


def get_address_data(address: str, offset: int = 0, limit: int = 50,
                      max_retries: int = 5) -> Dict[str, Any]:
    """
    Fetch one page of address data from blockchain.info with retry logic.
    NOTE: blockchain.info's rawaddr endpoint caps out at 50 tx per call,
    so callers must page through with `offset` to get full history.
    """
    url = f"https://blockchain.info/rawaddr/{address}?limit={limit}&offset={offset}"

    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=30)

            if response.status_code == 429:
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
            time.sleep(1.5)

    return {}


def fetch_all_transactions(address: str, page_size: int = 50) -> Tuple[List[Dict], int]:
    """
    Page through blockchain.info until every transaction for the address
    has been retrieved. Returns (all_txs, reported_n_tx).
    """
    print(f"\n📡 Fetching data for address: {address}")
    first_page = get_address_data(address, offset=0, limit=page_size)

    n_tx = first_page.get('n_tx', 0)
    if n_tx == 0:
        return [], 0

    all_txs = list(first_page.get('txs', []))

    remaining = n_tx - len(all_txs)
    if remaining > 0:
        pages_needed = (remaining + page_size - 1) // page_size
        print(f"📊 Address reports {n_tx} total transactions — "
              f"fetching {pages_needed} additional page(s)...")

        offset = len(all_txs)
        with tqdm(total=remaining, desc="Fetching pages", unit="tx") as pbar:
            while offset < n_tx:
                page = get_address_data(address, offset=offset, limit=page_size)
                page_txs = page.get('txs', [])
                if not page_txs:
                    break  # nothing more to fetch, avoid infinite loop
                all_txs.extend(page_txs)
                pbar.update(len(page_txs))
                offset += len(page_txs)
                time.sleep(0.3)  # be polite to the free API

    # De-duplicate in case pages overlap
    seen = set()
    deduped = []
    for tx in all_txs:
        h = tx.get('hash')
        if h and h not in seen:
            seen.add(h)
            deduped.append(tx)

    return deduped, n_tx


def analyze_transactions(address: str, txs: List[Dict]) -> List[Dict]:
    """Analyze transactions and extract R/S values with proper DER parsing."""
    tx_details = []

    print("\n" + "═" * 80)
    print("📊 ANALYZING TRANSACTIONS")
    print("═" * 80)

    num_txs = len(txs)
    if num_txs == 0:
        print("❌ No transactions found for this address")
        return []

    print(f"📊 Processing {num_txs} transactions from wallet: {address}")
    print("═" * 40)

    for tx_idx, tx in enumerate(tqdm(txs, desc="Scanning signatures", unit="tx")):
        tx_hash = tx.get('hash', 'Unknown')
        vin_sz = tx.get('vin_sz', 0)
        time_val = tx.get('time', 0)

        for idx, input_script in enumerate(tx.get('inputs', [])):
            script = input_script.get('script', '')
            if len(script) < 20:
                continue

            der_parts = extract_r_s_from_der(script)
            if not der_parts:
                continue

            r_value = der_parts['r']
            s_value = der_parts['s']

            prev_out = input_script.get('prev_out', {}) or {}
            prev_addr = prev_out.get('addr', 'Unknown')
            prev_value = prev_out.get('value', 0)

            tx_details.append({
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
                'prev_value': prev_value,
            })

    print(f"\n{'=' * 80}")
    print("📊 SCAN COMPLETE")
    print(f"{'=' * 80}")
    print(f"  ✅ Total signed inputs found: {len(tx_details)}")

    r_counts = defaultdict(int)
    for d in tx_details:
        r_counts[d['r_value']] += 1
    unique_r = len(r_counts)
    repeated = {k: v for k, v in r_counts.items() if v > 1}

    print(f"  🔑 Unique R values: {unique_r}")
    if repeated:
        print(f"  ⚠️  R values reused: {len(repeated)}")
    else:
        print("  ✅ No repeated R values detected in this pass")

    return tx_details


def find_reused_r_values(tx_details: List[Dict]) -> List[Dict]:
    """Find reused R values and return all pairwise combinations."""
    r_value_groups = defaultdict(list)
    for detail in tx_details:
        r_value_groups[detail['r_value']].append(detail)

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
                        'all_inputs': items,
                    })
    return reused_pairs


def fmt_time(t):
    return time.ctime(t) if t else "Unknown"


def display_results(reused_pairs: List[Dict], address: str, num_txs: int, total_inputs: int):
    """Display detailed, complete results — what, where, which, how."""
    if not reused_pairs:
        print("\n" + "=" * 80)
        print("✅ No reused R values found across the full transaction history.")
        print("=" * 80)
        return

    print("\n" + "=" * 80)
    print(f"⚠️  ALERT: {len(reused_pairs)} reused R-value pair(s) found!")
    print("=" * 80)

    print("\n" + "═" * 80)
    print("🔴 AFFECTED WALLET ADDRESS")
    print("═" * 80)
    print(f"  💰 {address}")

    r_value_summary = defaultdict(list)
    for pair in reused_pairs:
        r_value_summary[pair['r_value']].append(pair)

    print("\n" + "═" * 80)
    print("📊 REUSED R VALUES — SUMMARY")
    print("═" * 80)
    for r_val, pairs in r_value_summary.items():
        total_uses = pairs[0]['total_uses']
        affected_txs = set()
        for p in pairs:
            affected_txs.add(p['input1']['tx_hash'])
            affected_txs.add(p['input2']['tx_hash'])
        print(f"\n  🔑 R = {r_val}")
        print(f"     • Used {total_uses} time(s) across {len(affected_txs)} transaction(s)")
        print(f"     • Produces {len(pairs)} vulnerable signature pair(s)")

    print("\n" + "═" * 80)
    print("🔍 DETAILED PAIR-BY-PAIR BREAKDOWN")
    print("═" * 80)

    for pair_num, pair in enumerate(reused_pairs, 1):
        print(f"\n{'=' * 80}")
        print(f"🔴 PAIR #{pair_num}")
        print(f"{'=' * 80}")
        print(f"\n🔑 Reused R value: {pair['r_value']}")
        print(f"   Total uses: {pair['total_uses']}")

        for label, inp in (("INPUT 1", pair['input1']), ("INPUT 2", pair['input2'])):
            print(f"\n📍 {label}")
            print("─" * 40)
            print(f"  🏷️  TX hash:        {inp['tx_hash']}")
            print(f"  🔢 Input index:    {inp['input_index']} (of {inp['vin_sz']} inputs)")
            print(f"  🔑 R value:        {inp['r_value']}")
            print(f"  🔐 S value:        {inp['s_value']}")
            if inp['prev_addr'] != 'Unknown':
                print(f"  📤 Funding addr:   {inp['prev_addr']}")
                print(f"  💰 Amount:         {inp['prev_value'] / 1e8:.8f} BTC")
            print(f"  🕐 Time:           {fmt_time(inp['time'])}")

        if pair['total_uses'] > 2:
            print("\n📋 ALL OCCURRENCES OF THIS R VALUE:")
            print("─" * 40)
            for i, inp in enumerate(pair['all_inputs'], 1):
                print(f"  {i}. TX {inp['tx_hash']}  |  input #{inp['input_index']}  |  {fmt_time(inp['time'])}")

        print("\n" + "─" * 40)
        print("⚠️  Same R (nonce) reused across two ECDSA signatures from this wallet.")
        print("─" * 40)

    affected_txs = set()
    for pair in reused_pairs:
        affected_txs.add(pair['input1']['tx_hash'])
        affected_txs.add(pair['input2']['tx_hash'])

    print("\n" + "═" * 80)
    print("📊 COMPREHENSIVE SUMMARY")
    print("═" * 80)
    print(f"  🔴 Wallet:                   {address}")
    print(f"  📊 Transactions analyzed:    {num_txs}")
    print(f"  📊 Signed inputs analyzed:   {total_inputs}")
    print(f"  ⚠️  Reused-R pairs found:     {len(reused_pairs)}")
    print(f"  🔑 Unique R values reused:   {len(r_value_summary)}")
    print(f"  📋 Transactions affected:    {len(affected_txs)}")

    print("\n" + "═" * 80)
    print("📋 ALL AFFECTED TRANSACTIONS")
    print("═" * 80)
    for i, tx_hash in enumerate(sorted(affected_txs), 1):
        matches = [d for pair in reused_pairs
                   for d in (pair['input1'], pair['input2']) if d['tx_hash'] == tx_hash]
        if matches:
            d = matches[0]
            r_list = sorted({m['r_value'] for m in matches})
            print(f"  {i}. {tx_hash}")
            print(f"      Inputs: {d['vin_sz']} | Time: {fmt_time(d['time'])}")
            print(f"      R value(s) involved: {', '.join(r_list)}")

    print("\n" + "═" * 80)
    print("🚨 RECOMMENDATION")
    print("═" * 80)
    print("  This is the well-known ECDSA nonce-reuse (repeated-R) vulnerability.")
    print("  With two signatures sharing an R value, the private key controlling")
    print("  this address can be mathematically recovered by anyone who sees them")
    print("  on-chain — this data is already public. If this wallet is yours,")
    print("  move any remaining funds to a new address generated with a wallet")
    print("  that uses proper deterministic nonces (RFC 6979), and stop reusing it.")
    print("=" * 80)


def main():
    print_logo()
    print("WELCOME TO Reused R Scanner 0.9!\n")

    address = input("Enter the Bitcoin address to scan: ").strip()
    if not address:
        print("❌ Invalid address. Please try again.")
        sys.exit(1)

    print("⏳ Please wait, this may take a moment for wallets with long histories...")

    try:
        all_txs, reported_n_tx = fetch_all_transactions(address)
    except Exception as e:
        print(f"❌ Error processing address data: {e}")
        sys.exit(1)

    if reported_n_tx == 0 or not all_txs:
        print(f"❌ No transactions found for address: {address}")
        sys.exit(1)

    print(f"\n📊 Address: {address}")
    print(f"📊 Transactions reported by API: {reported_n_tx}")
    print(f"📊 Transactions actually fetched: {len(all_txs)}")
    if len(all_txs) < reported_n_tx:
        print("⚠️  Fetched fewer transactions than reported — API may have truncated results.")
    print("═" * 80)

    tx_details = analyze_transactions(address, all_txs)

    if not tx_details:
        print("\n❌ No valid input scripts with R values found!")
        sys.exit(0)

    print(f"\n📊 Total signed inputs extracted: {len(tx_details)}")
    print("\n🔍 Checking for reused R values...\n")

    reused_pairs = find_reused_r_values(tx_details)
    display_results(reused_pairs, address, len(all_txs), len(tx_details))


if __name__ == "__main__":
    main()
    sys.exit()
