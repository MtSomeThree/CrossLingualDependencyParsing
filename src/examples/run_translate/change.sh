#!/usr/bin/env bash

# change target languages into english

# dictionary-based
for cur_lang in ar bg ca zh hr cs da nl en et "fi" fr de he hi id it ja ko la lv no pl pt ro ru sk sl es sv uk;
do
python3 dictionary.py "../data2.2_more/${cur_lang}_test.conllu" "./${cur_lang}_test.dict.conllu" "${cur_lang}"
done

# near-neighbour based
for cur_lang in ar bg ca zh hr cs da nl en et "fi" fr de he hi id it ja ko la lv no pl pt ro ru sk sl es sv uk;
do
python knn.py "../data2.2_more/${cur_lang}_test.conllu" "./${cur_lang}_test.near.conllu" "${cur_lang}"
done
