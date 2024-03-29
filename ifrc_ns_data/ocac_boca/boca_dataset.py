"""
Module to handle BOCA data, including loading it from the API, cleaning, and processing.
"""
import requests
import warnings
import pandas as pd
from ifrc_ns_data.common import Dataset
from ifrc_ns_data.common.cleaners import NSInfoMapper


class BOCAAssessmentDatesDataset(Dataset):
    """
    Load BOCA assessment dates data from the API, and clean and process the data.

    Parameters
    ----------
    filepath : string (required)
        Path to save the dataset when loaded, and to read the dataset from.
    """
    def __init__(self, api_key):
        super().__init__(name='BOCA Assessment Dates')
        self.api_key = api_key.strip()


    def pull_data(self, filters=None):
        """
        Read in raw data from the BOCA Assessments Dates API from the NS databank.

        Parameters
        ----------
        filters : dict (default=None)
            Filters to filter by country or by National Society.
            Keys can only be "Country", "National Society name", or "ISO3". Values are lists.
            Note that this is NOT IMPLEMENTED and is only included in this method to ensure consistency with the parent class and other child classes.
        """
        # The data cannot be filtered from the API so raise a warning if filters are provided
        if (filters is not None) and (filters != {}):
            warnings.warn(f'Filters {filters} not applied because the API response cannot be filtered.')

        # Pull data from FDRS API
        response = requests.get(url=f'https://data-api.ifrc.org/api/bocapublic?apiKey={self.api_key}')
        response.raise_for_status()
        results = response.json()

        # Convert the data into a pandas DataFrame
        data = pd.DataFrame(results)

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
        # Use the NS code to add other NS information
        ns_info_mapper = NSInfoMapper()
        for column in self.index_columns:
            ns_id_mapped = ns_info_mapper.map(data=data['NsId'], map_from='National Society ID', map_to=column, errors='raise')\
                                         .rename(column)
            data = pd.concat([data.reset_index(drop=True), ns_id_mapped.reset_index(drop=True)], axis=1)
        data = data.drop(columns=['NsId', 'NsName'])

        # Add other columns and order the columns
        data = self.rename_columns(data, drop_others=True)
        data = self.order_index_columns(data)

        return data
