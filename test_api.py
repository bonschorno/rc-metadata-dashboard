#!/usr/bin/env python3
"""
Test script for ETH Research Collection API connection.
Run this to verify your API setup is working correctly.
"""

import sys
import os
from pathlib import Path

def test_api_connection():
    """Test the API connection and data retrieval."""
    print("Testing ETH Research Collection API Connection")
    print("=" * 50)
    
    # Check for required packages
    try:
        import requests
        import pandas as pd
        from dotenv import load_dotenv
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("\nPlease install required packages:")
        print("  pip install requests pandas python-dotenv openpyxl")
        return False
    
    # Load environment variables
    load_dotenv()
    
    # Check for API key
    api_key = os.getenv('ETH_RC_API_KEY')
    if not api_key:
        print("❌ API key not found in environment")
        print("\nTo set up credentials, run:")
        print("  python setup_credentials.py")
        return False
    
    print(f"✓ API key found: {api_key[:10]}...")
    
    # Check for group ID
    group_id = os.getenv('ETH_RC_GROUP_ID', '09746')
    print(f"✓ Group ID: {group_id}")
    
    # Test API connection
    try:
        from api_client import ETHResearchCollectionAPI
        
        print("\nTesting API connection...")
        client = ETHResearchCollectionAPI(api_key=api_key, group_identifier=group_id)
        
        # Fetch a small number of items for testing
        data = client.fetch_publications(max_items=5)
        
        print("✓ API connection successful")
        
        # Extract and process metadata
        df = client.extract_metadata(data)
        
        print(f"✓ Successfully retrieved {len(df)} publications")
        
        if len(df) > 0:
            print("\nSample data:")
            print(f"  First publication: {df.iloc[0]['name'][:60]}...")
            print(f"  Publication types: {df['publication_type'].unique()[:3].tolist()}")
            print(f"  Years: {sorted(df['year'].dropna().unique())[:5]}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ API request failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_full_workflow():
    """Test the complete workflow including data save."""
    print("\n\nTesting Full Workflow")
    print("=" * 50)
    
    try:
        from api_client import ETHResearchCollectionAPI
        
        client = ETHResearchCollectionAPI()
        
        # Create test output directory
        test_dir = Path("test_output")
        test_dir.mkdir(exist_ok=True)
        
        print(f"Fetching and saving data to {test_dir}/...")
        df = client.fetch_and_save(output_dir=str(test_dir), max_items=10)
        
        # Check files exist
        csv_file = test_dir / 'ghe-research-collection.csv'
        excel_file = test_dir / 'ghe-research-collection.xlsx'
        
        if csv_file.exists() and excel_file.exists():
            print(f"✓ CSV file created: {csv_file}")
            print(f"✓ Excel file created: {excel_file}")
            
            # Clean up test files
            csv_file.unlink()
            excel_file.unlink()
            test_dir.rmdir()
            print("✓ Test files cleaned up")
            
            return True
        else:
            print("❌ Output files not created")
            return False
            
    except Exception as e:
        print(f"❌ Workflow test failed: {e}")
        return False


def main():
    """Run all tests."""
    success = True
    
    # Test API connection
    if not test_api_connection():
        success = False
    
    # Test full workflow if API connection works
    if success:
        if not test_full_workflow():
            success = False
    
    print("\n" + "=" * 50)
    if success:
        print("✅ All tests passed! Your API setup is working correctly.")
        print("\nYou can now run:")
        print("  python api_client.py")
        print("\nOr use the API in your dashboard:")
        print("  streamlit run app.py")
    else:
        print("❌ Some tests failed. Please check the error messages above.")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())