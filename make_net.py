from os.path import join, abspath, dirname
import sqlite3
import argparse
import nltk
import MeCab
from itertools import combinations, dropwhile
from collections import Counter, OrderedDict
import networkx as nx
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from nltk.corpus import stopwords as nltk_stopwords
from networkx.drawing import nx_agraph
from wordcloud import WordCloud
import itertools
from os.path import expanduser

matplotlib.use('Agg')
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
    word_list = []
    while node:
        features = node.feature.split(",")
        features = [features[i] if len(features) > i else None for i in range(0, 9)]
        if features[0] in ['名詞', '形容詞']:
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


def word2pair(tweet_list, min_count=5):
    # 全単語ペアのリスト
    pair_all = []

    for tweet in tweet_list:
        # combinationsを使うと順番が違うだけのペアは重複しない
        pairs = list(combinations(set(tweet), 2))
        for i, pair in enumerate(pairs):
            pairs[i] = tuple(sorted(pair))
        pair_all += pairs
    pair_count = Counter(pair_all)
    for key, count in dropwhile(lambda key_count: key_count[1] >= min_count, pair_count.most_common()):
        del pair_count[key]
    return pair_count


def pair2jaccard(pair_count, tweet_list, edge_th=0.4):
    # jaccard係数を計算

    # 単語ごとの出現章数
    word_count = Counter()
    for tweet in tweet_list:
        word_count += Counter(set(tweet))

    # 単語ペアごとのjaccard係数を計算
    jaccard_coef = []
    for pair, cnt in pair_count.items():
        jaccard_coef.append(cnt / (word_count[pair[0]] + word_count[pair[1]] - cnt))

    # jaccard係数がedge_th未満の単語ペアを除外
    jaccard_dict = OrderedDict()
    for (pair, cnt), coef in zip(pair_count.items(), jaccard_coef):
        if coef >= edge_th:
            jaccard_dict[pair] = coef
            # print(pair, cnt, coef, word_count[pair[0]], word_count[pair[1]], sep='\t')

    return jaccard_dict, word_count


def build_network(jaccard_dict, word_count, table):
    # 共起ネットワークを作成
    # print(jaccard_dict)
    G = nx.Graph()

    #  接点／単語（node）の追加
    # ソートしないとネットワーク図の配置が実行ごとに変わる
    nodes = sorted(set([j for pair in jaccard_dict.keys() for j in pair]))
    G.add_nodes_from(nodes)

    print('Number of nodes =', G.number_of_nodes())

    #  線（edge）の追加
    for pair, coef in jaccard_dict.items():
        G.add_edge(pair[0], pair[1], weight=coef)

    print('Number of edges =', G.number_of_edges())

    plt.figure(figsize=(5, 5))

    # nodeの配置方法の指定
    seed = 0
    np.random.seed(seed)
    # pos = nx.spring_layout(G, k=0.3, seed=seed)
    pos = nx_agraph.graphviz_layout(
        G,
        prog='neato',
        args='-Goverlap="scalexy" -Gsep="+6" -Gnodesep=0.8 -Gsplines="polyline" -GpackMode="graph" -Gstart={}'.format(
            seed))

    # nodeの大きさと色をページランクアルゴリズムによる重要度により変える
    pr = nx.pagerank(G)
    # node_count = [word_count['{}'.format(node)] for node in nodes]
    # c_max = np.max(node_count)
    # c_min = np.min(node_count)
    # node_count = [(x-c_min)/(c_max-c_min) for x in node_count]
    nx.draw_networkx_nodes(
        G,
        pos,
        node_color=list(pr.values()),
        cmap=plt.cm.rainbow,
        alpha=0.7,
        node_size=[10000 * v for v in list(pr.values())])

    # 日本語ラベルの設定
    nx.draw_networkx_labels(G, pos, fontsize=15, font_family='IPAexGothic', font_weight='bold')

    # エッジ太さをJaccard係数により変える
    edge_width = [d['weight'] * 6 for (u, v, d) in G.edges(data=True)]
    nx.draw_networkx_edges(G, pos, alpha=0.7, edge_color='darkgrey', width=edge_width)

    plt.axis('off')
    plt.tight_layout()

    plt.savefig(join(current_dirname, 'image', '{}.png'.format(table)), bbox_inches='tight')


def main(args):
    dbc = db_connect(join(current_dirname, 'tweet.db'))
    tweet_list = select(dbc, args.table)
    print("Number of tweet = {}".format(len(tweet_list)))
    # WordCloud
    word_list = list(itertools.chain.from_iterable(tweet_list))
    text = ' '.join(word_list)
    home = expanduser("~")
    font_path = join(home, "Library", "Fonts","RictyDiminished-Bold.ttf")
    wc = WordCloud(background_color="white", collocations=False, font_path=font_path, width=800, height=500).generate(text)
    wc.to_file(join(current_dirname, 'image', '{}_wc.png'.format(args.table)))
    # 共起ネットワーク
    jaccard_dict, word_count = pair2jaccard(word2pair(tweet_list, min_count=10), tweet_list, edge_th=0.05)
    build_network(jaccard_dict, word_count, args.table)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--table', type=str, choices=['en_diet', 'jp_diet', 'jp_syokujiseigen'], default='jp_diet')
    args = parser.parse_args()
    main(args)
