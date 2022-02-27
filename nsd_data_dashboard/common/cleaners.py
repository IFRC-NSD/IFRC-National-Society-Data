"""
Module to define data cleaners.
"""
import os
from ast import literal_eval
import warnings
import requests
import pandas as pd
import yaml
from . import NationalSocietiesInfo


class DatabankNSIDMap:
    """
    Get a map of National Society IDs for data in the NS Databank, to National Society names.

    Parameters
    ----------
    api_key : string (required)
        API key for the NS databank.
    """
    api_response = None

    def __init__(self, api_key):
        self.api_key = api_key


    def get_map(self, reverse=False):
        """
        Get a map of National Society IDs from the NS Databank, to National Society names.

        Parameters
        ----------
        reverse : boolean (default=False)
            If True, map NS names to NS IDs.
        """
        # Pull the data from the databank API
        if DatabankNSIDMapper.api_response is None:
            DatabankNSIDMapper.api_response = requests.get(url=f'https://data-api.ifrc.org/api/entities/ns?apiKey={self.api_key}')
            DatabankNSIDMapper.api_response.raise_for_status()

        # Get a map of NS IDs to NS names
        ns_ids_names_map = pd.DataFrame(DatabankNSIDMapper.api_response.json()).set_index('KPI_DON_code')['NSO_DON_name'].to_dict()
        if reverse: ns_ids_names_map = {v: k for k, v in ns_ids_names_map.items()}

        return ns_ids_names_map


class DatabankNSIDMapper:
    """
    Convert National Society IDs for data in the NS Databank, to names.

    Parameters
    ----------
    api_key : string (required)
        API key for the NS databank.
    """
    api_response = None

    def __init__(self, api_key):
        self.api_key = api_key


    def map(self, data, reverse=False):
        """
        Convert National Society IDs from the NS Databank, to National Society names.

        Parameters
        ----------
        data : pandas Series or list (required)
            Series or list of NS IDs from the NS Databank to be mapped to NS names.

        reverse : boolean (default=False)
            If True, map NS names to NS IDs.
        """
        # Pull the data from the databank API
        if DatabankNSIDMapper.api_response is None:
            DatabankNSIDMapper.api_response = requests.get(url=f'https://data-api.ifrc.org/api/entities/ns?apiKey={self.api_key}')
            DatabankNSIDMapper.api_response.raise_for_status()

        # Get a map of NS IDs to NS names
        ns_ids_names_map = pd.DataFrame(DatabankNSIDMapper.api_response.json()).set_index('KPI_DON_code')['NSO_DON_name'].to_dict()
        if reverse: ns_ids_names_map = {v: k for k, v in ns_ids_names_map.items()}

        # Check if there are any unkown IDs
        unknown_ids = set(data).difference(ns_ids_names_map.keys())
        if unknown_ids:
            warnings.warn(f'Unknown NSs in data will not be converted: {unknown_ids}')

        # Map the names depending on the data type, and return
        if isinstance(data, pd.Series):
            results = data.map(ns_ids_names_map)
        elif isinstance(data, list):
            results = [ns_ids_names_map[ns_id] if (ns_id in ns_ids_names_map) else ns_id for ns_id in data]
        else:
            raise TypeError('Unrecognised type', type(data))

        return results


class NSInfoCleaner:
    """
    Compare a list of National Society names against a central list of National
    Society names to ensure that all names are recognised and consistent.
    Run some basic cleaning including stripping whitespace.
    """
    def __init__(self):
        pass


    def clean(self, data, column, errors='raise'):
        """
        Compare the NS names in the provided data series to a known list of National Society names.

        Parameters
        ----------
        data : pandas Series (required)
            Series of a pandas DataFrame to be cleaned.

        column : string (required)
            Name of the column to be used to compare the data to, to clean.

        errors : string (default='warn')
            What to do with errors: raise, warn, or ignore.
        """
        ns_info = NationalSocietiesInfo().data

        # Run some basic cleaning
        data = data.str.strip()

        # Map the list of alternative names including country names to the main name
        alternative_names = {'National Society name': 'Alternative National Society names', 'Country': 'Alternative country names'}
        if column not in alternative_names:
            raise ValueError(f'Unrecognised column name for cleaning {column}')
        alt_column = alternative_names[column]
        ns_clean_map = {}
        for ns in ns_info:
            for alt_name in ns[alt_column]:
                ns_clean_map[alt_name] = ns[column]
        data = data.replace(ns_clean_map)

        # Check for unrecognised values
        unrecognised_values = set(data.unique()).difference(set([ns[column] for ns in ns_info]))
        if unrecognised_values:
            if errors=='ignore':
                pass
            elif errors=='warn':
                warnings.warn(f'Unknown NS names in data: {unrecognised_values}')
            elif errors=='raise':
                raise ValueError(f'Unknown NS names in data: {unrecognised_values}')
            else:
                raise ValueError(f'Unrecognised values for parameter errors: {errors}')

        return data


    def clean_ns_names(self, data, errors='raise'):
        """
        Compare the NS names in the provided data series to a known list of National Society names.

        Parameters
        ----------
        data : pandas Series (required)
            Series of a pandas DataFrame to be cleaned.

        errors : string (default='warn')
            What to do with errors: raise, warn, or ignore.
        """
        data = self.clean(data=data, column='National Society name', errors=errors)
        return data


    def clean_country_names(self, data, errors='raise'):
        """
        Compare the NS names in the provided data series to a known list of National Society names.

        Parameters
        ----------
        data : pandas Series (required)
            Series of a pandas DataFrame to be cleaned.

        errors : string (default='warn')
            What to do with errors: raise, warn, or ignore.
        """
        data = self.clean(data=data, column='Country', errors=errors)
        return data


class NSInfoMapper:
    """
    Take in a dataset and merge in National Society information including country and region information.
    """
    def __init__(self):
        pass


    def map(self, data, on, column, errors='warn'):
        """
        Merge NS information into the dataset.

        Parameters
        ----------
        data : pandas Series (required)
            Pandas Series.

        on : string (required)
            Column to use to merge the data onto.

        column : string (required)
            Name of the column to map onto the data.

        errors : string (default='warn')
            What to do with errors: raise, warn, or ignore.
        """
        # Map the list of alternative names to the main name
        ns_info_data = NationalSocietiesInfo().data
        ns_map = {ns[on]: ns[column] for ns in ns_info_data}

        # Check if there are any unknown values
        unknown_values = [value for value in data.unique() if (value==value) and (value not in ns_map)]
        if unknown_values:
            if errors=='ignore':
                pass
            elif errors=='warn':
                warnings.warn(f'Unknown {on} values in data will not be converted: {unknown_values}')
            elif errors=='raise':
                raise ValueError(f'Unknown {on} values in data will not be converted: {unknown_values}')
            else:
                raise ValueError(f'Unrecognised values for parameter errors: {errors}')

        # Map the NS names to the NS IDs in the provided data
        return data.map(ns_map)


    def map_iso_to_ns(self, data, errors='ignore'):
        """
        Map the country ISO3 codes in the provided data series to National Society names.

        Parameters
        ----------
        data : pandas Series (required)
            Series of a pandas DataFrame to be mapped to National Society names.
        """
        mapped_data = self.map(data=data, on='ISO3', column='National Society name', errors=errors)
        return mapped_data


    def map_nsid_to_ns(self, data, errors='raise'):
        """
        Map NS IDs to NS names.

        Parameters
        ----------
        data : pandas Series (required)
            Series of a pandas DataFrame to be mapped to National Society names.
        """
        mapped_data = self.map(data=data, on='National Society ID', column='National Society name', errors=errors)
        return mapped_data


class DictColumnExpander:
    """
    Class to expand a dict-type column in a pandas DataFrame into multiple columns.
    """
    def __init__(self):
        pass


    def clean(self, data, columns, drop=False):
        """
        Expand the dict-type column into multiple columns
        Names of the new columns will be in the format column+dict_key.

        Parameters
        ----------
        data : pandas DataFrame (required)
            Pandas DataFrame containing the columns to expand.

        columns : string or list (required)
            List of columns, or the name of one column, to expand.

        drop : bool (default=False)
            If True, the original column(s) will be dropped from the DataFrame.
        """
        # Convert columns to a list if it is a string
        if not isinstance(columns, list):
            columns = [columns]
        if not isinstance(drop, list):
            drop = [drop]*len(columns)

        # Loop through the columns to expand, rename them, and append them to the original dataframe
        for column, drop_column in zip(columns, drop):
            data[column] = data[column].apply(lambda x: x if x!=x else literal_eval(str(x)))
            expanded_column = pd.json_normalize(data[column])
            expanded_column.rename(columns={dict_key: f'{column}.{dict_key}' for dict_key in expanded_column.columns},
                                   errors='raise',
                                   inplace=True)
            data = pd.concat([data, expanded_column], axis=1)
            if drop_column:
                data.drop(columns=[column], inplace=True)

        return data
