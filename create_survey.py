# -*- coding: utf-8 -*-
"""
Created on Thu Mar  7 12:22:05 2019

@author: jdevreeze
"""

from tqdm import tqdm

import os
import pandas as pd

from config import common, survey

def createQuestions(row, edit):
    
    questions = []
    
    nation1 = survey.countryNames[row[common.parentTitle]][0]
    nation2 = survey.countryNames[row[common.parentTitle]][1]
    
    # The translation of the article
    questions.append('[[Question:TE:Essay]]\n')
    questions.append('[[ID:translation_{}_{}]]\n'.format(edit, row[common.editId]))
    questions.append('Please translate the text above and write down the translation in this text-box.\n')
    questions.append('\n')
    
    # The translation of the actual edit displayed in bold
    questions.append('[[Question:TE:Essay]]\n')
    questions.append('[[ID:translation_{}_edit_{}]]\n'.format(edit, row[common.editId]))
    questions.append('Please place the translation which is displayed in bold in this text-box. Note that you can copy part of the translation from above in here.\n')
    questions.append('\n')
    
    # Ask quetions about bias
    questions.append('[[Question:MC:SingleAnswer:Horizontal]]\n')
    questions.append('[[ID:prefer_{}_{}]]\n'.format(edit, row[common.editId]))
    questions.append('When comparing both parties described in the text directly, do you get the impression that the text highlighted in bold prefers one of the two parties?\n')
    questions.append('[[Choices]]\n')
    
    questions.append('{}\n'.format(nation1))
    questions.append('2\n')
    questions.append('3\n')
    questions.append('4\n') 
    questions.append('none of the parties\n') 
    questions.append('6\n')
    questions.append('7\n')
    questions.append('8\n')
    questions.append('{}\n'.format(nation2))
    questions.append('\n')
    
    questions.append('[[Question:MC:SingleAnswer:Horizontal]]\n')
    questions.append('[[ID:perspective_{}_{}]]\n'.format(edit, row[common.editId]))
    questions.append('Do you have the impression that the perspective of one of the two parties is neglected (i.e., not sufficiently elaborated on) in this text highlighted in bold?\n')
    questions.append('[[Choices]]\n')
    
    questions.append('perspective of {} is neglected\n'.format(nation1))
    questions.append('2\n')
    questions.append('3\n')
    questions.append('4\n') 
    questions.append('balanced elaboration\n') 
    questions.append('6\n')
    questions.append('7\n')
    questions.append('8\n')
    questions.append('perspective of {} is neglected\n'.format(nation2))
    questions.append('\n')    
                
    questions.append('[[Question:Matrix]]\n')
    questions.append('[[ID:valence_{}_{}]]\n'.format(edit, row[common.editId]))
    questions.append('How positively or negatively is each of the conflicting parties presented?\n')
    questions.append('[[Choices]]\n')
    
    questions.append('{}\n'.format(nation1))
    questions.append('{}\n'.format(nation2))
    
    questions.append('[[AdvancedAnswers]]\n')
    questions.append('[[Answer]]\n')
    questions.append('very negatively\n')
    questions.append('[[Answer]]\n')
    questions.append('2\n')
    questions.append('[[Answer]]\n')
    questions.append('3\n')
    questions.append('[[Answer]]\n')
    questions.append('4\n')
    questions.append('[[Answer]]\n')
    questions.append('neutral\n')
    questions.append('[[Answer]]\n')
    questions.append('6\n')
    questions.append('[[Answer]]\n')
    questions.append('7\n')
    questions.append('[[Answer]]\n')
    questions.append('8\n')
    questions.append('[[Answer]]\n')
    questions.append('very positively\n')
    questions.append('\n')   

    questions.append('[[Question:Matrix]]\n')
    questions.append('[[ID:valence_{}_{}]]\n'.format(edit, row[common.editId]))
    questions.append('Does the text present one of the two parties as more responsible?\n')
    questions.append('[[Choices]]\n')
    
    questions.append('{}\n'.format(nation1))
    questions.append('{}\n'.format(nation2))
    
    questions.append('[[AdvancedAnswers]]\n')
    questions.append('[[Answer]]\n')
    questions.append('not at all responsible\n')
    questions.append('[[Answer]]\n')
    questions.append('2\n')
    questions.append('[[Answer]]\n')
    questions.append('3\n')
    questions.append('[[Answer]]\n')
    questions.append('4\n')
    questions.append('[[Answer]]\n')
    questions.append('neutral\n')
    questions.append('[[Answer]]\n')
    questions.append('6\n')
    questions.append('[[Answer]]\n')
    questions.append('7\n')
    questions.append('[[Answer]]\n')
    questions.append('8\n')
    questions.append('[[Answer]]\n')
    questions.append('very responsible\n')
    questions.append('\n')            
        
    return questions

def addToSurvey(question, language, stype, size):
    
    if not os.path.exists(survey.exportPath):
         os.mkdir(survey.exportPath)
    
    fileName = '{}/{}_{}_{}.txt'.format(survey.exportPath, language, stype, size)
    
    if os.path.isfile(fileName) is False:        
        question.insert(0, '\n')
        question.insert(0, '[[AdvancedFormat]]')
    
    file = open(fileName, 'a', encoding='utf-8')
    file.write(''.join(question))
    file.close()

"""
Execute the main survey generation process.
"""
if __name__ == "__main__":
        
    # Set the current working directory
    os.chdir(common.pathName)         
        
    # Open the dataset with all edits for translation
    df = pd.read_csv(common.fileName, sep=';', encoding='utf-8')
    
    split1 = df[common.currentEdit].str.len().quantile(.33)
    split2 = df[common.currentEdit].str.len().quantile(.66)
    
    split3 = df[common.previousEdit].str.len().quantile(.33)
    split4 = df[common.previousEdit].str.len().quantile(.66)
    
    languages = pd.Series([1] * df[common.languageCode].describe()['unique'], index=df[common.languageCode].unique()) 
        
    # Iterate through all edits and add elements to the surveys
    for index, row in tqdm(df.iterrows(), total=df.shape[0]):

        i = languages[row[common.languageCode]]        
        size1 = size2 = 0
        
        # determine size of current edit
        if type(row[common.currentEdit]) is str:
            current_size = len(row[common.currentEdit])                        
            if current_size <= split1:
                size1 = 1 
            elif current_size > split1 and current_size < split2:
                size1 = 2
            elif current_size >= split2:
                size1 = 3
        
        # determine size of previous edit
        if type(row[common.previousEdit]) is str:            
            previous_size = len(row[common.previousEdit])
            
            if previous_size <= split3:
                size2 = 1 
            elif previous_size > split3 and previous_size < split4:
                size2 = 2
            elif previous_size >= split4:
                size2 = 3
        
        size = size1 + size2  
        
        # Determine to which survey type we should be writing       
        if type(row[common.previousEdit]) is str and type(row[common.currentEdit]) is str:             
            stype = 'double'        
            if size < 4:
                size = 'small'
            elif size == 4:
                size = 'medium'
            elif size > 4:
                size = 'large'       
        else:            
            stype = 'single'                     
            if size < 2:
                size = 'small'
            elif size == 2:
                size = 'medium'
            elif size > 2:
                size = 'large'

        question = []

        # First page assessing the direction of the article
        question.append('[[Block:Text {}]]\n'.format(row[common.editId]))
        question.append('\n')
        
        question.append('[[Question:DB]]\n')
        question.append(''.join(['[[ID:decription]]\n']))
        question.append('<p>The texts that you will translate is about a conflict between two parties (nations or groups). The text that you will be working on is about the following topic: <br /><br /></p><p><b>{}:</b> {}</p>\n'.format(
            row[common.parentTitle], survey.descriptions[row[common.parentTitle]])
        )
        question.append('\n')
        question.append('[[PageBreak]]\n')
        question.append('\n')
                     
        # Previous Edit
        if type(row[common.previousEdit]) is str:
             
            question.append('[[Question:DB]]\n')
            question.append('[[ID:text{:03d}_previous_{}]]\n'.format(i, row[common.editId]))

            question.append(
                '<img src="{}/{}/{:03d}_{}_previous_{}.png" /\n'.format(
                    survey.imgSource, row[common.languageCode], i, survey.types[size2-1], row[common.editId]
                )
            )
                
            question.append('\n')
            
            question.extend(createQuestions(row, 'previous'))            

        # Current Edit
        if type(row[common.currentEdit]) is str:
            
            question.append('[[Question:DB]]\n')
            question.append('[[ID:text{:03d}_current_{}]]\n'.format(i, row[common.editId]))
            
            question.append(
                '<img src="{}/{}/{:03d}_{}_current_{}.png" />\n'.format(
                    survey.imgSource, row[common.languageCode], i, survey.types[size1-1], row[common.editId]
                )
            )
                
            question.append('\n')
            
            question.extend(createQuestions(row, 'current'))            
        
        if stype is 'double':
            
            question.append('[[PageBreak]]\n')
            
            question.append('[[Question:MC:SingleAnswer:Horizontal]]\n')
            question.append('[[ID:similarity_{}]]\n'.format(row[common.editId]))
            question.append('When comparing both edits, how similar do you think that both text are?\n')
            question.append('[[Choices]]\n')
            
            question.append('very different\n')
            question.append('2\n')
            question.append('3\n')
            question.append('4\n')
            question.append('5\n')
            question.append('6\n')
            question.append('very similar\n')
            question.append('\n')
            
            question.append('[[Question:MC:SingleAnswer:Horizontal]]\n')
            question.append('[[ID:both_perspective_{}]]\n'.format(row[common.editId]))
            question.append('Do both edits have similar perspectives (i.e., do both edits focus on the same party)?\n')
            question.append('[[Choices]]\n')
            
            question.append('different perspective\n')
            question.append('2\n')
            question.append('3\n')
            question.append('4\n')
            question.append('5\n')
            question.append('6\n')
            question.append('similar perspective\n')
            question.append('\n')
            
        addToSurvey(question, row[common.languageCode], stype, size)
        
        languages[row[common.languageCode]] += 1
           
