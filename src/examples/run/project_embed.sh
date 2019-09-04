#!/usr/bin/env bash

# project for zh & ja

# in the data2.2 directory

# first get the codes
git clone https://github.com/facebookresearch/MUSE

for lang in ja zh;
do
echo "dealing with $lang"
# monoligual embeddings
wget -nc https://s3-us-west-1.amazonaws.com/fasttext-vectors/wiki.$lang.vec
# dictionary
wget -nc https://s3.amazonaws.com/arrival/dictionaries/$lang-en.0-5000.txt
wget -nc https://s3.amazonaws.com/arrival/dictionaries/$lang-en.5000-6500.txt
# project
CUDA_VISIBLE_DEVICES=$RGPU python2 MUSE/supervised.py --src_lang $lang --tgt_lang en --src_emb wiki.$lang.vec --tgt_emb wiki.multi.en.vec --n_refinement 5 --dico_train $lang-en.0-5000.txt --dico_eval $lang-en.5000-6500.txt
done
