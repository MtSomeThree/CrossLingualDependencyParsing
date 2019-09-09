#!/usr/bin/env bash

#
function run_lang () {

echo "======================"
echo "Running with lang = $1"

cur_lang=$1

CUDA_VISIBLE_DEVICES=7 python ../src/examples/analyze.py --parser biaffine --ordered --gpu \
--punctuation 'PUNCT' 'SYM' --out_filename analyzer.$cur_lang.out --model_name 'network.pt' \
--test "../data2.2/${cur_lang}_test.conllu" --model_path "./model/final_gtrans.sh_1/" --extra_embed "../data2.2/wiki.multi.${cur_lang}.vec" \
--decode proj --constraints_method Lagrange --constraint_file "./constraints.txt" --ratio_file "./model/constraints/${cur_lang}.constraint" \
--mt_log "./log/${cur_lang}.log"

}

for lang in pl sv de sl no sk
do
    run_lang $lang;
done
