"""
Module to handle NS documents data from FDRS, including loading it from the API, cleaning, and processing.
"""
import requests
import pandas as pd
from ifrc_ns_data.common import Dataset, NationalSocietiesInfo
from ifrc_ns_data.common.cleaners import DatabankNSIDMap, NSInfoMapper


class NSDocumentsDataset(Dataset):
    """
    Load NS documents data from the NS databank API, and clean and process the data.

    Parameters
    ----------
    filepath : string (required)
        Path to save the dataset when loaded, and to read the dataset from.
    """
    def __init__(self, api_key):
        super().__init__(name='NS Documents')
        self.api_key = api_key.strip()


    def pull_data(self, filters=None):
        """
        Read in data from the NS Databank API and save to file.

        Parameters
        ----------
        filters : dict (default=None)
            Filters to filter by country or by National Society.
            Keys can only be "Country", "National Society name", or "ISO3". Values are lists.
        """
        # Get the list of NSs
        selected_ns = NationalSocietiesInfo().data
        for filter_name, filter_values in filters.items():
            selected_ns = [ns for ns in selected_ns if ns[filter_name] in filter_values]
        selected_ns_ids = [ns['National Society ID'] for ns in selected_ns if ns['National Society ID'] is not None]

        # Pull data from FDRS API
        response = requests.get(url=f'https://data-api.ifrc.org/api/documents?ns={",".join(selected_ns_ids)}&apiKey={self.api_key}')
        response.raise_for_status()
        results = response.json()

        # Make the format consistent for if one or multiple NSs are provided
        if len(selected_ns_ids)==1:
            results = [results]

        # Loop through the NS results and merge into a single DataFrame with a column giving the NS code
        data_list = []
        for ns_response in results:
            ns_documents = pd.DataFrame(ns_response['documents'])
            ns_documents['National Society ID'] = ns_response['code']
            data_list.append(ns_documents)
        data = pd.concat(data_list, axis='rows')

        return data


    def process_data(self, data, latest=False):
        """
        Transform and process the data, including changing the structure and selecting columns.

        Parameters
        ----------
        data : pandas DataFrame (required)
            Raw data to be processed.

        latest : bool (default=False)
            If True, only the latest data for each National Society and indicator will be returned.
        """
        # Add extra NS and country information based on the NS ID
        data = data[['National Society ID', 'name', 'document_type', 'year', 'url']].reset_index(drop=True)
        ns_info_mapper = NSInfoMapper()
        for column in self.index_columns:
            ns_id_mapped = ns_info_mapper.map(data=data['National Society ID'], map_from='National Society ID', map_to=column, errors='raise')\
                                         .rename(column)
            data = pd.concat([data.reset_index(drop=True), ns_id_mapped.reset_index(drop=True)], axis=1)

        # Keep only the latest document for each document type and NS
        data = data.dropna(subset=['National Society name', 'document_type', 'year'], how='any')\
                             .sort_values(by=['National Society name', 'document_type'], ascending=True)\
                             .rename(columns={'url': 'Value', 'document_type': 'Indicator', 'year': 'Year'})
        data['Indicator'] = data['Indicator'].str.strip()

        # Drop columns which are not needed
        data = data.drop(columns=['name', 'National Society ID'])

        # Select and rename indicators
        data = self.rename_indicators(data, missing='ignore')
        data = self.order_index_columns(data, other_columns=['Indicator', 'Value', 'Year'])

        # Filter the dataset if required
        if latest:
            data = self.filter_latest_indicators(data).reset_index(drop=True)

        return data
