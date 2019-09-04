#!/usr/bin/env bash
CUDA_VISIBLE_DEVICES=$1 python2 examples/StackPointerParser.py --mode FastLSTM --num_epochs 1000 --batch_size 32 --decoder_input_size 256 \
 --hidden_size 200 --encoder_layers 6 --decoder_layers 1 \
 --pos_dim 100 --char_dim 100 --num_filters 100 --arc_space 512 --type_space 128 \
 --opt adam --learning_rate 0.001 --decay_rate 0.75 --epsilon 1e-4 --coverage 0.0 --gamma 0.0 --clip 5.0 \
 --schedule 20 --double_schedule_decay 5 \
 --p_in 0.33 --p_out 0.33 --p_rnn 0.33 0.33 --unk_replace 0.5 --label_smooth 1.0 --pos --beam 1 --prior_order inside_out \
 --grandPar --sibling --freeze --no_CoRNN \
 --word_embedding word2vec --word_path "../../../../kwchang/npeng/embeddings/bilingual/wiki.multi.en_es.joint.vec" --char_embedding random \
 --punctuation 'PUNCT' 'SYM' --pool_type weight --multi_head_attn --num_head 8 \
 --train "data/udt_google/English/en-ud-train.upos.conll" \
 --dev "data/udt_google/English/en-ud-dev.upos.conll" \
 --test "data/udt_google/Spanish/es-ud-test.upos.conll" \
 --model_path "models/parsing/stack_ptr_en_es_rnn_off/" --model_name 'network.pt'
