#!/usr/bin/env python3
"""
Debug script to understand the ETH Research Collection API response structure.
"""

import json
import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def debug_api_response():
    """Debug the API response structure."""
    print("ETH Research Collection API Response Debugger")
    print("=" * 50)
    
    # Get credentials
    api_key = os.getenv('ETH_RC_API_KEY')
    if not api_key:
        print("❌ API key not found. Please set ETH_RC_API_KEY in .env file")
        print("\nCreate a .env file with:")
        print("ETH_RC_API_KEY=your_api_key_here")
        print("ETH_RC_GROUP_ID=09746")
        return
    
    group_id = os.getenv('ETH_RC_GROUP_ID', '09746')
    
    print(f"API Key: {api_key[:10]}...")
    print(f"Group ID: {group_id}")
    
    # Make API request
    url = "https://api.library.ethz.ch/research-collection/v2/discover/search/objects"
    params = {
        'query': f'leitzahlCode:{group_id}',
        'size': 2,  # Just get 2 items for debugging
        'apikey': api_key
    }
    
    print(f"\nMaking request to: {url}")
    print(f"Query: leitzahlCode:{group_id}")
    
    try:
        response = requests.get(url, params=params)
        print(f"Response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Response text: {response.text[:500]}")
            return
        
        data = response.json()
        
        # Save full response for inspection
        debug_file = Path("debug_response.json")
        with open(debug_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"\n✓ Full response saved to: {debug_file}")
        
        # Analyze structure
        print("\n" + "=" * 50)
        print("Response Structure Analysis:")
        print("=" * 50)
        
        def analyze_keys(obj, prefix="", max_depth=4, current_depth=0):
            """Recursively analyze object structure."""
            if current_depth >= max_depth:
                return
            
            if isinstance(obj, dict):
                for key in obj.keys():
                    value = obj[key]
                    if isinstance(value, dict):
                        print(f"{prefix}{key}: <dict with {len(value)} keys>")
                        if current_depth < max_depth - 1:
                            analyze_keys(value, prefix + "  ", max_depth, current_depth + 1)
                    elif isinstance(value, list):
                        print(f"{prefix}{key}: <list with {len(value)} items>")
                        if len(value) > 0 and current_depth < max_depth - 1:
                            print(f"{prefix}  [0]: {type(value[0]).__name__}")
                            if isinstance(value[0], dict):
                                analyze_keys(value[0], prefix + "    ", max_depth, current_depth + 2)
                    else:
                        value_str = str(value)[:50]
                        print(f"{prefix}{key}: {value_str}")
        
        analyze_keys(data)
        
        # Try to extract publication data
        print("\n" + "=" * 50)
        print("Attempting to Extract Publications:")
        print("=" * 50)
        
        # Try different paths
        paths_to_try = [
            ['_embedded', 'searchResult', '_embedded', 'objects'],
            ['_embedded', 'objects'],
            ['searchResult', '_embedded', 'objects'],
            ['results'],
            ['items'],
            ['data']
        ]
        
        for path in paths_to_try:
            try:
                current = data
                for key in path:
                    current = current[key]
                print(f"✓ Found data at path: {' -> '.join(path)}")
                print(f"  Type: {type(current).__name__}")
                if isinstance(current, list):
                    print(f"  Items: {len(current)}")
                    if len(current) > 0:
                        first_item = current[0]
                        if isinstance(first_item, dict):
                            print(f"  First item keys: {list(first_item.keys())[:5]}")
                break
            except (KeyError, TypeError):
                continue
        
        # Try to find indexableObject
        print("\n" + "=" * 50)
        print("Looking for indexableObject:")
        print("=" * 50)
        
        def find_key(obj, target_key, path="", results=None):
            """Recursively find a key in nested structure."""
            if results is None:
                results = []
            
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_path = f"{path}/{key}" if path else key
                    if key == target_key:
                        results.append(new_path)
                    find_key(value, target_key, new_path, results)
            elif isinstance(obj, list):
                for i, item in enumerate(obj[:2]):  # Check first 2 items
                    find_key(item, target_key, f"{path}[{i}]", results)
            
            return results
        
        paths = find_key(data, 'indexableObject')
        if paths:
            print(f"Found 'indexableObject' at paths:")
            for p in paths[:5]:  # Show first 5 paths
                print(f"  - {p}")
        
        # Look for metadata fields
        print("\n" + "=" * 50)
        print("Looking for metadata fields:")
        print("=" * 50)
        
        metadata_fields = ['name', 'uuid', 'metadata', 'dc.type', 'dc.identifier.doi']
        for field in metadata_fields:
            paths = find_key(data, field)
            if paths:
                print(f"'{field}' found at {len(paths)} location(s)")
                if len(paths) > 0:
                    print(f"  First path: {paths[0]}")
        
    except requests.RequestException as e:
        print(f"❌ Request failed: {e}")
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse JSON: {e}")
        print(f"Response text: {response.text[:500]}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    debug_api_response()