# -*- coding: utf-8 -*-
"""
Created on Wed Mar  6 11:27:40 2019

@author: jdevreeze
"""

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from tqdm import tqdm

import pandas as pd
import os

from config import similarity

def getCosineSimilarity(*strs, method='tfidf'):
    if method is 'tfidf':
        vectors = [t for t in getTfidfVectors(*strs)]
    else:
        vectors = [t for t in getVectors(*strs)]
    return cosine_similarity(vectors)
    
def getVectors(*strs):
    text = [t for t in strs]
    vectorizer = CountVectorizer(text)
    vectorizer.fit(text)
    return vectorizer.transform(text).toarray()

def getTfidfVectors(*strs):
    text = [t for t in strs]
    vectorizer = TfidfVectorizer(text)
    vectorizer.fit(text)
    return vectorizer.transform(text).toarray()

"""
Execute the main text comparison process.
"""
if __name__ == "__main__":    
        
    tokens = [
        df['CurrentEdit'][68],
        df['PreviousEdit'][68],
        df['CurrentEdit'][358],
        df['PreviousEdit'][358]
    ]
    
    print(getCosineSimilarity(tokens[0], tokens[1], method='tf')[0,1])
    print(getCosineSimilarity(tokens[0], tokens[1], method='tfidf')[0,1])