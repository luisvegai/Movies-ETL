#!/usr/bin/env PythonData
# coding: utf-8


import json
import pandas as pd
import numpy as np
import re
import time
import os

while True:
    file_dir = input('Enter full path of data folder: ')
    #file_dir = 'C:/Users/JD/Desktop/Analysis Projects/Movies-ETL'
    if os.path.exists(file_dir) == True:
        break
    else:
        print("Data folder not found")
        continue

while True:
    try:
        wikip_mov_json = input('Enter filename of wikipedia movies json file: ')
        #wikipedia.movies.json
        with open(f'{file_dir}/{wikip_mov_json}', mode='r') as file:
            wiki_movies_raw = json.load(file)
        break
    except FileNotFoundError:
        print("File not found")
        continue
    except (EOFError,PermissionError):
        print("Input is required")
        continue

wiki_movies = [movie for movie in wiki_movies_raw
               if ('Director' in movie or 'Directed by' in movie)
                   and 'imdb_link' in movie
                   and 'No. of episodes' not in movie]

while True:
    try:
        mov_metadata_csv = input('Enter filename of Kaggle metadata (csv) file: ')
        #movies_metadata.csv
        kaggle_metadata = pd.read_csv(f'{file_dir}/{mov_metadata_csv}', low_memory=False)
        break
    except FileNotFoundError:
        print("File not found")
        continue
    except (EOFError,PermissionError,OSError):
        print("Input is required")
        continue

while True:
    try:
        ratings_csv = input('Enter filename of MovieLens Rating data (csv) file (from Kaggle): ')
        #ratings.csv
        ratings = pd.read_csv(f'{file_dir}/{ratings_csv}')
        break
    except FileNotFoundError:
        print("File not found")
        continue
    except (EOFError,PermissionError,OSError):
      print("Input is required")
      continue


# Create a Function to Clean the Data

def clean_movie(movie):
    movie = dict(movie) #create a non-destructive copy
    alt_titles = {}
    # combine alternate titles into one list
    for key in ['Also known as','Arabic','Cantonese','Chinese','French',
                'Hangul','Hebrew','Hepburn','Japanese','Literally',
                'Mandarin','McCune–Reischauer','Original title','Polish',
                'Revised Romanization','Romanized','Russian',
                'Simplified','Traditional','Yiddish']:
        if key in movie:
            alt_titles[key] = movie[key]
            movie.pop(key)
    if len(alt_titles) > 0:
        movie['alt_titles'] = alt_titles


    # merge column names
    def change_column_name(old_name, new_name):
        if old_name in movie:
            movie[new_name] = movie.pop(old_name)
    change_column_name('Adaptation by', 'Writer(s)')
    change_column_name('Country of origin', 'Country')
    change_column_name('Directed by', 'Director')
    change_column_name('Distributed by', 'Distributor')
    change_column_name('Edited by', 'Editor(s)')
    change_column_name('Length', 'Running time')
    change_column_name('Original release', 'Release date')
    change_column_name('Music by', 'Composer(s)')
    change_column_name('Produced by', 'Producer(s)')
    change_column_name('Producer', 'Producer(s)')
    change_column_name('Productioncompanies ', 'Production company(s)')
    change_column_name('Productioncompany ', 'Production company(s)')
    change_column_name('Released', 'Release Date')
    change_column_name('Release Date', 'Release date')
    change_column_name('Screen story by', 'Writer(s)')
    change_column_name('Screenplay by', 'Writer(s)')
    change_column_name('Story by', 'Writer(s)')
    change_column_name('Theme music composer', 'Composer(s)')
    change_column_name('Written by', 'Writer(s)')

    return movie


clean_movies = [clean_movie(movie) for movie in wiki_movies]

wiki_movies_df = pd.DataFrame(clean_movies)

wiki_movies_df['imdb_id'] = wiki_movies_df['imdb_link'].str.extract(r'(tt\d{7})')
wiki_movies_df.drop_duplicates(subset='imdb_id', inplace=True)



#Remove Duplicate Rows

wiki_columns_to_keep = [column for column in wiki_movies_df.columns if wiki_movies_df[column].isnull().sum() < len(wiki_movies_df) * 0.9]
wiki_movies_df = wiki_movies_df[wiki_columns_to_keep]

box_office = wiki_movies_df['Box office'].dropna() 

def is_not_a_string(x):
    return type(x) != str

box_office = box_office.apply(lambda x: ' '.join(x) if type(x) == list else x)


#Parse the Box Office Data

form_one = r'\$\s*\d+\.?\d*\s*[mb]illi?on'
form_two = r'\$\s*\d{1,3}(?:[,\.]\d{3})+(?!\s[mb]illion)'

box_office = box_office.str.replace(r'\$.*[-—–](?![a-z])', '$', regex=True)

def parse_dollars(s):
    # if s is not a string, return NaN
    if type(s) != str:
        return np.nan

    # if input is of the form $###.# million
    if re.match(r'\$\s*\d+\.?\d*\s*milli?on', s, flags=re.IGNORECASE):

        # remove dollar sign and " million"
        s = re.sub('\$|\s|[a-zA-Z]','', s)

        # convert to float and multiply by a million
        value = float(s) * 10**6

        # return value
        return value

    # if input is of the form $###.# billion
    elif re.match(r'\$\s*\d+\.?\d*\s*billi?on', s, flags=re.IGNORECASE):

        # remove dollar sign and " billion"
        s = re.sub('\$|\s|[a-zA-Z]','', s)

        # convert to float and multiply by a billion
        value = float(s) * 10**9

        # return value
        return value

    # if input is of the form $###,###,###
    elif re.match(r'\$\s*\d{1,3}(?:[,\.]\d{3})+(?!\s[mb]illion)', s, flags=re.IGNORECASE):

        # remove dollar sign and commas
        s = re.sub('\$|,','', s)

        # convert to float
        value = float(s)

        # return value
        return value

    # otherwise, return NaN
    else:
        return np.nan

wiki_movies_df['box_office'] = box_office.str.extract(f'({form_one}|{form_two})', flags=re.IGNORECASE)[0].apply(parse_dollars)

wiki_movies_df.drop('Box office', axis=1, inplace=True)



#Parse Budget Data

budget = wiki_movies_df['Budget'].dropna()
budget = budget.map(lambda x: ' '.join(x) if type(x) == list else x)
budget = budget.str.replace(r'\$.*[-—–](?![a-z])', '$', regex=True)

matches_form_one = budget.str.contains(form_one, flags=re.IGNORECASE)
matches_form_two = budget.str.contains(form_two, flags=re.IGNORECASE)

budget = budget.str.replace(r'\[\d+\]\s*', '')

wiki_movies_df['budget'] = budget.str.extract(f'({form_one}|{form_two})', flags=re.IGNORECASE)[0].apply(parse_dollars)

release_date = wiki_movies_df['Release date'].dropna().apply(lambda x: ' '.join(x) if type(x) == list else x)

date_form_one = r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s[123]\d,\s\d{4}'
date_form_two = r'\d{4}.[01]\d.[123]\d'
date_form_three = r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s\d{4}'
date_form_four = r'\d{4}'

wiki_movies_df['release_date'] = pd.to_datetime(release_date.str.extract(f'({date_form_one}|{date_form_two}|{date_form_three}|{date_form_four})')[0], infer_datetime_format=True)

running_time = wiki_movies_df['Running time'].dropna().apply(lambda x: ' '.join(x) if type(x) == list else x)

running_time_extract = running_time.str.extract(r'(\d+)\s*ho?u?r?s?\s*(\d*)|(\d+)\s*m')

running_time_extract = running_time_extract.apply(lambda col: pd.to_numeric(col, errors='coerce')).fillna(0)

wiki_movies_df['running_time'] = running_time_extract.apply(lambda row: row[0]*60 + row[1] if row[2] == 0 else row[2], axis=1)

wiki_movies_df.drop('Running time', axis=1, inplace=True)



## Kaggle Metadata

kaggle_metadata = kaggle_metadata[kaggle_metadata['adult'] == 'False'].drop('adult',axis='columns')

kaggle_metadata['video'] = kaggle_metadata['video'] == 'True'

kaggle_metadata['budget'] = kaggle_metadata['budget'].astype(int)
kaggle_metadata['id'] = pd.to_numeric(kaggle_metadata['id'], errors='raise')
kaggle_metadata['popularity'] = pd.to_numeric(kaggle_metadata['popularity'], errors='raise')

kaggle_metadata['release_date'] = pd.to_datetime(kaggle_metadata['release_date'])

ratings['timestamp'] = pd.to_datetime(ratings['timestamp'], unit='s')



#Merge Wikipedia and Kaggle Metadata

movies_df = pd.merge(wiki_movies_df, kaggle_metadata, on='imdb_id', suffixes=['_wiki','_kaggle'])

movies_df.fillna(0).plot(x='running_time', y='runtime', kind='scatter')

movies_df.fillna(0).plot(x='budget_wiki',y='budget_kaggle', kind='scatter')

movies_df.fillna(0).plot(x='box_office', y='revenue', kind='scatter')

movies_df.fillna(0)[movies_df['box_office'] < 10**9].plot(x='box_office', y='revenue', kind='scatter')

movies_df[['release_date_wiki','release_date_kaggle']].plot(x='release_date_wiki', y='release_date_kaggle', style='.')

movies_df = movies_df.drop(movies_df[(movies_df['release_date_wiki'] > '1996-01-01') & (movies_df['release_date_kaggle'] < '1965-01-01')].index)

movies_df.drop(columns=['title_wiki','release_date_wiki','Language','Production company(s)'], inplace=True)

def fill_missing_kaggle_data(df, kaggle_column, wiki_column):
    df[kaggle_column] = df.apply(
        lambda row: row[wiki_column] if row[kaggle_column] == 0 else row[kaggle_column]
        , axis=1)
    df.drop(columns=wiki_column, inplace=True)

fill_missing_kaggle_data(movies_df, 'runtime', 'running_time')
fill_missing_kaggle_data(movies_df, 'budget_kaggle', 'budget_wiki')
fill_missing_kaggle_data(movies_df, 'revenue', 'box_office')

for col in movies_df.columns:
    lists_to_tuples = lambda x: tuple(x) if type(x) == list else x
    value_counts = movies_df[col].apply(lists_to_tuples).value_counts(dropna=False)
    num_values = len(value_counts)
    if num_values == 1:
        movies_df[col].value_counts(dropna=False)

movies_df = movies_df.loc[:, ['imdb_id','id','title_kaggle','original_title','tagline','belongs_to_collection','url','imdb_link',
                       'runtime','budget_kaggle','revenue','release_date_kaggle','popularity','vote_average','vote_count',
                       'genres','original_language','overview','spoken_languages','Country',
                       'production_companies','production_countries','Distributor',
                       'Producer(s)','Director','Starring','Cinematography','Editor(s)','Writer(s)','Composer(s)','Based on'
                      ]]

movies_df.rename({'id':'kaggle_id',
                  'title_kaggle':'title',
                  'url':'wikipedia_url',
                  'budget_kaggle':'budget',
                  'release_date_kaggle':'release_date',
                  'Country':'country',
                  'Distributor':'distributor',
                  'Producer(s)':'producers',
                  'Director':'director',
                  'Starring':'starring',
                  'Cinematography':'cinematography',
                  'Editor(s)':'editors',
                  'Writer(s)':'writers',
                  'Composer(s)':'composers',
                  'Based on':'based_on'
                 }, axis='columns', inplace=True)




#Transform and Merge Rating Data

rating_counts = ratings.groupby(['movieId','rating'], as_index=False).count() \
                .rename({'userId':'count'}, axis=1) \
                .pivot(index='movieId',columns='rating', values='count')

rating_counts.columns = ['rating_' + str(col) for col in rating_counts.columns]

movies_with_ratings_df = pd.merge(movies_df, rating_counts, left_on='kaggle_id', right_index=True, how='left')

movies_with_ratings_df[rating_counts.columns] = movies_with_ratings_df[rating_counts.columns].fillna(0)



## Connect Pandas and SQL

from sqlalchemy import create_engine

from config import db_password

db_name = input('Enter postgreSQL database name to enter data: ')
db_string = f"postgres://postgres:{db_password}@127.0.0.1:5432/{db_name}"

engine = create_engine(db_string)

print(f'Importing data to database {db_name}...')

while True:
    try:
        movies_table = input('Enter movies table name for postgreSQL database: ')
        movies_df.to_sql(name=movies_table, con=engine)
        break
    except ValueError:
        print("Table already exist, choose another name")
        continue

print("Import of movies data to movies table completed")


# Importing the ratings data

# create a variable for the number of rows imported
rows_imported = 0
# get the start_time from time.time()
start_time = time.time()

while True:
    try:
        ratings_table = input('Enter ratings table name for postgreSQL database: ')

        for data in pd.read_csv(f'{file_dir}/{ratings_csv}', chunksize=1000000):

            # print out the range of rows that are being imported
            print(f'importing rows {rows_imported} to {rows_imported + len(data)}...', end='')

            data.to_sql(name=ratings_table, con=engine, if_exists='append')

            # increment the number of rows imported by the size of 'data'
            rows_imported += len(data)
            # add elapsed time to final print out
            
            
            # print that the rows have finished importing
            print(f'Done. {time.time() - start_time} total seconds elapsed')
        break
    except ValueError:
        print("Table already exist, choose another name")
        continue
    
print("Import of ratings data to ratings table completed")