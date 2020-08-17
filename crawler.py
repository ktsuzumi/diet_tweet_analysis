import time
import os
from os.path import join, abspath, dirname, expanduser
import requests
from requests_oauthlib import OAuth1
import sqlite3
from dotenv import load_dotenv
import argparse
import re
import emoji


def remove_emoji(src_str):
    return ''.join(c for c in src_str if c not in emoji.UNICODE_EMOJI)


def insert(tweet, dbc, table):
    sql = 'insert into {} values (?)'.format(table)
    tap = (tweet, )
    cursor = dbc.cursor()
    cursor.execute(sql, tap)


def db_connect(db_file):
    try:
        dbc = sqlite3.connect(db_file, timeout=10)
        return dbc
    except sqlite3.Error as e:
        print ("Error {}:".format(e.args[0]))
        return None


def do_preprocess(text):
    text = text.lower()
    text = re.sub(r'rt', '', text)
    text = re.sub(r'@(\w+:*)', '', text)
    text = re.sub(r'https?://[\w/:%#\$&\?\(\)~\.=\+\-]+', '', text)
    text = re.sub(r'\d+', '', text)
    text = re.sub(r'[０-９]+', '', text)
    text = re.sub(r'(?<![0-9a-zA-Z\'\"#@=:;])@([0-9a-zA-Z_]{1,15})', "", text)
    text = re.sub(r'…', '', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub('\n', ' ', text)
    text = remove_emoji(text)
    text = text.translate(str.maketrans(' ', ' ', '*#$%&()*+,-./:;<=>@[\]^_`{|}~'))
    return text


def main(args):
    current_dirname = dirname(abspath(__file__))
    dbc = db_connect(join(current_dirname, 'tweet.db'))
    home = expanduser('~')
    env_path = join(home, '.env')
    load_dotenv(dotenv_path=env_path)

    # 環境変数から取得
    client_key= os.getenv('TWITTER_CLIENT_KEY', None)
    client_secret=os.getenv('TWITTER_CLIENT_SECRET', None)
    resource_owner_key=os.getenv('TWITTER_RESOURCE_OWNER_KEY', None)
    resource_owner_secret=os.getenv('TWITTER_RESOURCE_OWNER_SECRET', None)
    oauth = OAuth1(client_key, client_secret, resource_owner_key, resource_owner_secret)
    url = 'https://api.twitter.com/1.1/search/tweets.json'

    if args.table == 'en_diet':
        params = {'q': 'diet or Diet or DIET',
                  'lang': 'en',
                  'locale': 'en',
                  'result_type': 'mixed',
                  'count': '100'}
    elif args.table == 'jp_diet':
        params = {'q': 'ダイエット',
                  'lang': 'ja',
                  'result_type': 'mixed',
                  'count': '100'}
    elif args.table == 'jp_syokujiseigen':
        params = {'q': '食事制限',
                  'lang': 'ja',
                  'result_type': 'mixed',
                  'count': '100'}
    r = requests.get(url, params=params, auth=oauth)
    time.sleep(1)
    if r.status_code == 404:
        print('404')
    res_data = r.json()
    res_statuses = res_data['statuses']
    for steps,tweet in enumerate(res_statuses):
        tweet_text = tweet['text']
        text = do_preprocess(tweet_text)
        insert(text, dbc, args.table)
    dbc.commit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--table', type=str, choices=['en_diet', 'jp_diet', 'jp_syokujiseigen'])
    args = parser.parse_args()
    main(args)
