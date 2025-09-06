#!/usr/bin/env python3
"""
Fetch publication statistics for ALL publications in the ETH Research Collection.
This script will take a while to run due to API rate limiting.
"""

import sys
from publication_stats import fetch_all_statistics


def main():
    """Fetch statistics for all publications."""
    print("=" * 70)
    print("ETH Research Collection - Complete Statistics Fetcher")
    print("=" * 70)
    print("This will fetch download and view statistics for ALL publications.")
    print("⚠️  This may take a while due to API rate limiting (1 second between requests)")
    print("⚠️  The process will be respectful to the API servers.")
    print()
    
    # Ask for confirmation
    response = input("Do you want to proceed? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("Operation cancelled.")
        return 0
    
    try:
        # Fetch all statistics
        df_main, df_monthly, df_countries = fetch_all_statistics(sample_only=False)
        
        print("\n" + "=" * 70)
        print("🎉 ALL STATISTICS SUCCESSFULLY COLLECTED!")
        print("=" * 70)
        print("\nFiles saved in data/ folder:")
        print("📊 publication_statistics.csv - Main statistics for all publications")
        print("📅 monthly_visits.csv - Time series data for all publications")  
        print("🌍 country_statistics.csv - Geographic distribution data")
        print("📋 publication_stats_raw.json - Complete raw API responses")
        
        print(f"\n📈 Summary:")
        print(f"   • Total publications: {len(df_main):,}")
        print(f"   • Total downloads: {df_main['total_downloads'].sum():,}")
        print(f"   • Total visits: {df_main['total_visits'].sum():,}")
        print(f"   • Countries represented: {df_countries['country'].nunique():,}")
        
        print("\n✅ Ready for dashboard integration!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Process interrupted by user.")
        print("Note: Any completed statistics have been saved.")
        return 1
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        print("Check your API credentials and network connection.")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())