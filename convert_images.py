# -*- coding: utf-8 -*-
"""
Created on Mon Mar  4 11:58:55 2019

@author: jdevreeze
"""
from PIL import Image, ImageDraw, ImageFont
from textwrap import wrap
from tqdm import tqdm

import pandas as pd
import os

from config import common, images

def getTextDimensions(text, font):     
    width = 0    
    for char in text:
        width += font.getsize(char)[0]        
    return width

def convertImage(text): 
    
    # Font used for the text
    font_regular = ImageFont.truetype('font/Arial.ttf', size=images.fontSize)
    font_bold = ImageFont.truetype('font/Arialbd.ttf', size=images.fontSize)
    color = 'rgb(0, 0, 0)'

    line_height = images.fontSize
    
    # Determine the line width for the specified font size
    line_width = int(600 / (getTextDimensions(text, font_regular) / len(text)))
    
    # Add space between the lines
    padding = int(images.fontSize / 2)
    
    # Warp the text
    lines = wrap(text, width=line_width)
    
    # Calculate image height
    image_height = line_height + ((len(lines) + 1) * (line_height + padding)) + line_height
    image_width = 650

    # Create an empty image
    img = Image.new('RGB', (image_width, image_height), (255, 255, 255))
    d = ImageDraw.Draw(img)
    
    (x, y) = (0, 0)
    
    flag = False

    for line in lines:
        
        # The edit is starts and ends on this line
        if line.find('<b>') is not -1 and line.find('</b>') is not -1:
            
            parts = line.split('<b>')
            d.text((x, y), parts[0], fill=color, font=font_regular)

            first = getTextDimensions(parts[0], font_regular)
            
            parts = parts[1].split('</b>')
            second = first + getTextDimensions(parts[0], font_bold)

            d.text((first, y), parts[0], fill=color, font=font_bold)
            d.text((second, y), parts[1], fill=color, font=font_regular)
        
        # The edit starts on this line
        if line.find('<b>') is not -1 and line.find('</b>') is -1:
            
            flag = True
            parts = line.split('<b>')            

            start = getTextDimensions(parts[0], font_regular)
            
            d.text((x, y), parts[0], fill=color, font=font_regular)
            d.text((start, y), parts[1], fill=color, font=font_bold)
        
        # The edit ends on this line
        if line.find('<b>') is -1 and line.find('</b>') is not -1:
            
            flag = False
            parts = line.split('</b>')
            
            start = getTextDimensions(parts[0], font_bold)
            
            d.text((x, y), parts[0], fill=color, font=font_bold)
            d.text((start, y), parts[1], fill=color, font=font_regular)
        
        # This line is part of the edit or is part of the context
        if line.find('<b>') is -1 and line.find('</b>') is -1:
            if flag is True:
                d.text((x, y), line, fill=color, font=font_bold)
            else:
                d.text((x, y), line, fill=color, font=font_regular)
            
        y += line_height + padding
    
    return img

"""
Execute the main conversion process.
"""
if __name__ == "__main__":    
        
    os.chdir(common.pathName)
    
    df = pd.read_csv(common.fileName, sep=';', encoding='utf-8')
    
    split1 = df[common.currentEdit].str.len().quantile(.33)
    split2 = df[common.currentEdit].str.len().quantile(.66)
    
    split3 = df[common.previousEdit].str.len().quantile(.33)
    split4 = df[common.previousEdit].str.len().quantile(.66)

    languages = pd.Series([1] * df[common.languageCode].describe()['unique'], index=df[common.languageCode].unique())
    
    # Create path if it not exists
    if not os.path.exists(images.exportPath):
         os.mkdir(images.exportPath)
         
    for language in languages.index:
        if not os.path.exists('{}/{}'.format(images.exportPath, language)):
            os.mkdir('{}/{}'.format(images.exportPath, language))

    for index, row in tqdm(df.iterrows(), total=df.shape[0]):
       
        i = languages[row[common.languageCode]]
        
        # determine size of current edit
        if type(row[common.currentEdit]) is str:
            
            current_size = len(row[common.currentEdit])
                        
            if current_size <= split1:
                size = 'small' 
            elif current_size > split1 and current_size < split2:
                size = 'medium'
            elif current_size >= split2:
                size = 'large'
            
            # Convert the text to an image
            img = convertImage(row[common.currentEdit])         
            img.save('{}/{}/{:03d}_{}_current_{}.png'.format(images.exportPath, row[common.languageCode], i, size, row[common.editId]))
        
        # determine size of previous edit
        if type(row[common.previousEdit]) is str:
            
            previous_size = len(row[common.previousEdit])
            
            if previous_size <= split3:
                size = 'small' 
            elif previous_size > split3 and previous_size < split4:
                size = 'medium'
            elif previous_size >= split4:
                size = 'large'
            
            # Convert the text to an image
            img = convertImage(row[common.previousEdit])         
            img.save('{}/{}/{:03d}_{}_previous_{}.png'.format(images.exportPath, row[common.languageCode], i, size, row[common.editId]))
               
        languages[row[common.languageCode]] += 1
        
