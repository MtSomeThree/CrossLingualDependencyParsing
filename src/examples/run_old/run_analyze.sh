#!/usr/bin/env bash
CUDA_VISIBLE_DEVICES=$1 python2 examples/analyze.py --parser stackptr --beam 5 --ordered --gpu \
 --punctuation 'PUNCT' 'SYM' --out_filename analyzer_out \
 --test "data/udt_google/German/de-ud-test.upos.conll" \
 --model_path "models/parsing/stack_ptr_en_de_test/" --model_name 'network.pt'
