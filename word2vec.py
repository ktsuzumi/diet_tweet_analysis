from os.path import join, abspath, dirname
import sqlite3
import numpy as np
import nltk
import MeCab
from nltk.corpus import stopwords as nltk_stopwords
import itertools
from gensim.models import word2vec
import argparse


current_dirname = dirname(abspath(__file__))

slothlib_path = join(current_dirname, 'jp_stopword.txt')
with open(slothlib_path) as f:
    lines = f.readlines()
    slothlib_stopwords = [word.rstrip('\n') for word in lines]

jp_stopwords = [ss for ss in slothlib_stopwords if not ss == u'']
en_stopwords = list(set(nltk_stopwords.words("english")))


def db_connect(db_file):
    try:
        dbc = sqlite3.connect(db_file, timeout=10)
        return dbc
    except sqlite3.Error as e:
        print("Error {}:".format(e.args[0]))
        return None


def del_en_stopwords(text):
    text = [word for word in text if word not in en_stopwords and len(word) > 1]
    return text


def del_jp_stopwords(text):
    text = [word for word in text if word not in jp_stopwords]
    return text


def tokenizer(text):
    # MeCabの形態素解析器(Tagger)の初期化
    tagger = MeCab.Tagger()
    tagger.parse('')
    # MeCabの解析
    node = tagger.parseToNode(text)
    # 解析結果から名詞、動詞、形容詞のみにする
    word_list = []
    while node:
        features = node.feature.split(",")
        features = [features[i] if len(features) > i else None for i in range(0, 9)]
        if features[0] in ['名詞']:
            word_list.append(features[6])
        node = node.next
    return word_list


def select(dbc, table):
    sql = 'SELECT tweet from {}'.format(table)
    cursor = dbc.cursor()
    rs = cursor.execute(sql).fetchall()
    tweet_list = []
    if rs:
        if table == 'en_diet':
            for tweet in rs:
                tokens = nltk.word_tokenize(tweet[0])
                if "diet" in tokens:
                    tweet_list.append(del_en_stopwords(tokens))
        else:
            for tweet in rs:
                tokens = tokenizer(tweet[0])
                if not set(tokens).isdisjoint({"食事制限", "ダイエット"}) and set(tokens).isdisjoint({"質問箱",}):
                    tweet_list.append(del_jp_stopwords(tokens))
    return tweet_list


def main(args):
    # モデルの学習
    # dbc = db_connect(join(current_dirname, 'tweet.db'))
    # tweet_list = select(dbc, 'jp_diet')
    # tweet_list.extend(select(dbc, 'jp_syokujiseigen'))
    # tweet_list_l = len(tweet_list)
    # batch_mask = np.random.choice(tweet_list_l, 2*tweet_list_l)
    # for i in batch_mask:
    #     tweet_list.append(tweet_list[i])
    # print("Number of tweet = {}".format(len(tweet_list)))
    # word_list = list(itertools.chain.from_iterable(tweet_list))
    # print("Number of word = {}".format(len(set(word_list))))
    # model = word2vec.Word2Vec(tweet_list,
    #                           size=300,
    #                           min_count=1,
    #                           window=1,
    #                           hs=1,
    #                           negative=5)
    # model.save(join(current_dirname, 'word2vec', 'word2vec.model'))
    # モデルの読み込み
    model = word2vec.Word2Vec.load(join(current_dirname, 'word2vec', 'word2vec.model'))
    if not args.n_word:
        print("\"{}\" is similar to:".format(args.p_word))
        results = model.wv.most_similar(positive=[args.p_word], topn=5)
    else:
        print("\"{}\" - \"{}\" is similar to:".format(args.p_word, args.n_word))
        results = model.wv.most_similar(positive=[args.p_word], negative=[args.n_word], topn=5)
    for result in results:
        print(result[0], result[1])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--p_word', type=str, default='ダイエット')
    parser.add_argument('--n_word', type=str)
    args = parser.parse_args()
    main(args)
