# Import package(s)
import os
import urllib.request
import json
import math
import pandas as pd
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from xml.sax.saxutils import unescape
import argparse

# Parse and validate command line arguments.
parser = argparse.ArgumentParser()

parser.add_argument('action', help='Specify the action to perform.', type=str, choices=['download', 'clean', 'analyze'])
parser.add_argument('-v', '--verbose', help='Increase output verbosity.', action='store_true')
parser.add_argument('-it', '--include_tests', help='Include tests, where applicable.', action='store_true')
parser.add_argument('-cf', '--configuration_file', help='Specify configuration file (Defaults to "etsy_configuration.json").', type=str, default='etsy_configuration.json')
parser.add_argument('-wd', '--working_directory', help='Specify working directory (Defaults to same directory as Python script).', type=str, default=os.path.dirname(os.path.realpath(__file__)))
parser.add_argument('-sf', '--shops_file', help='Specify shops file (Defaults to "etsy_shops.json").', type=str, default='etsy_shops.json')
parser.add_argument('-s', '--shop_ID', help='Specify shop ID to be processed.', type=int)
parser.add_argument('-t', '--top_N', help='Specify number of top meaningful terms to be displayed.', type=int, default=5)

args = parser.parse_args()

# Make shop_ID required if action = 'analyze'
if (args.action == 'analyze' and args.shop_ID is None):
    print('-s (shop_ID) is required when action is "analyze".')
    quit()

if args.verbose:
    print('')
    print('Verbosity: On')
    print('Specified action:', args.action)
    print('Include tests, where applicable: Yes') if args.include_tests else print('Include tests, where applicable: No')
    print('Configuration file name:', args.configuration_file)
    print('Working direcory:', args.working_directory)
    print('Shops file name:', args.shops_file)
    print('Shop ID:', args.shop_ID) if args.shop_ID is not None else print('Processing all stores.')

# Declare variable(s).
configuration_file_name = args.configuration_file
working_directory = args.working_directory
configuration_file_path = os.path.abspath(os.path.join(working_directory, configuration_file_name))
shops_file_name = args.shops_file
shops_file_path = os.path.abspath(os.path.join(working_directory, shops_file_name))

if args.verbose:
    print('Configuration file path:', configuration_file_path)
    print('Shops file path:', shops_file_path)

# Function to get configuration values
def get_configurations(JSON_file_path):
    with open(JSON_file_path, 'r') as configuration_file:
        dict_configurations = json.loads(configuration_file.read())

    return(dict_configurations)

# Test function: get_configurations()
if(args.include_tests):
    assert type(get_configurations(configuration_file_path)) == dict, 'get_configurations function failed test.'
    assert len(get_configurations(configuration_file_path)) > 0, 'get_configurations function failed test.'

# Function to get shops
def get_shops(JSON_file_path):
    with open(JSON_file_path, 'r') as shops_file:
        dict_shops = json.loads(shops_file.read())

    return(dict_shops)

# Test function: get_shops()
if(args.include_tests):
    assert type(get_shops(shops_file_path)) == dict, 'get_shops function failed test.'
    assert len(get_shops(shops_file_path)) > 0, 'get_shops function failed test.'

# Declare variable(s).
configurations = get_configurations(configuration_file_path)
API_URI_template = configurations['API_URI_template']
API_key = configurations['API_key']
API_page_limit = configurations['API_page_limit']
shops = get_shops(shops_file_path)
separator = '\n******************************************\n'

if args.verbose:
    print('API URI template:', API_URI_template)
    print('API key:', API_key)
    print('API page_limit:', API_page_limit)

# Function to download and return single shop's items from API
def download_single_shop_items(shop_ID, configurations, working_directory, maximum_request_count = -1, verbose = False):

    # Get configuration values.
    API_URI_template = configurations['API_URI_template']
    API_key = configurations['API_key']
    API_page_limit = configurations['API_page_limit']

    # Construct request URL.
    API_request_URL_part_1 = API_URI_template.replace('$shop_ID$', str(shop_ID))
    API_request_URL =  API_request_URL_part_1 + '?api_key=' + str(API_key) + '&limit=' + str(API_page_limit)
    API_request_URL_setup =  API_request_URL_part_1 + '?api_key=' + str(API_key) + '&limit=1&offset=0'

    print(separator)
    print('Start download for Shop ' + shops[str(shop_ID)] + ' (' + str(shop_ID) + ').')

    # Perform setup request (limit = 1) to get & compute API request summary information.
    # E.g., item count & request count
    with urllib.request.urlopen(API_request_URL_setup) as url:
        dict_items = json.loads(url.read().decode())
    
    if(verbose): print(API_request_URL_setup)

    # Set API request variables.
    item_count = dict_items['count']
    target_request_count = int(math.ceil(item_count / API_page_limit))
    current_request_count = 1
    API_current_offset = 0
    
    if(verbose):
        print('Item count:', item_count)
        print('Target request count:', target_request_count)
    
    # Set API response variables.
    lst_items= []
    df_items = pd.DataFrame(columns=['title', 'description'])
    
    # For each request ...
    for i in range(target_request_count):
        
        # maximum_request_count: Debug variable to limit the number of requests,
        # irrespective of target request count
        if (current_request_count <= maximum_request_count or maximum_request_count < 0):
            API_request_URL_current = API_request_URL + '&offset=' + str(API_current_offset)

            with urllib.request.urlopen(API_request_URL_current) as url:
                dict_items = json.loads(url.read().decode())

            if(verbose):
                print(API_request_URL_current)
                print('Current request count:', current_request_count)
            
            lst_items = [{'title':item['title'], 'description':item['description']} for item in dict_items['results']]
            df_current_items = pd.DataFrame(lst_items)
            df_items = pd.concat([df_items, df_current_items[['title', 'description']]])
            if(verbose): print('# of items: ', str(len(df_items)))
            
            API_current_offset = API_current_offset + API_page_limit
            current_request_count = current_request_count + 1

    # Save downloaded items.
    JSON_destination_file_name = 'items_raw_' + str(shop_ID) + '.json'
    JSON_destination_file_name = os.path.abspath(os.path.join(working_directory, JSON_destination_file_name))

    with open(JSON_destination_file_name, 'w') as f_JSON_destination_file:
        df_items.to_json(path_or_buf=f_JSON_destination_file, orient="records", lines=False)

    print('End download for Shop ' + shops[str(shop_ID)] + ' (' + str(shop_ID) + ').')
    print('Downloaded ' + str(len(df_items)) + ' items to ' + JSON_destination_file_name)

    # Return downloaded items as dataframe.
    return(df_items)

# Function to download all shops' items from API
def download_all_shop_items(shops, configurations, working_directory, verbose = False):
    for shop_ID in shops.keys():
        df_shop_items = download_single_shop_items(shop_ID = shop_ID,
                                                         configurations = configurations,
                                                         working_directory = working_directory,
                                                         verbose=verbose)

# Function to filter out non-alphabetic characters.
def remove_non_alphabetic_characters(lst_words):
    return([word for word in lst_words if word.isalpha()])

# Test function: remove_non_alphabetic_characters()
if(args.include_tests):
    assert type(remove_non_alphabetic_characters(['abc', 'def', ';', '*', '3', '44'])) == list, 'remove_non_alphabetic_characters function failed test.'
    assert len(remove_non_alphabetic_characters(['abc', 'def', ';', '*', '3', '44'])) == 2, 'remove_non_alphabetic_characters function failed test.'

# Function to filter out HTML characters.
def clean_HTML_characters(str_words):
    HTML_characters = {'&amp;':'&', '&lt;':'<', '&gt;':'>', '&quot;':'"', '&nbsp;':' ', '&copy;':' ', '&trade;':' ',
                       '&reg;':' '}
    
    unescaped_words = unescape(str_words, HTML_characters).strip()
    return(unescaped_words)

# Test function: clean_HTML_characters()
if(args.include_tests):
    assert type(clean_HTML_characters('All My Stars: 12&quot; x 12&quot; &lt;&nbsp;&lt;&copy;&trade;')) == str, 'clean_HTML_characters function failed test.'
    assert len(clean_HTML_characters('All My Stars: 12&quot; x 12&quot; &lt;&nbsp;&lt;&copy;&trade;')) == 27, 'clean_HTML_characters function failed test.'

# Function to filter out stop words.
def remove_stop_words(lst_words, verbose = False):
    stop_words = stopwords.words('english')
    shop_names = [shop_name.lower() for shop_name in get_shops(shops_file_path).values()]
    social_media_names = ['linkedin', 'facebook', 'etsy', 'snapchat', 'instagram']
    domain_specific_words = ['x', 'http', 'https', 'cm', 'inc', 'inches', 'mm', 'days', 'please', 'shop', 'ever',
                             'thanks', 'receive', 'purchase', 'ready', 'return', 'contact', 'shipping', 'cost', 'expedited',
                             'size', 'made']
    
    stop_words = stop_words + shop_names + social_media_names + domain_specific_words

    return([word for word in lst_words if not word in stop_words])

# Test function: remove_stop_words()
if(args.include_tests):
    assert type(remove_stop_words(['abc', 'def', 'i', 'me', 'you'])) == list, 'remove_stop_words function failed test.'
    assert len(remove_stop_words(['abc', 'def', 'i', 'me', 'you'])) == 2, 'remove_stop_words function failed test.'

# Function to clean and return single shop's items from raw file
def clean_single_shop_items(shop_ID, configurations, working_directory, verbose = False):
    # Construct raw file name for specified shop.
    shop_items_raw_file_name = 'items_raw_' + str(shop_ID) + '.json'
    shop_items_raw_file_path = os.path.abspath(os.path.join(working_directory, shop_items_raw_file_name))
    if verbose: print('Shop', str(shop_ID), 'raw file name:', shop_items_raw_file_path)

    print(separator)
    print('Start cleaning for Shop ' + shops[str(shop_ID)] + ' (' + str(shop_ID) + ').')

    # Load raw file into dataframe.
    with open(shop_items_raw_file_path, 'r') as shop_items_raw_file:
        dict_shop_items = json.loads(shop_items_raw_file.read())
        df_shop_items = pd.DataFrame(dict_shop_items)
        df_shop_items = df_shop_items[['title', 'description']]

    # Filter out HTML characters.
    df_shop_items['title_clean'] = df_shop_items['title'].apply(clean_HTML_characters)
    df_shop_items['description_clean'] = df_shop_items['description'].apply(clean_HTML_characters)

    # Convert to lower case.
    df_shop_items['title_clean'] = df_shop_items['title_clean'].apply(str.lower)
    df_shop_items['description_clean'] = df_shop_items['description_clean'].apply(str.lower)

    # Perform word tokenization.
    df_shop_items['title_clean'] = df_shop_items['title_clean'].apply(word_tokenize)
    df_shop_items['description_clean'] = df_shop_items['description_clean'].apply(word_tokenize)
    
    # Filter out non-alphabetic characters.
    df_shop_items['title_clean'] = df_shop_items['title_clean'].apply(remove_non_alphabetic_characters)
    df_shop_items['description_clean'] = df_shop_items['description_clean'].apply(remove_non_alphabetic_characters)
    
    # Filter out stop words.
    df_shop_items['title_clean'] = df_shop_items['title_clean'].apply(remove_stop_words)
    df_shop_items['description_clean'] = df_shop_items['description_clean'].apply(remove_stop_words)

    # Save cleaned items.
    JSON_destination_file_name = 'items_clean_' + str(shop_ID) + '.json'
    JSON_destination_file_name = os.path.abspath(os.path.join(working_directory, JSON_destination_file_name))

    with open(JSON_destination_file_name, 'w') as f_JSON_destination_file:
        df_shop_items.to_json(path_or_buf=f_JSON_destination_file, orient="records", lines=False)

    print('End cleaning for Shop ' + shops[str(shop_ID)] + ' (' + str(shop_ID) + ').')
    print('Cleaned ' + str(len(df_shop_items)) + ' items to ' + JSON_destination_file_name)

    return(df_shop_items)

# Function to clean all shops' items from raw files
def clean_all_shop_items(shops, configurations, working_directory, verbose = False):
    for shop_ID in shops.keys():
        df_shop_items = clean_single_shop_items(shop_ID = shop_ID,
                                                configurations = configurations,
                                                working_directory = working_directory,
                                                verbose=verbose)

# Function to compute Term Frequency (TF) of a word in a given document.
def get_word_TF(word, document):
    return(document.count(word) / len(document))

# Test function: get_word_TF()
if(args.include_tests):
    assert type(get_word_TF(word='hello', document=['hello','world','today','is','a','beautiful','day'])) == float, 'get_word_TF function failed test.'
    assert get_word_TF(word='hello', document=['hello','world','today','is','a','beautiful','day']) == 0.14285714285714285, 'get_word_TF function failed test.'

# Function to compute Term Frequency (TF) of all words in a given document.
def get_document_TFs(document):
    # Create dictionary containing word:TFIDF key:value pairs for each word in document.
    scores = {word: get_word_TF(word, document) for word in document}
    
    # Convert dictionary to list of (word:TFIDF) tuples.
    scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return(scores)

# Test function: get_document_TFs()
if(args.include_tests):
    assert type(get_document_TFs(document=['hello','world','today','is','a','beautiful','day'])) == list, 'get_document_TFs function failed test.'
    assert len(get_document_TFs(document=['hello','world','today','is','a','beautiful','day'])) == 7, 'get_document_TFs function failed test.'

# Function to get single shop's top meaningful items.
def get_single_shop_top_meaningful_terms(shop_ID, configurations, working_directory, top_N = 5, verbose = False):

    # Construct clean file name for specified shop.
    shop_items_clean_file_name = 'items_clean_' + str(shop_ID) + '.json'
    shop_items_clean_file_path = os.path.abspath(os.path.join(working_directory, shop_items_clean_file_name))
    if verbose: print('Shop', str(shop_ID), 'clean file name:', shop_items_clean_file_path)

    # Load clean file into dataframe.
    with open(shop_items_clean_file_path, 'r') as shop_items_clean_file:
        dict_shop_items = json.loads(shop_items_clean_file.read())
        df_shop_items = pd.DataFrame(dict_shop_items)
        df_shop_items = df_shop_items[['title', 'description', 'title_clean', 'description_clean']]

    ds_terms = pd.concat([df_shop_items['title_clean'], df_shop_items['description_clean']])
    document = []

    for terms in ds_terms:
        for term in terms:
            document.append(term)
    
    document_TFs = get_document_TFs(document)
    document_TFs = sorted(document_TFs, key=lambda x: x[1], reverse=True)[:top_N]

    print('')
    print('Top', str(top_N), 'meaningful terms:')
    print('')
    print(pd.DataFrame(document_TFs, columns=['term', 'score']))

    return(document_TFs)

if __name__ == '__main__':
    if (args.action == 'download'):
        if (args.shop_ID is None):
            download_all_shop_items(shops, configurations, args.working_directory, verbose=args.verbose)
        else:
            df_shop_items = download_single_shop_items(args.shop_ID, configurations, args.working_directory, verbose=args.verbose)
    elif (args.action == 'clean'):
        if (args.shop_ID is None):
            clean_all_shop_items(shops, configurations, args.working_directory, verbose=args.verbose)
        else:
            clean_single_shop_items(args.shop_ID, configurations, args.working_directory, verbose=args.verbose)
    elif (args.action == 'analyze'):
        if (args.shop_ID is None):
            pass
        else:
            get_single_shop_top_meaningful_terms(args.shop_ID, configurations, args.working_directory, top_N = args.top_N, verbose=args.verbose)