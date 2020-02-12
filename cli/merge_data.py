# -*- coding: utf-8 -*-
"""
Created on Wed Feb 05 11:35:46 2020

@author: jdevreeze
"""

import argparse
import os
import re

import pandas as pd
import numpy as np

from tqdm import tqdm
from datetime import datetime

def iterateThroughData(path, selector):    
    for filename in os.listdir(path):        
        if filename.endswith('.csv'):            
            try:
                df = pd.read_csv(os.path.join(path, filename), encoding='utf-8')
                df = df.iloc[2:]
            except:
                raise ValueError('Can not open the dataset "%s" in the specified path.' % (filename))
            if len(df.filter(regex=selector).columns) is not 0:
                return df
    return False

def main():
    
    parser = argparse.ArgumentParser(description='Merge the processed data with all translations.') 
    
    # Required arguments to merge the translations with the raw data
    parser.add_argument('--input', metavar='input', type=str, required=True, help='Opens a csv file from the specified path.')
    parser.add_argument('--output', metavar='output', type=str, required=True, help='Stores the merged data to the specified path.')
    parser.add_argument('--path', metavar='path', type=str, required=True, help='Specify a path which contains all translations (i.e., csv files).')
    parser.add_argument('--regex', metavar='regex', type=str, required=True, help='Defines the first column name to use as selector.')
    
    # Optional arguments which overrides the default settings
    parser.add_argument('--pattern', metavar='pattern', type=str, default=False, help='Override the regex pattern that removes the edit id from all column names (default: "{}\w\D+{}").')
    parser.add_argument('--metadata', metavar='metadata', type=str, nargs='*', default=False, help='Override which columns contain metadata (default: ["ResponseId", "language", "english", "id"]).')
    parser.add_argument('--divider', metavar='divider', type=int, nargs=2, default=False, help='Override how to split up the columns in the dataset (default: [7,19]).')

    args = parser.parse_args()

    metadata = [
        'ResponseId',
        'language',
        'english',
        'comment',
        'id'
    ]

    pattern = r'{}\w\D+{}$'
    divider = [7,19]

    try:
        df = pd.read_csv(args.input, sep=';', encoding='utf-8')
    except:
        raise ValueError('Can not open the specified dataset.')

    edits = False

    print('%s: Merging the translations together with the raw data.' % (datetime.strftime(datetime.now(), '%Y-%m-%d | %H:%M:%S')))
    print('%s: Start iterating through %d records...' % (datetime.strftime(datetime.now(), '%Y-%m-%d | %H:%M:%S'), len(df)))

    # Check if we have to override the default arguments
    if args.pattern is not False:
        pattern = args.pattern

    if args.metadata is not False:
        metadata = args.metadata

    if args.divider is not False:
        divider = args.divider

    # Iterate through all edits
    for index, row in tqdm(df.iterrows()):

        selector = pattern.format(args.regex, str(row.EditId))
        data = iterateThroughData(args.path, selector)
        
        if data is not False and data.shape[1] > 0:
        
            i = data.columns.get_loc(data.filter(regex=selector).columns[0])
            n = i + divider[1] if row.Type is 2 else i + divider[0]
            
            meta = data[metadata]
            edit = data.iloc[:,i:n].dropna()
            meta = meta.loc[edit.index,:]
            
            if len(edit.columns) > divider[0] and str(row.EditId) not in edit.columns[-1]:
                error = True
                edit = edit.iloc[:,0:divider[0]].copy()
            
            count = len(edit.index)
            
            # Rename all columns in the dataset
            for idx, name in enumerate(edit.columns):
                regex = re.findall('\d+', name)
                prefix = '_' if '_' in name else ''            
                replace = re.sub(prefix + str(row.EditId), '', name)           
                if len(regex) > 1:
                    if regex[0] == regex[1]:
                        replace = re.sub('_\d_', '_', name)               
                edit.rename(columns={edit.columns[idx] : replace}, inplace=True)           
            
            edit = pd.concat([meta, edit], axis=1)
            
            # Insert additional data
            edit.insert(0, 'EditId', row.EditId)
            edit.insert(1, 'Count', count)
            
            # Create column in dataset
            if edits is False:
                edits = edit
            else:
                edits = pd.concat([edits, edit], sort=False)
            

    print('%s: Saving the merged dataset...' % (datetime.strftime(datetime.now(), '%Y-%m-%d | %H:%M:%S')))

    # Merge the datasets
    if edits is not False:        
        df_merged = pd.merge(df, edits, on='EditId', how='outer')
        df_merged.to_csv(args.output, sep=';', encoding='utf-8', index=False)

if __name__ == "__main__": 
   main() 
 
