# -*- coding: utf-8 -*-
"""
Created on Wed Jan  8 15:25:00 2020

@author: jdevreeze
"""

import pandas as pd

import geoip2.database

import re
import sqlite3
import argparse
import inspect
import time

from tqdm import tqdm
from datetime import datetime
from parsewiki import page

class Extract:
    
    _ignore = True
    _print_errors = True
    _force = False
    
    _db = None
    _wiki = None
    _geolocation = None    
    _item = None
    _parent = None
    
    _sleep = 0    
    
    _usertype = 'registered'
    
    def __init__(self, output=None, usertype=None, sleep=False, force=False, ignore=True):
        
        if usertype is not None:
            self._usertype = 'anonymous'
            self._geolocation = usertype
            
        if ignore is False:
            self._ignore = False
            
        if sleep is not False:
            self._sleep = sleep
            
        if force is not False:
            self._force = force
        
        try:
            
            # Create or open the sqlite database
            self._db = sqlite3.connect(output)    
            cursor = self._db.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS authors(
                    id INTEGER PRIMARY KEY, 
                    name TEXT,
                    language TEXT,
                    country TEXT)
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS articles(
                    id INTEGER PRIMARY KEY, 
                    parent_id INTEGER,
                    title TEXT, 
                    language TEXT,
                    timestamp DATETIME,
                    flag BOOLEAN)
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS revisions(
                    id INTEGER PRIMARY KEY, 
                    article_id INTEGER, 
                    author_id INTEGER, 
                    revision_id INTEGER,
                    previous_id INTEGER,
                    timestamp DATETIME,
                    content TEXT,
                    previous TEXT,
                    paragraphs INTEGER)
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS edits(
                    id INTEGER PRIMARY KEY,
                    revision_id INTEGER,
                    updated_text TEXT,
                    previous_text TEXT,
                    size INTEGER)
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS errors(
                    id INTEGER PRIMARY KEY, 
                    article_id INTEGER, 
                    author_id INTEGER, 
                    revision_id INTEGER,
                    language TEXT,
                    current BOOLEAN)
            ''')
                
            self._db.commit()

        except:                   
            self.__error(self.__line_no(), 'The database cannot be created.', None)
            pass

    
    def close_sqlite(self):
        self._db.close()
        
    def extract_wiki(self, item=None):
        
        if item is not None:
            
            wiki = page.Parse(item.title, lang=item.main)
            wiki._print_errors = False
            wiki.extract()
            
            if item.main is not item.lang1:
                wiki.extract(lang=item.lang1)
            if item.main is not item.lang2:
                wiki.extract(lang=item.lang2)
             
            self._item = item
            self._wiki = wiki
        
        else:
            self.__error(self.__line_no(), 'A valid Wikipedia record must be provided.', None)
    
    def extract_users(self):
    
        wiki = self._wiki
        item = self._item
        
        users = []
        
        if wiki.get_page(lang=item.lang1) is not False and wiki.get_page(lang=item.lang2) is not False:
            
            # Extract all users that contributed to both language versions            
            wiki.extract_users(lang=item.lang1)
            wiki.extract_users(lang=item.lang2)

            users_first = wiki.get_users(lang=item.lang1, whom=self._usertype)
            users_second = wiki.get_users(lang=item.lang2, whom=self._usertype)
            
            users_first = set(users_first)
            users_second = set(users_second)
            
            if self._geolocation is not None:
                
                for name in users_first.intersection(users_second):            
                    
                    nation1 = item.country1.split('|')
                    nation2 = item.country2.split('|')                
                    geo = self._geolocation.country(name).country.name                
                    
                    if geo in nation1 or geo in nation2:
                        users.append(name)
            else:
                
                for name in users_first.intersection(users_second):
                    if not re.search('bot', name, re.IGNORECASE) and not re.search('CommonsDelinker', name, re.IGNORECASE):
                        users.append(name)
                        
        return users
    
    def extract_page(self):

        wiki = self._wiki
        item = self._item
        
        cursor = self._db.cursor()
        
        # Check whether the requested tile has already been saved in the DB
        cursor.execute('''SELECT * FROM articles WHERE title=?''', (item.title.replace('_', ' '),))        
        
        result = cursor.fetchone()      
        
        if result is not None:
            
            parent = result[0]
            
            if self._force is False:
                replace = self.query_yes_no('The current page already exists in the database. Do you want to replace it?')
            else:
                replace = True if self._force is 'replace' else False                

            if replace:

                cursor.execute('''UPDATE articles SET timestamp = ? WHERE id = ?''', (wiki.get_date(lang=item.main), parent,))
                    
                if item.main not in item.lang1:                
                    cursor.execute('''UPDATE articles SET timestamp = ? WHERE parent_id = ?''', (wiki.get_date(lang=item.lang1), parent,))
                    
                if item.main not in item.lang2:    
                    cursor.execute('''UPDATE articles SET timestamp = ? WHERE parent_id = ?''', (wiki.get_date(lang=item.lang2), parent,))

        else:
            
            if item.main not in [item.lang1, item.lang2]:
                first = 0
            else:
                first = 1
                
            article = {
                'parent_id' : 0,
                'title' : wiki.get_title(lang=item.main),
                'language' : item.main,
                'timestamp' : wiki.get_date(lang=item.main),
                'flag' : first
            }
            
            cursor.execute('''INSERT INTO articles(parent_id, title, language, timestamp, flag) VALUES(:parent_id, :title, :language, :timestamp, :flag)''', article)        
            cursor.execute('''SELECT COUNT(*) FROM articles''')
            
            result = cursor.fetchone()
            parent = result[0]        
        
            if item.main not in item.lang1:
                
                article = {
                    'parent_id' : parent,
                    'title' : wiki.get_title(lang=item.lang1),
                    'language' : item.lang1,
                    'timestamp' : wiki.get_date(lang=item.lang1),
                    'flag' : 1
                }
                
                cursor.execute('''INSERT INTO articles(parent_id, title, language, timestamp, flag) VALUES(:parent_id, :title, :language, :timestamp, :flag)''', article)
                
            if item.main not in item.lang2:
    
                article = {
                    'parent_id' : parent,
                    'title' : wiki.get_title(lang=item.lang2),
                    'language' : item.lang2,
                    'timestamp' : wiki.get_date(lang=item.lang2),
                    'flag' : 1
                }
                
                cursor.execute('''INSERT INTO articles(parent_id, title, language, timestamp, flag) VALUES(:parent_id, :title, :language, :timestamp, :flag)''', article)
        
        self._parent = parent
        self._db.commit()
        
    def extract_edits(self, user, lang, indent=0):

        wiki = self._wiki
        item = self._item
        
        cursor = self._db.cursor()

        # Check whether the user has already been saved in the DB
        cursor.execute('''SELECT * FROM authors WHERE name=?''', (user,))

        if cursor.fetchone() is None:                    
            cursor.execute('''INSERT INTO authors(name, language, country) VALUES(?, ?, ?)''', (user, None, None))
            
        cursor.execute('''SELECT id FROM authors WHERE name=?''', (user,))                
        author_id = cursor.fetchone()[0]
        
        # Delay the data extraction so the MediaWiki server doesn't get overloaded
        time.sleep(self._sleep)
        
        # Extract revisions for the first language 
        wiki.extract_revisions_by_user(lang=lang, username=user)            
        identifiers = wiki.get_pageid(lang=lang, user=user)
        
        # Output the total amount of edits for this language version
        print('%sExtracted %d revisions(s) for language code \'%s\':' % (' ' * indent, len(identifiers), lang))
        
        for i, identifier in enumerate(identifiers, 1):
            
            # Output the revision
            print('%sRevision %d of %d: %s' % (' ' * (indent + 2), i, len(identifiers), identifier))
            
            # Check whether the revision has already been saved in the DB
            cursor.execute('''SELECT * FROM revisions WHERE revision_id=?''', (identifier,))
            
            result = cursor.fetchone()
            
            if result is not None:
                
                if self._force is False:
                    replace = self.query_yes_no('The current revision is already saved in the database. Do you want to replace it?')
                else:
                    replace = True if self._force is 'replace' else False 

                if replace:                
                    revids = cursor.execute('''SELECT id FROM revisions WHERE revision_id=?''', (identifier,)).fetchall()                    
                    for revid in revids:                        
                        cursor.execute('''DELETE FROM edits WHERE revision_id = ? ''', (revid[0],))                    
                    cursor.execute('''DELETE FROM revisions WHERE revision_id = ? ''', (identifier,))                  
                
            if result is None or replace is True:
            
                # Extract metadata
                timestamp = wiki.get_date(lang=lang, revid=identifier)
                previous_id = wiki.get_previous(lang=lang, revid=identifier)  
                
                if previous_id is 0:                        
                    previous = ''                   
                else:
                    wiki.extract_revision(lang=lang, revid=previous_id)
                    
                    if wiki.has_content(lang=lang, revid=previous_id) is True:                                
                        previous = wiki.get_text(lang=lang, revid=previous_id, references=False, headers=True)
                    else:
                        previous = ''
                        cursor.execute('''INSERT INTO errors(article_id, author_id, revision_id, language, current) VALUES(?,?,?,?,?)''', (self._parent, author_id, previous_id, lang, False))
                        
                if wiki.has_content(lang=lang, revid=identifier) is True:                                
                    content = wiki.get_text(lang=lang, revid=identifier, references=False, headers=True)
                else:
                    content = ''
                    cursor.execute('''INSERT INTO errors(article_id, author_id, revision_id, language, current) VALUES(?,?,?,?,?)''', (self._parent, author_id, identifier, lang, True))
                
                if item.main not in lang:
                    cursor.execute('''SELECT * FROM articles WHERE parent_id = ? AND language = ?''', (self._parent, lang,))
                else:
                    cursor.execute('''SELECT * FROM articles WHERE id = ? AND language = ?''', (self._parent, lang,))
                    
                parent_id = cursor.fetchone()[0]

                revision = {
                    'article_id' : parent_id, 
                    'author_id' : author_id, 
                    'revision_id' : identifier, 
                    'previous_id' : previous_id, 
                    'timestamp' : timestamp, 
                    'content' : content, 
                    'previous' : previous, 
                    'paragraphs' : None                        
                }
                
                cursor.execute('''INSERT INTO revisions(article_id, author_id, revision_id, previous_id, timestamp, content, previous, paragraphs) 
                                  VALUES(:article_id, :author_id, :revision_id, :previous_id, :timestamp, :content, :previous, :paragraphs)''', revision)                        
                
                cursor.execute('''SELECT id FROM revisions WHERE revision_id=?''', (identifier,))
            
                revision_id = cursor.fetchone()[0]
                
                # Extract all the edits done by the user on this revision
                differences, original = wiki.get_differences(lang=lang, revid=identifier, compare=True)
                
                if not differences:
                    pass
                    
                for (d,o) in zip(differences, original):                    
                    edit = {
                       'revision_id' : revision_id, 
                       'updated_text' : d, 
                       'previous_text' : o, 
                       'size' : len(d.encode('utf-8'))
                    }
                    cursor.execute('''INSERT INTO edits(revision_id, updated_text, previous_text, size) VALUES(:revision_id, :updated_text, :previous_text, :size)''', edit)                        
                
        self._db.commit()
    
    def query_yes_no(self, question, default=True):
        """
        Ask a yes/no question via standard input and return the answer.

        If invalid input is given, the user will be asked until
        they acutally give valid input.
    
        Args:
            question(str):
                A question that is presented to the user.
            default(bool|None):
                The default value when enter is pressed with no value.
                When None, there is no default value and the query
                will loop.
        Returns:
            A bool indicating whether user has entered yes or no.
        """
        
        default_dict = {
            None:  '[y/n]',
            True:  '[Y/n]',
            False: '[y/N]',
        }
    
        default_str = default_dict[default]
        prompt_str = '%s %s ' % (question, default_str)
    
        while True:
            
            print(prompt_str)
            choice = input().lower()
            
            if not choice and default is not None:
                return default
            if choice in ['yes', 'y']:
                return True
            if choice in ['no', 'n']:
                return False
    
            notification_str = 'Please respond with \'y\' or \'n\''
            print(notification_str)
                        
    def __line_no(self):
        """
        Internal method to get the current line number.
        
        Returns:
            An integer with the current line number.
        """
        
        return inspect.currentframe().f_back.f_lineno
        
    def __error(self, line, error, etype):
        """
        Internal method to handle errors.    
        
        Args:
            line: An integer with the current line number
            error: A string with the error message.
            etype: A string with the error type
        """

        if self._print_errors is True:
            print('Line: %s - %s' % (line, error))
            
        self._log.append((datetime.strftime(datetime.now(), '%Y-%m-%dT%H:%M:%S%Z'), line, error, etype))
        
        if self._ignore is False:
            raise ValueError(error)
  
def main():
    
    parser = argparse.ArgumentParser(description='Extract Wikipedia edits made by all users on two language versions of an article.') 
    
    parser.add_argument('--input', metavar='input', type=str, required=True, help='Opens a csv file from the specified path.')
    parser.add_argument('--output', metavar='output', type=str, required=True, help='Stores the extracted data to a sqlite database in the specified path.')
    parser.add_argument('--usertype', choices=['registered', 'anonymous'], default='registered', help='Type of user to extract edits from (default: registered).')
    parser.add_argument('--blacklist', metavar='blacklist', nargs='*', type=str, default=False, help='A list with titles to exclude from the input data.')
    parser.add_argument('--whitelist', metavar='whitelist', nargs='*', type=str, default=False, help='A list with titles to include from the input data. Note that this overrides a blacklist.')
    parser.add_argument('--sleep', metavar='sleep', type=int, default=0, help='Set a delay for the extraction process so the MediaWiki API does not get overloaded.')
    parser.add_argument('--force', metavar='force', choices=['replace', 'keep'], default=False, help='Automatically replace or keep saved items.')
    parser.add_argument('--resume', metavar='resume', type=str, default=False, help='Continue the extraction process from the specified article name.')

    args = parser.parse_args()
    
    # Open the dataset
    data = pd.read_csv(args.input, sep=',', encoding='utf-8')
    
    df = data

    if args.blacklist is not False: 
        df = data[~data.title.isin(args.blacklist)]
    
    if args.whitelist is not False: 
        df = data[data.title.isin(args.whitelist)]
    
    data.drop_duplicates(subset="title", keep='first', inplace=True) 
    
    try:            
        usertype = None if args.usertype == 'registered' else geoip2.database.Reader('../models/GeoLite2-Country.mmdb') 
    except:
        raise ValueError('Can not open a valid GeoLite2 Country model. Make sure you have specified the correct filename.')
    
    if args.resume is not False:
        index = df[df.title == args.resume].index.tolist()
        if index:
            df = df[df.index >= index[0]]
    
    # Start the extraction process
    extract = Extract(args.output, usertype, args.sleep, args.force)
    
    for index, row in tqdm(df.iterrows(), total=df.shape[0]):
    
        # Output the current title which is being processed
        print('\n%s: %s' % (datetime.strftime(datetime.now(), '%Y-%m-%d | %H:%M:%S'), row.title.replace('_', ' ')))
        
        extract.extract_wiki(row)
        users = extract.extract_users()

        if users:

            extract.extract_page()            
            
            # Output the total amount of users
            print('  Extracted %d %s user(s):' % (len(users), args.usertype))
            
            for i, user in enumerate(users, 1):
                
                # Output the current user which is being processed
                print('    User %d of %d: %s' % (i, len(users), user))
                
                extract.extract_edits(user, row.lang1, 6)
                extract.extract_edits(user, row.lang2, 6)  
                
    # Close the sqlite database
    extract.close_sqlite()

if __name__ == "__main__": 
   main() 
