# -*- coding: utf-8 -*-
"""
Created on Tue Jan 21 10:14:14 2020

@author: jdevreeze
"""

import sqlite3
import argparse
import pandas as pd

from datetime import datetime, timedelta
from dateutil.parser import parse
from babel import languages

def getJaccardSimilarity(str1, str2): 
    a = set(str1.split()) 
    b = set(str2.split())
    c = a.intersection(b)
    return float(len(c)) / (len(a) + len(b) - len(c))

def create_context(edit, text, length = 500, seperator = ['<b>', '</b>'], overlap = 90):
    """
    Wrap context around an edit made by a user. 
    
    Use this method to extract the preceding and following defined number of characters from the main 
    text. This method uses utf8 encoding, because otherwise Arabic, Hebrew, or Chinese texts won't be 
    handled properly.

    Args:
        edit: The actual edit made by the user
        text: The entire Wikipedia text in which the edit was made
        length: The number of characters that is required to create context (default: 500)
        seperator: A character to mark the beginning and end of the edit (default: ['<b>', '</b>'])
        overlap: The level of text overlap required in case a 100% match is not found (default: 90)
        
    Returns:
        A string with the context or None if there is no match.

    """
    split = text.rpartition(edit)
        
    # If there is no exact match between the edit and the text, try to find a closest match as possible
    if not split[1]:
        
        prefix = suffix = ''        
        edit_length = len(edit)

        for i in range(100, (100 - overlap), -1):            
            charlen = round(edit_length * ((i - 1) / 100))
            index = text.find(edit[:charlen])
            
            if charlen is 0:
                break

            # We have a match
            if index is not -1:
                split = text.rpartition(edit[:charlen])             
                prefix = split[0][-length:]
                break
        
        for i in range(0, overlap, 1):            
            charlen = round(edit_length * ((i + 1) / 100))
            index = text.find(edit[charlen:])
            
            if charlen is 0:
                break
            
            # We have a match
            if index is not -1:
                split = text.rpartition(edit[charlen:])                
                suffix = split[2][:length]
                break       

        if len(prefix) is 0 and len(suffix) is 0:
            return ''
    
    # We have a 100% match
    else:
        prefix = split[0][-length:]
        suffix = split[2][:length]
    
    # Remove the first and last word from the predefined character length of context
    prefix = ' '.join(prefix.split(' ')[1:])
    suffix = ' '.join(suffix.split(' ')[:-1]) 
    
    # Add an ellipsis before and after the context if there is any context available
    if len(prefix) is not 0:
        prefix = ''.join(['...', prefix])
    if len(suffix) is not 0:
        suffix = ''.join([suffix, '...'])       
    
    context = ''.join([prefix, ''.join([seperator[0], edit, seperator[1]]), suffix])

    return context

def main():
    
    parser = argparse.ArgumentParser(description='Create a dataset with all valid and pre-processed edits.') 
    
    parser.add_argument('--input', metavar='input', type=str, required=True, help='Opens a csv file from the specified path.')
    parser.add_argument('--output', metavar='output', type=str, required=True, help='Stores the extracted data to the specified path.')
    parser.add_argument('--google', action='store_true', help='Specify if a cell with Google translate should be created.')
    parser.add_argument('--date', metavar='date', type=str, default=None, help='The last date to include in the dataset (default None). The specified date should be in the "Y-m-d" format.')

    args = parser.parse_args()
       
    # Open the sqlite database
    db = sqlite3.connect(args.input)    
    cursor = db.cursor()

    date = datetime.now() if args.date is None else parse(args.date) + timedelta(hours=23, minutes=59, seconds=59) 
    
    # Validate the database
    for table in ['articles', 'revisions', 'edits', 'authors']:
        cursor.execute('''SELECT count(name) FROM sqlite_master WHERE type='table' AND name=?''', (table,))
        if cursor.fetchone()[0] != 1:
        	raise ValueError('The specified database is not valid (i.e., not all required tables exist).')
    
    cursor.execute('''
        SELECT DISTINCT
            authors.name AS author,
            authors.language AS tongue,
            authors.country AS country,
            authors.iso AS iso,
            articles.parent_id AS parent,
            articles.series AS series,
            articles.title AS title,
            articles.language AS language,
            revisions.id AS identifier,
            revisions.revision_id AS revision_id,
            revisions.timestamp AS timestamp,
            edits.id AS edit,
            edits.updated_text AS updated,
            edits.previous_text AS previous,
            edits.size AS size
        FROM
            articles
        INNER JOIN revisions ON revisions.article_id = articles.id
        INNER JOIN authors ON authors.id = revisions.author_id
        INNER JOIN edits ON edits.revision_id = revisions.id
        WHERE articles.flag = 1
            AND edits.flag = 1
            AND revisions.timestamp <= ?
        ORDER BY author
    ''', (date,))
    
    df = pd.DataFrame(cursor.fetchall())
    
    df.columns = [
        'Author', 
        'Tongue', 
        'Nationality', 
        'ISO', 
        'ParentID', 
        'Series', 
        'Title', 
        'Language', 
        'Identifier',
        'RevisionId',
        'Timestamp',
        'EditId', 
        'UpdatedText', 
        'PreviousText', 
        'Size'
    ]
    
    # Add two new columns to the dataframe for the edits
    df['ParentTitle'] = df['Type'] = df['CurrentEdit'] = df['PreviousEdit'] = df['Similarity'] = None
    
    # Iterate through all edits
    for index, row in df.iterrows():

        # Get the English title of the parent article
        if row['ParentID'] is not 0:
            parent_title = cursor.execute('''SELECT title FROM articles WHERE id = ?''', (row['ParentID'],)).fetchone()[0]
        else:
            parent_title = row['Title']
        
        df.at[index, 'ParentTitle'] = parent_title

        language = pd.DataFrame(
            cursor.execute('''SELECT language FROM articles WHERE series = ? AND flag = 1''', (row['Series'],)).fetchall()
        )
        
        if row['ISO'] is not None:
            tongue = languages.get_official_languages(row['ISO'], regional=False, de_facto=True)
        else:
            tongue = (row['Tongue'],)
        
        if len(language[language.iloc[:,0] == tongue[0]]) is not 0:            
            
            if len(row['UpdatedText']) is 0 and len(row['PreviousText']) is 0:
                edit_type = 0             
            if len(row['UpdatedText']) is not 0 and len(row['PreviousText']) is 0:
                edit_type = 1         
            if len(row['UpdatedText']) is not 0 and len(row['PreviousText']) is not 0:
                edit_type = 2         
            if len(row['UpdatedText']) is 0 and len(row['PreviousText']) is not 0:
                edit_type = 3    

            # Content is added (Create)
            if edit_type is 1:            
                revision = cursor.execute('''SELECT content FROM revisions WHERE id = ?''', (row['Identifier'],)).fetchone()[0]
                df.at[index, 'CurrentEdit'] = create_context(row['UpdatedText'], revision)
                df.at[index, 'Similarity'] = 0

            # Content is revised (Update)    
            if edit_type is 2:            
                revision = cursor.execute('''SELECT content, previous FROM revisions WHERE id = ?''', (row['Identifier'],)).fetchone()
                current_edit = create_context(row['UpdatedText'], revision[0])
                previous_edit = create_context(row['PreviousText'], revision[1])
                if len(current_edit) == 0 or len(previous_edit) == 0:
                    continue
                else:
                    df.at[index, 'CurrentEdit'] = current_edit
                    df.at[index, 'PreviousEdit'] = previous_edit
                    df.at[index, 'Similarity'] = getJaccardSimilarity(df.at[index, 'CurrentEdit'], df.at[index, 'PreviousEdit'])

            # Content is removed (Delete)  
            if edit_type is 3:
                revision = cursor.execute('''SELECT previous FROM revisions WHERE id = ?''', (row['Identifier'],)).fetchone()[0]
                df.at[index, 'PreviousEdit'] = create_context(row['PreviousText'], revision) 
                df.at[index, 'Similarity'] = 0
            
            df.at[index, 'Type'] = edit_type  

    df = df.drop('Identifier', 1)

    # Select only meaningfull edits
    selection = df[(df.CurrentEdit.notnull()) | (df.PreviousEdit.notnull())]
    selection = selection[(selection.Size > 2) & (selection.Similarity < 1)]

    # Select only edits that are made on both language versions
    exclude = []

    # Iterate through all conflicts
    for i in selection.Series.unique():
        conflict = selection[(selection.Series == i)]

        # Iterate through all authors within the current conflict
        for j in conflict.Author.unique():
            author = conflict[(conflict.Author == j)]

            # Select only the authors within this conflict that edited two language versions
            if len(author.Language.unique()) is not 2:
                for k in author.EditId:
                    exclude.append(k)
                
    # List of all edits in two languages made by one author
    excluded = selection.loc[~selection['EditId'].isin(exclude)]
    excluded = excluded[excluded.CurrentEdit.notna()]

    # Add a Google translate column
    if args.google is True:
        i = 2    
        for index, row in excluded.iterrows():
            if row['Language'] not in ['en', 'sco']:
                if row['CurrentEdit'] is not None:
                    excluded.at[index, 'Translate 1'] = '=GOOGLETRANSLATE(Q{}, "{}", "en")'.format(i, row['Language'])
                if row['PreviousEdit'] is not None:
                    excluded.at[index, 'Translate 2'] = '=GOOGLETRANSLATE(R{}, "{}", "en")'.format(i, row['Language'])
            i += 1
    
    if args.output.split('.')[-1] == 'xlsx':
        try:
            writer = pd.ExcelWriter(args.output)
            excluded.to_excel(writer,'Sheet1', index=False)
            writer.save()
        except:
            raise ValueError('Unable to save the data as an Excel format.')
    else:
        try:
            df.to_csv(args.output, sep=';', encoding='utf-8', index=False)
        except:
            raise ValueError('Unable to save the data as an CSV format.')
    
if __name__ == "__main__": 
   main() 
