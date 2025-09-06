import os
import json
import requests
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class ETHResearchCollectionAPI:
    """Client for ETH Research Collection API."""
    
    BASE_URL = "https://api.library.ethz.ch/research-collection/v2/discover/search/objects"
    
    def __init__(self, api_key: Optional[str] = None, group_identifier: Optional[str] = None):
        """Initialize API client with credentials from environment or parameters."""
        self.api_key = api_key or os.getenv('ETH_RC_API_KEY')
        self.group_identifier = group_identifier or os.getenv('ETH_RC_GROUP_ID', '09746')
        
        if not self.api_key:
            raise ValueError("API key not provided. Set ETH_RC_API_KEY environment variable or pass api_key parameter.")
    
    def fetch_publications(self, max_items: int = 150) -> Dict:
        """Fetch publications for the configured group."""
        params = {
            'query': f'leitzahlCode:{self.group_identifier}',
            'size': max_items,
            'apikey': self.api_key
        }
        
        response = requests.get(self.BASE_URL, params=params)
        response.raise_for_status()
        
        return response.json()
    
    def extract_metadata(self, data: Dict) -> pd.DataFrame:
        """Extract and process metadata from API response."""
        try:
            # Navigate through the nested structure more carefully
            embedded = data.get('_embedded', {})
            search_result = embedded.get('searchResult', {})
            
            # Handle both single result and array of results
            if '_embedded' in search_result:
                objects_wrapper = search_result['_embedded'].get('objects', [])
                
                # Objects can be a list or a single object
                if isinstance(objects_wrapper, list):
                    objects = []
                    for obj_wrapper in objects_wrapper:
                        if '_embedded' in obj_wrapper and 'indexableObject' in obj_wrapper['_embedded']:
                            objects.append(obj_wrapper['_embedded']['indexableObject'])
                elif isinstance(objects_wrapper, dict):
                    if '_embedded' in objects_wrapper and 'indexableObject' in objects_wrapper['_embedded']:
                        indexable = objects_wrapper['_embedded']['indexableObject']
                        objects = [indexable] if isinstance(indexable, dict) else indexable
                else:
                    objects = []
            else:
                objects = []
                
        except (KeyError, TypeError) as e:
            print(f"Debug - API response keys: {data.keys() if isinstance(data, dict) else 'Not a dict'}")
            if '_embedded' in data:
                print(f"Debug - _embedded keys: {data['_embedded'].keys()}")
            raise ValueError(f"Unexpected API response structure: {e}")
        
        publications = []
        relevant_metadata = ['dc.identifier.doi', 'dc.type', 'dc.date.issued', 'dc.rights.license']
        
        for obj in objects:
            publication = {
                'name': obj.get('name', ''),
                'uuid': obj.get('uuid', '')
            }
            
            metadata = obj.get('metadata', {})
            for field in relevant_metadata:
                if field in metadata and metadata[field]:
                    value = metadata[field][0].get('value') if isinstance(metadata[field], list) else metadata[field].get('value')
                    publication[field] = value
                else:
                    publication[field] = None
            
            publications.append(publication)
        
        df = pd.DataFrame(publications)
        
        df = df.rename(columns={
            'dc.identifier.doi': 'doi',
            'dc.type': 'publication_type',
            'dc.date.issued': 'date_issued',
            'dc.rights.license': 'license'
        })
        
        return self._process_dataframe(df)
    
    def _process_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process and enhance the publications dataframe."""
        df['year'] = pd.to_numeric(df['date_issued'].str[:4], errors='coerce')
        
        df['license'] = df['license'].fillna('No license')
        
        license_mapping = {
            'Creative Commons Attribution 4.0 International': 'CC BY 4.0',
            'Creative Commons Attribution-NonCommercial 4.0 International': 'CC BY-NC 4.0',
            'In Copyright - Non-Commercial Use Permitted': 'Copyright',
            'Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International': 'CC BY-NC-ND 4.0',
            'Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International': 'CC BY-NC-SA 4.0'
        }
        df['license_short'] = df['license'].map(license_mapping).fillna(df['license'])
        
        df['license_short_group'] = df['license_short'].apply(
            lambda x: 'CC BY 4.0' if '4.0' in str(x) else x
        )
        
        def categorize_publication(pub_type):
            if pub_type in ['Student Paper', 'Bachelor Thesis', 'Master Thesis']:
                return 'Student Paper'
            elif pub_type in ['Dataset', 'Data Collection']:
                return 'Dataset'
            elif pub_type in ['Journal Article', 'Review Article', 'Book Chapter']:
                return 'Scientific Article'
            else:
                return 'Other publication'
        
        df['publication_type_group'] = df['publication_type'].apply(categorize_publication)
        
        df['doi_dummy'] = df['doi'].apply(lambda x: 'Has DOI' if pd.notna(x) else 'No DOI')
        
        column_order = ['name', 'doi', 'doi_dummy', 'publication_type', 'publication_type_group',
                       'date_issued', 'year', 'license', 'license_short', 'license_short_group']
        existing_columns = [col for col in column_order if col in df.columns]
        df = df[existing_columns]
        
        df = df[df['year'] > 2010]
        
        return df
    
    def fetch_and_save(self, output_dir: str = '.', max_items: int = 150) -> pd.DataFrame:
        """Fetch publications and save to CSV and Excel files."""
        print(f"Fetching publications for group {self.group_identifier}...")
        data = self.fetch_publications(max_items)
        
        print("Extracting metadata...")
        df = self.extract_metadata(data)
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        csv_file = output_path / 'ghe-research-collection.csv'
        excel_file = output_path / 'ghe-research-collection.xlsx'
        
        df.to_csv(csv_file, index=False)
        df.to_excel(excel_file, index=False)
        
        print(f"Data saved to {csv_file} and {excel_file}")
        print(f"Total publications: {len(df)}")
        
        return df


def main():
    """Main function to fetch and process research collection data."""
    try:
        client = ETHResearchCollectionAPI()
        df = client.fetch_and_save()
        
        print("\nData summary:")
        print(f"Publications by type:")
        print(df['publication_type_group'].value_counts())
        print(f"\nPublications by license:")
        print(df['license_short_group'].value_counts())
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())