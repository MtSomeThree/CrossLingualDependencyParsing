#!/usr/bin/env bash

# run supervised-parser for all languages

BASE_DIR=`pwd`

function run_one ()
{

echo "======================"
echo "Running with lang = $1"

cur_lang=$1

# set up
mkdir $BASE_DIR/zr_${cur_lang};
cd $BASE_DIR/zr_${cur_lang};
mkdir tmp model;

# build dict
PYTHONPATH=../src/ CUDA_VISIBLE_DEVICES= python2 ../src/examples/vocab/build_joint_vocab_embed.py \
--embed_paths ../data2.2_more/wiki.multi.${cur_lang}.vec \
--embed_lang_ids ${cur_lang} \
--data_paths ../${cur_lang}_train.conllu ../data2.2_more/${cur_lang}_{dev,test}.conllu \
--model_path ./model/ |& tee log_v

# run gtrans
PYTHONPATH=../src/ CUDA_VISIBLE_DEVICES=$RGPU python2 ../src/examples/GraphParser.py \
--mode FastLSTM \
--no_CoRNN \
--hidden_size 300 \
--num_layers 6 \
--d_k 64 \
--d_v 64 \
--arc_space 512 \
--type_space 128 \
--opt adam \
--decay_rate 0.75 \
--epsilon 1e-4 \
--gamma 0.0 \
--clip 5.0 \
--schedule 20 \
--double_schedule_decay 5 \
--use_warmup_schedule \
--check_dev 5 \
--unk_replace 0.5 \
--freeze \
--pos \
--multi_head_attn \
--num_head 8 \
--word_embedding word2vec \
--word_path './model/alphabets/joint_embed.vec' \
--char_embedding random \
--punctuation 'PUNCT' 'SYM' \
--train "../${cur_lang}_train.conllu" \
--dev "../data2.2_more/${cur_lang}_dev.conllu" \
--test "../data2.2_more/${cur_lang}_test.conllu" \
--vocab_path './model/' \
--model_path './model/' \
--model_name 'network.pt' \
--p_in 0.2 \
--p_out 0.2 \
--p_rnn 0.2 0.1 0.2 \
--learning_rate 0.0001 \
--num_epochs 500 \
--trans_hid_size 512 \
--pos_dim 50 \
--char_dim 50 \
--num_filters 50 \
--position_dim 0 \
--enc_clip_dist 10 \
--batch_size 80 |& tee log

# test on all languages

RGPU=$RGPU bash -v ../src/examples/run_more/run_analyze.sh test biaffine |& tee log_test

}

run_one $1

#for cur_lang in ar bg ca zh hr cs da nl en et "fi" fr de he hi id it ja ko la lv no pl pt ro ru sk sl es sv uk;
#do
#    run_one $cur_lang;
#done

# RGPU=2 bash -v run_other.sh en
