#!/usr/bin/env python3
"""
Fetch publication statistics from ETH Research Collection API.
This includes downloads, views, and geographic distribution data.
"""

import os
import json
import requests
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dotenv import load_dotenv
import time

load_dotenv()


class PublicationStatsAPI:
    """Client for fetching publication statistics from ETH Research Collection."""
    
    BASE_URL = "https://api.library.ethz.ch/research-collection/v2/statistics/usagereports/search/object"
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize API client with credentials."""
        self.api_key = api_key or os.getenv('ETH_RC_API_KEY')
        
        if not self.api_key:
            raise ValueError("API key not provided. Set ETH_RC_API_KEY environment variable or pass api_key parameter.")
    
    def fetch_publication_stats(self, uuid: str) -> Dict:
        """Fetch statistics for a single publication by UUID."""
        url = f"{self.BASE_URL}?uri=https://www.research-collection.ethz.ch/entities/publication/{uuid}&&apikey={self.api_key}"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching stats for UUID {uuid}: {e}")
            return None
    
    def extract_statistics(self, uuid: str, data: Dict) -> Dict:
        """Extract relevant statistics from API response."""
        stats = {
            'uuid': uuid,
            'total_downloads': 0,
            'total_visits': 0,
            'monthly_visits': [],
            'top_countries': []
        }
        
        if not data or '_embedded' not in data:
            return stats
        
        # Parse the nested structure
        reports = data['_embedded'].get('usagereports', [])
        
        for report in reports:
            report_type = report.get('report-type', '')
            points = report.get('points', [])
            
            if report_type == 'TotalDownloads':
                # Sum all download views from different files
                for point in points:
                    stats['total_downloads'] += point.get('values', {}).get('views', 0)
            
            elif report_type == 'TotalVisits':
                # Get total visits
                for point in points:
                    stats['total_visits'] = point.get('values', {}).get('views', 0)
            
            elif report_type == 'TotalVisitsPerMonth':
                # Extract monthly visits
                monthly_data = []
                for point in points:
                    monthly_data.append({
                        'month': point.get('label', ''),
                        'visits': point.get('values', {}).get('views', 0)
                    })
                stats['monthly_visits'] = monthly_data
            
            elif report_type == 'TopCountries':
                # Extract country statistics
                country_data = []
                total_country_views = sum(p.get('values', {}).get('views', 0) for p in points)
                for point in points:
                    views = point.get('values', {}).get('views', 0)
                    country_data.append({
                        'country_code': point.get('id', ''),
                        'country': point.get('label', ''),
                        'visits': views,
                        'percentage': round((views / total_country_views * 100) if total_country_views > 0 else 0, 2)
                    })
                stats['top_countries'] = country_data
        
        return stats
    
    def fetch_multiple_stats(self, uuids: List[str], titles: Optional[List[str]] = None, delay: float = 0.5) -> List[Dict]:
        """Fetch statistics for multiple publications with rate limiting."""
        all_stats = []
        
        for i, uuid in enumerate(uuids, 1):
            title = titles[i-1] if titles and i-1 < len(titles) else "Unknown Title"
            print(f"Fetching stats for publication {i}/{len(uuids)}: {title[:60]}...")
            
            data = self.fetch_publication_stats(uuid)
            stats = self.extract_statistics(uuid, data)
            stats['title'] = title  # Add title to stats
            all_stats.append(stats)
            
            # Rate limiting - be nice to the API
            if i < len(uuids):
                time.sleep(delay)
        
        return all_stats
    
    def process_to_dataframes(self, stats_list: List[Dict]) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Process statistics into separate dataframes for different data types."""
        
        # Main statistics dataframe
        main_stats = []
        monthly_visits_data = []
        country_stats_data = []
        
        for stats in stats_list:
            main_stats.append({
                'uuid': stats['uuid'],
                'title': stats.get('title', 'Unknown Title'),
                'total_downloads': stats['total_downloads'],
                'total_visits': stats['total_visits'],
                'num_months_with_data': len(stats['monthly_visits']),
                'num_countries': len(stats['top_countries'])
            })
            
            # Process monthly visits
            for month_data in stats['monthly_visits']:
                if isinstance(month_data, dict):
                    monthly_visits_data.append({
                        'uuid': stats['uuid'],
                        'title': stats.get('title', 'Unknown Title'),
                        'month': month_data.get('month', ''),
                        'visits': month_data.get('visits', 0)
                    })
            
            # Process country statistics
            for country_data in stats['top_countries']:
                if isinstance(country_data, dict):
                    country_stats_data.append({
                        'uuid': stats['uuid'],
                        'title': stats.get('title', 'Unknown Title'),
                        'country_code': country_data.get('country_code', ''),
                        'country': country_data.get('country', ''),
                        'visits': country_data.get('visits', 0)
                    })
        
        df_main = pd.DataFrame(main_stats)
        df_monthly = pd.DataFrame(monthly_visits_data)
        df_countries = pd.DataFrame(country_stats_data)
        
        return df_main, df_monthly, df_countries
    
    def save_statistics(self, stats_list: List[Dict], output_dir: str = 'data', output_suffix: str = ''):
        """Save statistics to CSV files."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        df_main, df_monthly, df_countries = self.process_to_dataframes(stats_list)
        
        # Save main statistics
        main_file = output_path / f'publication_statistics{output_suffix}.csv'
        df_main.to_csv(main_file, index=False)
        print(f"✓ Main statistics saved to {main_file}")
        
        # Save monthly visits data
        if not df_monthly.empty:
            monthly_file = output_path / f'monthly_visits{output_suffix}.csv'
            df_monthly.to_csv(monthly_file, index=False)
            print(f"✓ Monthly visits saved to {monthly_file}")
        
        # Save country statistics
        if not df_countries.empty:
            country_file = output_path / f'country_statistics{output_suffix}.csv'
            df_countries.to_csv(country_file, index=False)
            print(f"✓ Country statistics saved to {country_file}")
        
        # Also save raw JSON for reference
        json_file = output_path / f'publication_stats_raw{output_suffix}.json'
        with open(json_file, 'w') as f:
            json.dump(stats_list, f, indent=2)
        print(f"✓ Raw data saved to {json_file}")
        
        return df_main, df_monthly, df_countries


def test_with_sample_uuids():
    """Test function to fetch stats for first 3 publications."""
    return fetch_all_statistics(sample_only=True, max_publications=3)


def fetch_all_statistics(sample_only=False, max_publications=None):
    """Fetch statistics for all publications or a sample."""
    from api_client import ETHResearchCollectionAPI
    
    print("Fetching all publications to get UUIDs and titles...")
    pub_client = ETHResearchCollectionAPI()
    
    # Fetch all publications (or specified max)
    fetch_limit = max_publications if sample_only and max_publications else 150
    df_publications = pub_client.fetch_and_save(max_items=fetch_limit)
    
    # Get all UUIDs and titles
    all_data = df_publications[['uuid', 'name']]
    if sample_only and max_publications:
        all_data = all_data.head(max_publications)
    
    all_uuids = all_data['uuid'].tolist()
    all_titles = all_data['name'].tolist()
    
    total_pubs = len(all_uuids)
    print(f"\n{'Sample' if sample_only else 'All'} publications to process: {total_pubs}")
    if sample_only:
        for i, (uuid, title) in enumerate(zip(all_uuids, all_titles), 1):
            print(f"  {i}. {title[:60]}... ({uuid})")
    else:
        print("Processing all publications...")
        # Show first few for reference
        for i in range(min(3, total_pubs)):
            print(f"  {i+1}. {all_titles[i][:60]}...")
        if total_pubs > 3:
            print(f"  ... and {total_pubs-3} more publications")
    
    # Fetch statistics with appropriate delay for large batches
    delay = 0.5 if sample_only else 1.0  # Longer delay for full batch to be API-friendly
    print(f"\nFetching statistics (with {delay}s delay between requests)...")
    
    stats_client = PublicationStatsAPI()
    stats_list = stats_client.fetch_multiple_stats(all_uuids, all_titles, delay=delay)
    
    # Save results
    output_suffix = "_sample" if sample_only else ""
    print(f"\nSaving statistics to data/ folder{' (sample)' if sample_only else ''}...")
    df_main, df_monthly, df_countries = stats_client.save_statistics(stats_list, output_suffix=output_suffix)
    
    # Display summary
    print("\n" + "="*60)
    print(f"Summary of {'sample' if sample_only else 'complete'} statistics:")
    print("="*60)
    
    print(f"\n📊 Total publications processed: {len(stats_list)}")
    print(f"📈 Total downloads across all publications: {df_main['total_downloads'].sum():,}")
    print(f"👁️  Total visits across all publications: {df_main['total_visits'].sum():,}")
    print(f"🌍 Unique countries represented: {df_countries['country'].nunique()}")
    
    # Show top publications by downloads and visits
    print(f"\n🔥 Top publications by downloads:")
    top_downloads = df_main.nlargest(3, 'total_downloads')[['title', 'total_downloads', 'total_visits']]
    for idx, row in top_downloads.iterrows():
        print(f"   • {row['title'][:50]}... ({row['total_downloads']} downloads, {row['total_visits']} visits)")
    
    print(f"\n👀 Top publications by visits:")
    top_visits = df_main.nlargest(3, 'total_visits')[['title', 'total_downloads', 'total_visits']]
    for idx, row in top_visits.iterrows():
        print(f"   • {row['title'][:50]}... ({row['total_visits']} visits, {row['total_downloads']} downloads)")
    
    # Show top countries
    if not df_countries.empty:
        print(f"\n🌍 Top countries by total visits:")
        country_totals = df_countries.groupby('country')['visits'].sum().nlargest(5)
        for country, visits in country_totals.items():
            print(f"   • {country}: {visits:,} visits")
    
    print("\n✅ Statistics collection completed successfully!")
    
    return df_main, df_monthly, df_countries


if __name__ == "__main__":
    test_with_sample_uuids()