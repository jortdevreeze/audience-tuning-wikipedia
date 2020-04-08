# -*- coding: utf-8 -*-
"""
Created on Wed Jan 29 16:01:30 2020

@author: jdevreeze
"""

import json
import gensim
import re
import os.path
import argparse
import warnings

import pandas as pd

from tqdm import tqdm
from datetime import datetime
from itertools import combinations, product

from nltk.tokenize import word_tokenize

from gensim.matutils import softcossim 
from gensim import corpora

from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer


class Similarity:
    
    _stopwords = []
    
    def __init__(self, language, stopwords):
        if stopwords is not None and language in stopwords.keys():
            self._stopwords = stopwords[language]
     
    def jaccard_similarity(self, str1, str2): 
        a = set(str1.split()) 
        b = set(str2.split())
        c = a.intersection(b)
        return float(len(c)) / (len(a) + len(b) - len(c))
    
    def vectorize(self, *strs):
        text = [t for t in strs]
        vectorizer = CountVectorizer(text)
        vectorizer.fit(text)
        return vectorizer.transform(text).toarray()
    
    def tfidf_vectors(self, *strs):
        text = [t for t in strs]
        vectorizer = TfidfVectorizer(text)
        vectorizer.fit(text)
        return vectorizer.transform(text).toarray()
    
    def tokenize_and_filter(self, string): 
        words = word_tokenize(string)        
        words = [w for w in words if w.isalpha()]
        words = [w for w in words if not w in self._stopwords]
        return words
    
    def cosine(self, *strs, method='tfidf'):
        if method is 'tfidf':
            vectors = [t for t in self.tfidf_vectors(' '.join(strs[0]), ' '.join(strs[1]))] 
        else:
            vectors = [t for t in self.vectorize(' '.join(strs[0]), ' '.join(strs[1]))]
        return cosine_similarity(vectors)[0,1]
    
    def soft_cosine(self, *strs, model):
        dictionary =  corpora.Dictionary([strs[0], strs[1]])
        s_matrix = model.similarity_matrix(dictionary, tfidf=None, threshold=0.0, exponent=2.0, nonzero_limit=100) # Default paramaters (see https://radimrehurek.com/gensim/models/keyedvectors.html)
        return softcossim(dictionary.doc2bow(strs[0]), dictionary.doc2bow(strs[1]), s_matrix)
    
    def word_embeddings(self, words, model):
        vocab = model.vocab 
        return [w for w in words if w in vocab]
    
    def embeddings_similarity(self, *strs, model):
        s1words = self.word_embeddings(strs[0], model)
        s2words = self.word_embeddings(strs[1], model)    
        if not s1words or not s2words:
            return None
        return model.n_similarity(s1words, s2words)
    
    def embeddings_distance(self, *strs, model):
        s1words = self.word_embeddings(strs[0], model)
        s2words = self.word_embeddings(strs[1], model)    
        if not s1words or not s2words:
            return None
        return model.wmdistance(s1words, s2words)


def process_document(doc): 
    if type(doc) is str:
        if '#VALUE' in doc:
            return None
        return re.findall(r'>(.+?)<', doc)[0]                  
    else:
        return None
    
def save_output(df, name): 
    if df is not False:             
        try:
            df.to_csv(name, sep=';', encoding='utf-8', index=False)
        except:
            raise ValueError('Unable to save the data as an CSV format.')
    else:
        raise ValueError('Unable to save the dataset, because it is empty.')

def main():

    metrics = [
        'tf',
        'tfidf',
        'soft_cosine',
        'embeddings'
    ]
    
    parser = argparse.ArgumentParser(description='Create a dataset with text similarities.') 
    
    parser.add_argument('--input', metavar='input', type=str, required=True, help='Opens a csv file from the specified path.')
    parser.add_argument('--output', metavar='output', type=str, required=True, help='Stores the similarity data to the specified path.')
    parser.add_argument('--strict', action='store_true', help='Specify if similarities should only be calculated when there are 2-combinations for both nationalities.')
    parser.add_argument('--metrics', metavar='metrics', nargs='*', type=str, default=False, help='Specify which metrics should be used (tf, tfidf, soft_cosine, embeddings).')
    parser.add_argument('--blacklist', metavar='blacklist', nargs='*', type=str, default=False, help='A list with languages to exclude from the input data.')
    parser.add_argument('--whitelist', metavar='whitelist', nargs='*', type=str, default=False, help='A list with languages to include from the input data. Note that this overrides a blacklist.')
    parser.add_argument('--resume', metavar='resume', type=str, default=False, help='Continue the calculation of text similarity from the specified language.')
    
    args = parser.parse_args()
    
    try:
        data = pd.read_csv(args.input, sep=';', encoding='utf-8')
    except:
        raise ValueError('Can not open the specified dataset.')
    
    df = data
    
    if args.blacklist is not False: 
        df = data[~data.Language.isin(args.blacklist)]
    
    if args.whitelist is not False: 
        df = data[data.Language.isin(args.whitelist)]

    # Overwrite the existing variable to suppress the inplace copy warning
    df = df.sort_values('Language')
    
    output = False

    # Open the stopwords dictionary
    try:
        with open('../data/stopwords-iso.json', encoding='utf-8') as file:
            stopwords = json.load(file)
    except:
        raise ValueError('Can not load the specified stopwords dictionary. You must provide a valid json dictionary.')

    # Check which metrics to use
    if args.metrics is not False:
        idx = [metrics.index(x) for x in set(args.metrics).intersection(metrics)]
        if len(idx) is 0:
            raise ValueError('You must specify a valid metric to calculate similarity.')
    else:
        idx = list(range(4))

    # Open a previously saved output file and continue calculation
    if args.resume is not False:        
        if os.path.isfile(args.output):
            output = pd.read_csv(args.output, sep=';', encoding='utf-8')
        else:
            raise ValueError('Unable to resume the process, because the specified output dataset does not exists.')        
        index = df[df.Language == args.resume].index.tolist()        
        if index:
            df = df[df.index >= index[0]]
    
    languages = df.Language.unique()
    
    # Print an overview of all available languages in the dataset
    print('There are %d unique languages in the dataset:' % (len(languages)))
    for language in languages:
        print('%s%s' % (' ' * 2, language))
    
    for language in languages:
        
        # Sort the dataset by language in order to reduce unnecesary loading of the word vectors
        print('%s: Calculating similarity for language "%s":' % (datetime.strftime(datetime.now(), '%Y-%m-%d | %H:%M:%S'), language))
        
        # Open a saved dataset to allow autosaving
        if output is not False:
            output = pd.read_csv(args.output, sep=';', encoding='utf-8')
        
        subset = df[(df.Language == language)]
        
        # Check if we need to load the Fasttext model
        flag = False
        if any(x >= 2 for x in idx):
            if args.strict is True:
                for article in subset.Series.unique():
                    flag = True if len(subset[(subset.Series == article)].Tongue.unique()) > 1 else False
                    if flag is True:
                        break
            else:
                flag = True

        # Load the Fasttext model
        if flag is True:
            try:   
                model = gensim.models.fasttext.load_facebook_vectors('../models/cc.{}.300.bin.gz'.format(language))
                print('%s: Finished loading the pre-trained word vectors' % (datetime.strftime(datetime.now(), '%Y-%m-%d | %H:%M:%S')))
            except:
                raise ValueError('Can not load the pre-trained word vectors for language: "%s". You must provide a valid Fasttext model.' % (language))

        similarity = Similarity(language, stopwords)  
        
        for article in subset.Series.unique():

            tongue = subset[(subset.Series == article)].Tongue.unique()

            if len(tongue) >= 1:
            
                print('%sProcessing the article "%s"' % (' ' * 2, subset[(subset.Series == article)].ParentTitle.iloc[0]))
                print('%sCalculating within similarities:' % (' ' * 4))
                
                for t in tongue:
                    
                    print('%s%s' % (' ' * 6, t))
                    
                    edits = subset[(subset.Series == article) & (subset.Tongue == t)]
                    edits = edits[['CurrentEdit', 'EditId']]
        
                    edits['CurrentEdit'] = edits['CurrentEdit'].apply(process_document)
                    edits = edits.dropna()
                    
                    pairs = list(combinations(edits['CurrentEdit'], 2))
                    
                    print('%sThere are %d k-combinations (k=2).' % (' ' * 8, len(pairs)))
                    
                    if len(pairs) > 0:
                    
                        a, b, c, d = [], [], [], []
                        
                        for pair in tqdm(pairs):
                            
                            w1 = similarity.tokenize_and_filter(pair[0])
                            w2 = similarity.tokenize_and_filter(pair[1])

                            if 0 in idx: a.append(similarity.cosine(w1, w2, method='tf'))
                            if 1 in idx: b.append(similarity.cosine(w1, w2, method='tfidf'))
                            if 2 in idx: c.append(similarity.soft_cosine(w1, w2, model=model))
                            if 3 in idx: d.append(similarity.embeddings_similarity(w1, w2, model=model))
                        
                        row = {'article' : [article], 'language' : [language], 'tongue' : [t], 'factor' : 0, 'tf' : [a], 'tfidf' : [b], 'soft_cosine' : [c], 'embeddings' : [d]}
                        
                        if output is False:
                            output = pd.DataFrame(row)
                        else:
                            output = output.append(pd.DataFrame(row), ignore_index=True)
                    
                if len(tongue) == 2:

                    print('%sCalculating between similarities:' % (' ' * 4))
                    
                    print('%s%s-%s' % (' ' * 6, tongue[0], tongue[1]))
                    
                    left = subset[(subset.Series == article) & (subset.Tongue == t)]
                    left = left[['CurrentEdit', 'EditId']]
        
                    left['CurrentEdit'] = left['CurrentEdit'].apply(process_document)
                    left = left.dropna()   
                    
                    right = subset[(subset.Series == article) & (subset.Tongue != t)]
                    right = right[['CurrentEdit', 'EditId']]
        
                    right['CurrentEdit'] = right['CurrentEdit'].apply(process_document)
                    right = right.dropna()
        
                    pairs = list(product(left['CurrentEdit'], right['CurrentEdit']))
                    
                    print('%sThe Cartesian product between both sets are equal to %d.' % (' ' * 8, len(pairs)))
                    
                    if len(pairs) > 0:
                    
                        a, b, c, d = [], [], [], []

                        for pair in tqdm(pairs):
                    
                            w1 = similarity.tokenize_and_filter(pair[0])
                            w2 = similarity.tokenize_and_filter(pair[1])
                            
                            if 0 in idx: a.append(similarity.cosine(w1, w2, method='tf'))
                            if 1 in idx: b.append(similarity.cosine(w1, w2, method='tfidf'))
                            if 2 in idx: c.append(similarity.soft_cosine(w1, w2, model=model))
                            if 3 in idx: d.append(similarity.embeddings_similarity(w1, w2, model=model))

                        row = {'article' : [article], 'language' : [language], 'tongue' : [t], 'factor' : 1, 'tf' : [a], 'tfidf' : [b], 'soft_cosine' : [c], 'embeddings' : [d]}

                        if output is False:
                            output = pd.DataFrame(row)
                        else:
                            output = output.append(pd.DataFrame(row), ignore_index=True)

                else:
                    print('%sCan not calculate between similarities. Only one tongue available.' % (' ' * 4))

                
        # Autosave after each language
        if output is not False:
            print('%s: Saving the results for language "%s"' % (datetime.strftime(datetime.now(), '%Y-%m-%d | %H:%M:%S'), language))
            save_output(output, args.output)

if __name__ == "__main__": 
    main()
