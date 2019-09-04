#!/usr/bin/env bash

# build
embed_path=../data2.2/
embed_path1=$embed_path/wiki.multi.en.vec
embed_path2=$embed_path/wiki.multi.de.vec
embed_path3=$embed_path/wiki.multi.fr.vec
embed_path4=$embed_path/wiki.multi.es.vec
data_path=../data2.2/
data0=$data_path/en_train.conllu
data1=$data_path/en_dev.conllu
data2=$data_path/en_test.conllu
data3=$data_path/de_test.conllu
data4=$data_path/fr_test.conllu
data5=$data_path/es_test.conllu

PYTHONPATH=../src/ CUDA_VISIBLE_DEVICES= python2 ../src/examples/vocab/build_joint_vocab_embed.py \
--embed_paths $embed_path1 $embed_path2 $embed_path3 $embed_path4 \
--embed_lang_ids en de fr es \
--data_paths $data0 $data1 $data2 $data3 $data4 $data5 \
--model_path ./model/

## simpler one
#embed_path=../data2.2/
#embed_path1=$embed_path/wiki.multi.en.vec
#embed_path2=$embed_path/wiki.multi.de.vec
#data_path=../data2.2/
#data0=$data_path/en_train.conllu
#data1=$data_path/en_dev.conllu
#data2=$data_path/en_test.conllu
#data3=$data_path/de_test.conllu
#
#PYTHONPATH=../src/ CUDA_VISIBLE_DEVICES= python2 ../src/examples/vocab/build_joint_vocab_embed.py \
#--embed_paths $embed_path1 $embed_path2 \
#--embed_lang_ids en de \
#--data_paths $data0 $data1 $data2 $data3 \
#--model_path ./model/
