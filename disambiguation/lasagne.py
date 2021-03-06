__author__ = 'yutao'

import lasagne
import theano.tensor as T
import pickle
from theano import sparse
import numpy as np
import random
import theano
from collections import defaultdict as dd

aff_vocab = pickle.load(open("aff_vocab.pkl", "rb"))
title_vocab = pickle.load(open("title_vocab.pkl", "rb"))
venue_vocab = pickle.load(open("venue_vocab.pkl", "rb"))
attr = pickle.load(open("attr.pkl", "rb"))
authors_map = pickle.load(open("authors_map.pkl", "rb"))
pub_author_map = pickle.load(open("pub_author_map.pkl", "rb"))

aff_idx = dict((c[0], i+1) for i, c in enumerate(aff_vocab))
title_idx = dict((c[0], i+1) for i, c in enumerate(title_vocab))
venue_idx = dict((c[0], i+1) for i, c in enumerate(venue_vocab))

aff_vocab = dict(aff_vocab)
title_vocab = dict(title_vocab)
venue_vocab = dict(venue_vocab)

aff_maxlen = 50
title_maxlen = 200
venue_maxlen = 30

embed_dim = 10

batch_size = 100
g_batch_size = 10
neg_sample = 5

path_size = 5
window_size = 3

# author - paper pairs
X_ap = []
y_ap = []

# author pairs
X_aa = []
y_aa = []

def vectorize(data, word_idx, vocab):
    x = np.zeros((len(data), max(word_idx.values())+1), dtype=np.int32)
    for i, d in enumerate(data):
        if d:
            for f in d:
                x[i, word_idx[f]] = .1 / vocab[f]
    return x

f_aff = []
f_title = []
f_venue = []
idx_a = []
idx_p = []
for i, d in enumerate(attr):
    if d[0] == "pub":
        f_title.append(d[1])
        f_venue.append(d[2])
        f_aff.append([])
        idx_p.append(i)
        idx_a.append(i)
    elif d[0] == "author":
        f_aff.append(d[2])
        f_title.append([])
        f_venue.append([])
        idx_a.append(i)
        idx_p.append(i)

aff_data = vectorize(f_aff, aff_idx, aff_vocab)
title_data = vectorize(f_title, title_idx, title_vocab)
venue_data = vectorize(f_venue, venue_idx, venue_vocab)

def gen_feature_a():
    while True:
        idx = np.array(np.random.permutation((aff_data.shape[0])), dtype=np.int32)
        i = 0
        while i < idx.shape[0]:
            j = min(idx.shape[0], i + batch_size)
            yield aff_data[idx[i: j]], idx[i: j]
            i = j

def gen_feature_p():
    while True:
        idx = np.array(np.random.permutation((title_data.shape[0])), dtype=np.int32)
        i = 0
        while i < idx.shape[0]:
            j = min(idx.shape[0], i + batch_size)
            yield title_data[idx[i: j]], venue_data[idx[i: j]], idx[i: j]
            i = j


def gen_graph_ap():
    graph = dd(list)
    num_ver = len(attr)
    for e in pub_author_map:
        graph[e[0]].append(e[1])
        graph[e[1]].append(e[1])
    for e in authors_map:
        graph[e[0]].append(e[1])
        graph[e[1]].append(e[1])

    while True:
        idx = np.random.permutation(num_ver)
        i = 0
        while i < idx.shape[0]:
            g = []
            gy = []
            j = min(idx.shape[0], i+g_batch_size)
            for k in idx[i: j]:
                if len(graph[k]) == 0:
                    continue
                path = [k]
                for _ in range(path_size):
                    path.append(random.choice(graph[path[-1]]))
                for l in range(len(path)):
                    for m in range(l-window_size, l + window_size + 1):
                        if m < 0 or m >= len(path):
                            continue
                        g.append([path[l], path[m]])
                        gy.append(1.0)
                        for k in range(neg_sample):
                            g.append((path[l], random.randint(0, num_ver-1)))
                            gy.append(-1.0)
            if len(g) == 0:
                break
            yield np.array(g, dtype=np.int32), np.array(gy, dtype=np.float32)
            i = j

def gen_graph_aa():
    graph = dd(list)
    num_ver = len(attr)
    for e in authors_map:
        graph[e[0]].append(e[1])
        graph[e[1]].append(e[1])

    while True:
        idx = np.random.permutation(num_ver)
        i = 0
        while i < idx.shape[0]:
            g = []
            gy = []
            j = min(idx.shape[0], i+g_batch_size)
            for k in idx[i: j]:
                if len(graph[k]) == 0:
                    continue
                path = [k]
                for _ in range(path_size):
                    path.append(random.choice(graph[path[-1]]))
                for l in range(len(path)):
                    for m in range(l-window_size, l + window_size + 1):
                        if m < 0 or m >= len(path):
                            continue
                        g.append([path[l], path[m]])
                        gy.append(1.0)
                        for k in range(neg_sample):
                            g.append((path[l], random.randint(0, num_ver-1)))
                            gy.append(-1.0)
            if len(g) == 0:
                break
            yield np.array(g, dtype=np.int32), np.array(gy, dtype=np.float32)
            i = j

def get_test_data():
    g = []
    gy = []
    for e in authors_map:
        g.append(e)
        gy.append(1.0)
        g.append((e[0], random.randint(0, len(attr)-1)))
        gy.append(0)
    return np.array(g, dtype=np.int32), np.array(gy, dtype=np.float32)


aff_var = T.imatrix('aff')
title_var = T.imatrix('title')
venue_var = T.imatrix('venue')
pub_idx = T.ivector("pub_idx")
author_idx = T.ivector("author_idx")

pairs = T.imatrix("pairs")
pairs_y = T.fvector("pairs_y")

aff_input_layer = lasagne.layers.InputLayer(shape=(None, max(aff_idx.values())+1), input_var=aff_var)
aff_input_layer = lasagne.layers.DenseLayer(aff_input_layer, embed_dim, nonlinearity=lasagne.nonlinearities.softmax)
title_input_layer = lasagne.layers.InputLayer(shape=(None, max(title_idx.values())+1), input_var=title_var)
title_input_layer = lasagne.layers.DenseLayer(title_input_layer, embed_dim, nonlinearity=lasagne.nonlinearities.softmax)
venue_input_layer = lasagne.layers.InputLayer(shape=(None, max(venue_idx.values())+1), input_var=venue_var)
venue_input_layer = lasagne.layers.DenseLayer(venue_input_layer, embed_dim, nonlinearity=lasagne.nonlinearities.softmax)


pairs_input_layer = lasagne.layers.InputLayer(shape=(None, 2), input_var=pairs)
embedding_layer_w = lasagne.layers.SliceLayer(pairs_input_layer, indices=0, axis=1)
embedding_layer_w = lasagne.layers.EmbeddingLayer(embedding_layer_w, input_size=len(attr), output_size=embed_dim)
embedding_layer_c = lasagne.layers.SliceLayer(pairs_input_layer, indices=1, axis=1)
embedding_layer_c = lasagne.layers.EmbeddingLayer(embedding_layer_c, input_size=len(attr), output_size=embed_dim)


embedding_layer_p = lasagne.layers.InputLayer(shape=(None, ), input_var=pub_idx)
embedding_layer_p = lasagne.layers.EmbeddingLayer(embedding_layer_p, input_size=len(attr), output_size=embed_dim, W=embedding_layer_w.W)
embedding_layer_a = lasagne.layers.InputLayer(shape=(None, ), input_var=author_idx)
embedding_layer_a = lasagne.layers.EmbeddingLayer(embedding_layer_a, input_size=len(attr), output_size=embed_dim, W=embedding_layer_w.W)

feature_layer_a = aff_input_layer
feature_layer_a = lasagne.layers.DenseLayer(feature_layer_a, embed_dim, nonlinearity=lasagne.nonlinearities.softmax)
feature_layer_p = title_input_layer#lasagne.layers.ElemwiseMergeLayer([title_input_layer, venue_input_layer], T.sum)
feature_layer_p = lasagne.layers.DenseLayer(feature_layer_p, embed_dim, nonlinearity=lasagne.nonlinearities.softmax)

feature_loss_a = lasagne.objectives.categorical_crossentropy(
        lasagne.layers.get_output(feature_layer_a),
        lasagne.layers.get_output(embedding_layer_a)
).mean()

feature_loss_p = lasagne.objectives.categorical_crossentropy(
    lasagne.layers.get_output(feature_layer_p),
    lasagne.layers.get_output(embedding_layer_p)
).mean()

graph_output_layer = lasagne.layers.ElemwiseMergeLayer([embedding_layer_w, embedding_layer_c], T.mul)
graph_output = lasagne.layers.get_output(graph_output_layer)

graph_loss = - T.log(T.nnet.sigmoid(T.sum(graph_output, axis=1) * pairs_y)).sum()

graph_params = lasagne.layers.get_all_params(graph_output_layer, trainable=True)
graph_updates = lasagne.updates.sgd(graph_loss, graph_params, learning_rate=0.1)

train_graph = theano.function([pairs, pairs_y], graph_loss, updates=graph_updates, on_unused_input="warn")


feature_params_a = lasagne.layers.get_all_params(feature_layer_a)
feature_params_p = lasagne.layers.get_all_params(feature_layer_p)
updates_a = lasagne.updates.sgd(feature_loss_a, feature_params_a, learning_rate=0.1)
updates_p = lasagne.updates.sgd(feature_loss_p, feature_params_p, learning_rate=0.1)

train_feature_a = theano.function([aff_var, author_idx], feature_loss_a, updates=updates_a, on_unused_input="warn")
train_feature_p = theano.function([title_var, venue_var, pub_idx], feature_loss_p, updates=updates_p, on_unused_input="warn")

result = T.nnet.sigmoid(T.sum(graph_output, axis=1))
pos_result = T.ge(result, 0.5)
acc = T.mean(T.eq(pos_result, pairs_y))
tp = T.sum(T.mul(pos_result, pairs_y))
fp = T.sum(T.mul(pos_result, 1-pairs_y))
p = T.sum(T.ge(result, 0.5))
t = T.sum(pairs_y)

test_graph = theano.function([pairs, pairs_y], acc, on_unused_input="warn")
tp_graph = theano.function([pairs, pairs_y], tp, on_unused_input="warn")
fp_graph = theano.function([pairs, pairs_y], fp, on_unused_input="warn")
p_graph = theano.function([pairs, pairs_y], p, on_unused_input="warn")
n_graph = theano.function([pairs, pairs_y], t, on_unused_input="warn")
iter = 0
max_acc = 0
test_g, test_gy = get_test_data()

while True:

    g1, gy1 = next(gen_graph_ap())
    loss1 = train_graph(g1, gy1)
    g2, gy2 = next(gen_graph_ap())
    loss2 = train_graph(g2, gy2)
    f_a, f_idx_a = next(gen_feature_a())
    loss3 = train_feature_a(f_a, f_idx_a)
    f_t, f_v, f_idx_p = next(gen_feature_p())
    loss4 = train_feature_p(f_t, f_v, f_idx_p)
    print(iter, loss1, loss2, loss3, loss4)
    acc = test_graph(test_g, test_gy)
    tp1 = tp_graph(test_g, test_gy)
    fp1 = fp_graph(test_g, test_gy)
    s1 = p_graph(test_g, test_gy)
    s2 = n_graph(test_g, test_gy)
    max_acc = max(acc, max_acc)

    print(acc, max_acc, "pre", tp1 / s1, "rec", fp1 / s2)
    iter += 1