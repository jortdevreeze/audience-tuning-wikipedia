# -*- coding: utf-8 -*-
"""
Created on Wed Feb 12 11:26:14 2020

@author: jdevreeze
"""

import os
import argparse
import pandas as pd

from PIL import Image, ImageDraw, ImageFont
from textwrap import wrap
from tqdm import tqdm

def getTextDimensions(text, font):     
    width = 0    
    for char in text:
        width += font.getsize(char)[0]        
    return width

def convertImage(text, seperator, font_size): 
    
    # Font used for the text
    try:
        font_regular = ImageFont.truetype('../font/Arial.ttf', size=font_size)
        font_bold = ImageFont.truetype('../font/Arialbd.ttf', size=font_size)
    except:
        raise ValueError('Can not open the specified font.')
    
    color = 'rgb(0, 0, 0)'

    line_height = font_size
    
    # Determine the line width for the specified font size
    line_width = int(600 / (getTextDimensions(text, font_regular) / len(text)))
    
    # Add space between the lines
    padding = int(font_size / 2)
    
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
        if line.find(seperator[0]) is not -1 and line.find(seperator[1]) is not -1:
            
            parts = line.split(seperator[0])
            d.text((x, y), parts[0], fill=color, font=font_regular)

            first = getTextDimensions(parts[0], font_regular)
            
            parts = parts[1].split(seperator[1])
            second = first + getTextDimensions(parts[0], font_bold)

            d.text((first, y), parts[0], fill=color, font=font_bold)
            d.text((second, y), parts[1], fill=color, font=font_regular)
        
        # The edit starts on this line
        if line.find(seperator[0]) is not -1 and line.find(seperator[1]) is -1:
            
            flag = True
            parts = line.split(seperator[0])            

            start = getTextDimensions(parts[0], font_regular)
            
            d.text((x, y), parts[0], fill=color, font=font_regular)
            d.text((start, y), parts[1], fill=color, font=font_bold)
        
        # The edit ends on this line
        if line.find(seperator[0]) is -1 and line.find(seperator[1]) is not -1:
            
            flag = False
            parts = line.split(seperator[1])
            
            start = getTextDimensions(parts[0], font_bold)
            
            d.text((x, y), parts[0], fill=color, font=font_bold)
            d.text((start, y), parts[1], fill=color, font=font_regular)
        
        # This line is part of the edit or is part of the context
        if line.find(seperator[0]) is -1 and line.find(seperator[1]) is -1:
            if flag is True:
                d.text((x, y), line, fill=color, font=font_bold)
            else:
                d.text((x, y), line, fill=color, font=font_regular)
            
        y += line_height + padding
    
    return img

def main():
    
    parser = argparse.ArgumentParser(description='Render all edits to images to prohibit copy and pasting of text.') 
    
    parser.add_argument('--input', metavar='input', type=str, required=True, help='Opens a csv file from the specified path.')
    parser.add_argument('--path', metavar='path', type=str, required=True, help='Specify a path to save all rendered images.')
    parser.add_argument('--blacklist', metavar='blacklist', nargs='*', type=str, default=False, help='A list with languages to exclude from the input data.')
    parser.add_argument('--whitelist', metavar='whitelist', nargs='*', type=str, default=False, help='A list with languages to include from the input data. Note that this overrides a blacklist.')
    parser.add_argument('--font_size', metavar='font_size', type=int, default=False, help='Defines font size that should be used rendering the edits (default: 16).')
    parser.add_argument('--seperator', metavar='seperator', type=str, nargs=2, default=False, help='Defines what separates context from the actual edit (default: ["<b>", "</b>"]).')

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

    font_size = args.font_size if args.font_size is not False else 16
    seperator = args.seperator if args.seperator is not False else ['<b>', '</b>']

    languages = pd.Series([1] * df.Language.describe()['unique'], index=df.Language.unique())
    
    # Create path if it not exists
    if not os.path.exists(args.path):
         os.mkdir(args.path)
         
    for language in languages.index:
        if not os.path.exists('{}/{}'.format(args.path, language)):
            os.mkdir('{}/{}'.format(args.path, language))
    
    for index, row in tqdm(df.iterrows(), total=df.shape[0]):
       
        i = languages[row.Language]

        #  Convert the current edit to an image
        if type(row.CurrentEdit) is str:
            img = convertImage(row.CurrentEdit, seperator, font_size)         
            img.save('{}/{}/{:03d}_current_{}.png'.format(args.path, row.Language, i, row.EditId))
        
        if type(row.PreviousEdit) is str:
            img = convertImage(row.PreviousEdit, seperator, font_size)         
            img.save('{}/{}/{:03d}_previous_{}.png'.format(args.path, row.Language, i, row.EditId))
               
        languages[row.Language] += 1

if __name__ == "__main__": 
   main() 
