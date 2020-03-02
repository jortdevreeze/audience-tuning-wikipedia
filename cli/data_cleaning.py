# -*- coding: utf-8 -*-
"""
Created on Wed Jan 15 15:16:06 2020

@author: jdevreeze
@todo: Implement a pre-trained anomaly model for the extraction of meaningful edits
"""

import pandas as pd
import geoip2.database
import sqlite3
import argparse
import textwrap
import math

def main():
    
    parser = argparse.ArgumentParser(description='Clean all extracted Wikipedia data in the sqlite database.') 
    
    parser.add_argument('--sqlite', metavar='output', type=str, required=True, help='Open the sqlite database from the specified path.')
    parser.add_argument('--users', metavar='users', type=str, default=False, help='Specify a dataset with nationality and native language for each user (default: False).')
    parser.add_argument('--filter', metavar='filter', choices=range(1, 6), type=int, default=1, help='Apply a filter to extract meaningful edits. Specify the number of samples that should be used (default: 1)')

    args = parser.parse_args()

    # Open the sqlite database
    db = sqlite3.connect(args.sqlite)    
    cursor = db.cursor()
    
    # Validate the database
    for table in ['articles', 'revisions', 'edits', 'authors']:
        cursor.execute('''SELECT count(name) FROM sqlite_master WHERE type='table' AND name=?''', (table,))
        if cursor.fetchone()[0] != 1:
        	raise ValueError('The specified database is not valid (i.e., not all required tables exist).')
    
    
    if args.users is False:
        skip = True
    if args.users == 'anonymous':
        try:            
            df = geoip2.database.Reader('../models/GeoLite2-Country.mmdb')
            skip = False 
        except:
            raise ValueError('Can not open a valid GeoLite2 Country model. Make sure you have specified the correct filename.')
    else:
        try:         
            df = pd.read_csv(args.users, sep=';', encoding='utf-8')
            skip = False
            # Validate the dataframe
            if False in [True if c in df.columns else False for c in ['Author', 'First Language', 'Country', 'Certain']]:
                raise ValueError('The specified dataframe is not valid (i.e., not all required columns exist).')
        except:
            raise ValueError('Can not open the specified user dataset. Make sure you have specified the correct filename.')

    # Set to which series each article belongs
    try:
        cursor.execute('''ALTER TABLE articles ADD COLUMN series INTEGER''')
    except:
        pass
    
    parents = cursor.execute('''SELECT id, title FROM articles WHERE parent_id = 0''').fetchall()
    
    for i, parent in enumerate(parents, 1):
        
        identifier = []
        identifier.append(parent[0])
        
        children = cursor.execute('''SELECT id FROM articles WHERE parent_id = ?''', (parent[0],)).fetchall()

        for child in children:        
            identifier.append(child[0])
        
        cursor.execute('''UPDATE articles SET series = ? WHERE (id BETWEEN ? AND ?)''', ((i), identifier[0], identifier[-1],))
        
    # Add nationality from the user dataset to the authors table
    try:
        cursor.execute('''ALTER TABLE authors ADD COLUMN usertype STRING''')
    except:
        pass
    
    try:
        cursor.execute('''ALTER TABLE authors ADD COLUMN flag BOOLEAN''')
    except:
        pass
    
    try:
        cursor.execute('''ALTER TABLE authors ADD COLUMN iso STRING''')
    except:
        pass
    
    if skip is True:
        print('Skipping user data because no user type is specified.')
    else:
        if isinstance(df, pd.DataFrame):      
            for index, row in df.iterrows():
                cursor.execute('''
                UPDATE authors 
                SET language = ?, country = ?, usertype = 'registered', flag = ? 
                WHERE name = ?
                ''', (row['First Language'], row['Country'], math.floor(row['Certain']), row['Author'], ))
            
            print('Updated %d registered users' % (len(df)))
        
        else:        
            users = cursor.execute('''SELECT name FROM authors''').fetchall()        
            for user in users:
                cursor.execute('''
                UPDATE authors 
                SET country = ?, usertype = 'anonymous', flag = 1, iso = ? 
                WHERE name = ?
                ''', (df.country(user[0]).country.name , df.country(user[0]).country.iso_code, user[0],))
            
            print('Updated %d anonymous users' % (len(users)))
    
    # Filter all edits which are not in the revision (i.e., metadata)
    try:
        cursor.execute('''ALTER TABLE edits ADD COLUMN flag BOOLEAN''')
    except:
        pass
    
    cursor.execute('''UPDATE edits SET flag = 0''')    
    cursor.execute('''SELECT DISTINCT edits.id, edits.updated_text, revisions.content FROM edits INNER JOIN revisions ON revisions.id = edits.revision_id''')
    
    rows = cursor.fetchall()

    for row in rows:
        
        valid = False
        
        # No filter
        if args.filter is 1:
        
            if row[1] in row[2]:
                if row[1].isspace() is not True and len(row[1]) > 1:    
                    valid = True
        
        else: 
            samples = textwrap.wrap(row[1], math.ceil(len(row[1])/args.filter))
            minimum = 0
            
            # Check of each sample is in the revision text
            for sample in samples:
                if sample in row[2]:
                    minimum += 1
                    
            # If more than half of the samples are in the revisions it is valid
            if minimum >= (args.filter/2):
                if row[1].isspace() is not True and len(row[1]) > 1:    
                    valid = True
                
        if valid is True:        
            cursor.execute('''UPDATE edits SET flag = 1 WHERE id = ?''', (row[0],))
            
            
    cursor.execute('''SELECT COUNT(*) FROM edits WHERE flag = 1''')
    print('Updated %d valid edits' % (len(rows)))
    db.commit()
    db.close()    
    
if __name__ == "__main__": 
   main() 
