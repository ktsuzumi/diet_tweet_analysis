# 認知言語学レポート用スクリプト

「ダイエット」と「食事制限」におけるプロトタイプの変化の考察

共起ネットワークとWordCloud,Word2Vec

## 使い方

### 共起ネットワークとWordCloudを作る時

``
$ python3 make_net_cloud.py --table dbのテーブル名
``

### Word2Vecのコサイン類似度を試す時

ダイエットのコサイン類似度

``
$ python3  word2vec.py
``

足し算とか引き算(複数指定可)

``
$ python3  word2vec.py --p_word 足したい単語 --n_word 引きたい単語
``

※dbは公開してない

# 参考サイト

https://irukanobox.blogspot.com/2019/10/python.html
