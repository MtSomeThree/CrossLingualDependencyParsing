#!/usr/bin/env bash

# train & test

mkdir tmp model; cp -r ../run_dict/model/alphabets/ ./model/;

#RGPU=1

PYTHONPATH=../src/ CUDA_VISIBLE_DEVICES=$RGPU python2 ../src/examples/StackPointerParser.py \
--mode FastLSTM \
--decoder_input_size 256 \
--hidden_size 512 \
--encoder_layers 3 \
--d_k 64 \
--d_v 64 \
--decoder_layers 1 \
--arc_space 512 \
--type_space 128 \
--opt adam \
--decay_rate 0.75 \
--epsilon 1e-4 \
--coverage 0.0 \
--gamma 0.0 \
--clip 5.0 \
--schedule 20 \
--double_schedule_decay 5 \
--use_warmup_schedule \
--check_dev 5 \
--unk_replace 0.5 \
--label_smooth 1.0 \
--beam 1 \
--freeze \
--pos \
--pool_type weight \
--multi_head_attn \
--num_head 8 \
--word_embedding word2vec \
--word_path './model/alphabets/joint_embed.vec' \
--char_embedding random \
--punctuation 'PUNCT' 'SYM' \
--train "../data2.2/en_train.conllu" \
--dev "../data2.2/en_dev.conllu" \
--test "../data2.2/de_test.conllu" \
--vocab_path './model/' \
--model_path './model/' \
--model_name 'network.pt' \
--p_in 0.33 \
--p_out 0.33 \
--p_rnn 0.33 0.33 \
--learning_rate 0.001 \
--num_epochs 1000 \
--trans_hid_size 512 \
--pos_dim 50 \
--char_dim 50 \
--num_filters 50 \
--input_concat_embeds \
--input_concat_position \
--position_dim 0 \
--prior_order left2right \
--grandPar \
--enc_clip_dist 10 \
--batch_size 32

#for beam in 1 5 8 10 16;
#do
#PYTHONPATH=../src/ CUDA_VISIBLE_DEVICES=$RGPU python2 ../src/examples/analyze.py --parser stackptr --beam $beam --ordered --gpu \
#--punctuation 'PUNCT' 'SYM' --out_filename analyzer_out --model_name 'network.pt' \
#--test "../data2.2/en_dev.conllu" --model_path "./model/"
#
#PYTHONPATH=../src/ CUDA_VISIBLE_DEVICES=$RGPU python2 ../src/examples/analyze.py --parser stackptr --beam $beam --ordered --gpu \
#--punctuation 'PUNCT' 'SYM' --out_filename analyzer_out --model_name 'network.pt' \
#--test "../data2.2/de_test.conllu" --model_path "./model/"
#done

RGPU=$RGPU python3 ../src/examples/run/run_analyze_multi.py

#
# b neuronlp2/transformer/multi_head_attn:104
# b neuronlp2/models/parsing:438

# run
# RGPU=2 bash -v go.sh |& tee log
