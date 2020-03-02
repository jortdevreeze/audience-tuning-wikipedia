# -*- coding: utf-8 -*-
"""
Created on Wed Feb 13 09:52:19 2020

@author: jdevreeze
"""

import argparse
import pandas as pd

def main():
    
    parser = argparse.ArgumentParser(description='Merge several pandas dataframes.') 

    parser.add_argument('--input', metavar='input', type=str, nargs='*', required=True, help='Opens several csv files from the specified path.')
    parser.add_argument('--output', metavar='output', type=str, required=True, help='Stores the merged data to the specified path.')

    args = parser.parse_args()

    frames = []

    for i, name in enumerate(args.input, 1):
        try:
            df = pd.read_csv(name, sep=';', encoding='utf-8')
        except:
            raise ValueError('Can not open the specified dataset.')

        df['ConflictType'] = i
        frames.append(df)

    df_merged = pd.concat(frames, sort=False)

    # Merge the datasets
    df_merged.to_csv(args.output, sep=';', encoding='utf-8', index=False)

if __name__ == "__main__":
   main()
 