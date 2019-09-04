#

import sys
import faiss
import torch
import json
import numpy as np

ENGLISH_PREFIX = "!en_"

# =====
class FastVector:
    def __init__(self, path, norm=True):
        self.word2id = {}
        self.id2word = []
        print("Load embedding.")
        with open(path, 'r') as fd:
            (self.n_words, self.n_dim) = (int(x) for x in fd.readline().rstrip('\n').split(' '))
            self.embed = np.zeros((self.n_words, self.n_dim), dtype=np.float32)
            for i, line in enumerate(fd):
                elems = line.rstrip('\n').split(' ')
                self.word2id[elems[0]] = i
                self.embed[i] = elems[1:self.n_dim+1]
                self.id2word.append(elems[0])
        if norm:
            self.embed = FastVector.normalised(self.embed)
        print("Load embedding OK %d." % (len(self.id2word)))

    @staticmethod
    def normalised(mat, axis=-1, order=2):
        """Utility function to normalise the rows of a numpy array."""
        norm = np.linalg.norm(mat, axis=axis, ord=order, keepdims=True)
        norm[norm == 0] = 1
        return mat / norm

# inputs are two numpy array (which are already normed)
def _get_dict_from_csls(target_emb_path, eng_emb_path, hit_list, k=10):
    fv_target = FastVector(target_emb_path)
    fv_eng = FastVector(eng_emb_path)
    queries, keys = fv_target.embed, fv_eng.embed
    #
    hit_query_idxes = [fv_target.word2id[w] for w in hit_list if w in fv_target.word2id]
    # hit_queries = queries[hit_query_idxes]
    print("From hit words to hit embeds: %s -> %s" % (len(hit_list), len(hit_query_idxes)))
    #
    average_dist_keys = get_nn_avg_dist(queries, keys, k)
    # average_dist_queries = get_nn_avg_dist(keys, queries, k)
    #
    output_dict = {}
    for query_id in hit_query_idxes:
        scores = np.matmul(keys, queries[query_id]) * 2 - average_dist_keys
        min_key = np.argmax(scores)
        output_dict[fv_target.id2word[query_id]] = fv_eng.id2word[min_key]
    return output_dict

# from MUSE
def get_nn_avg_dist(emb, query, knn):
    """
    Compute the average distance of the `knn` nearest neighbors
    for a given set of embeddings and queries.
    Use Faiss if available.
    """
    if True:
        # emb = emb.cpu().numpy()
        # query = query.cpu().numpy()
        if hasattr(faiss, 'StandardGpuResources'):
            # gpu mode
            res = faiss.StandardGpuResources()
            config = faiss.GpuIndexFlatConfig()
            config.device = 1   # GPU1
            index = faiss.GpuIndexFlatIP(res, emb.shape[1], config)
        else:
            # cpu mode
            index = faiss.IndexFlatIP(emb.shape[1])
        index.add(emb)
        distances, _ = index.search(query, knn)
        return distances.mean(1)
    else:
        bs = 1024
        all_distances = []
        emb = emb.transpose(0, 1).contiguous()
        for i in range(0, query.shape[0], bs):
            distances = query[i:i + bs].mm(emb)
            best_distances, _ = distances.topk(knn, dim=1, largest=True, sorted=True)
            all_distances.append(best_distances.mean(1).cpu())
        all_distances = torch.cat(all_distances)
    return all_distances.numpy()

# =====

def main(input_file, output_file, input_lang):
    print("Dealing with "+input_lang)
    # filter words
    hit_set = set()
    with open(input_file) as fd:
        for line in fd:
            fileds = line.split("\t")
            if len(fileds) == 10:
                hit_set.add(fileds[1])
                hit_set.add(str.lower(fileds[1]))
    print("Filtered word type = %d" % len(hit_set))
    hit_list = sorted(list(hit_set))
    #
    # TODO: fixd path
    try:
        with open("knn.%s-en.json" % input_lang) as fd:
            dictionary = json.load(fd)
    except:
        # debug
        # dictionary = _get_dict_from_csls("test.%s.vec"%input_lang, "test.en.vec", hit_list)
        dictionary = _get_dict_from_csls("../data2.2_more/wiki.multi.%s.vec"%input_lang, "../data2.2_more/wiki.multi.en.vec", hit_list)
        with open("knn.%s-en.json" % input_lang, "w") as fd:
            json.dump(dictionary, fd)
    #
    # change the file (same as dictionary.py)
    num_word, num_changed = 0, 0
    with open(input_file) as fd, open(output_file, "w") as wfd:
        for line in fd:
            fileds = line.split("\t")
            if len(fileds) == 10:
                num_word += 1
                w = fileds[1]
                if w in dictionary:
                    cc = ENGLISH_PREFIX + dictionary[w]
                    fileds[1] = cc
                    num_changed += 1
                elif str.lower(w) in dictionary:
                    cc = ENGLISH_PREFIX + dictionary[str.lower(w)]
                    fileds[1] = cc
                    num_changed += 1
                wfd.write("\t".join(fileds))
            else:
                wfd.write(line)
    print("Read %s, changed %s, perc=%s." % (num_word, num_changed, num_changed/(num_word+0.)))

if __name__ == '__main__':
    main(*sys.argv[1:])

# python knn.py "../data2.2_more/fr_test.conllu" "./fr_test.near.conllu" fr
