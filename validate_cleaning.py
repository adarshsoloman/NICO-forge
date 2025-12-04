"""
Quick validation script to show before/after comparison of cleaned data
"""

import json

print("="*80)
print("BEFORE/AFTER COMPARISON - First 3 Entries")
print("="*80)

# Load original data
with open('outputs/en_hi_dataset.json', 'r', encoding='utf-8') as f:
    original = json.load(f)

# Load cleaned data
with open('outputs/cleaned_dataset.json', 'r', encoding='utf-8') as f:
    cleaned = json.load(f)

# Show first 3 entries
for i in range(min(3, len(cleaned))):
    print(f"\n{'─'*80}")
    print(f"ENTRY {i+1}")
    print(f"{'─'*80}")
    
    # Find matching original entry
    orig_entry = next((e for e in original if e.get('chunk_id') == cleaned[i].get('chunk_id')), None)
    
    if orig_entry:
        print("\n🔴 ORIGINAL ENGLISH:")
        print(repr(orig_entry['english'][:200]))  # Show first 200 chars with escape sequences visible
        
        print("\n✅ CLEANED ENGLISH:")
        print(cleaned[i]['english'][:200])
        
        print("\n🔴 ORIGINAL HINDI:")
        print(repr(orig_entry['hindi'][:200]))
        
        print("\n✅ CLEANED HINDI:")
        print(cleaned[i]['hindi'][:200])

print(f"\n{'='*80}")
print(f"SUMMARY")
print(f"{'='*80}")
print(f"Original entries: {len(original)}")
print(f"Cleaned entries: {len(cleaned)}")
print(f"Entries removed: {len(original) - len(cleaned)}")
print(f"{'='*80}\n")
