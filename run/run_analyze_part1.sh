#!/usr/bin/env bash

#
function run_lang () {

echo "======================"
echo "Running with lang = $1"

cur_lang=$1

# try them both, will fail on one

CUDA_VISIBLE_DEVICES=0 python ../src/examples/analyze.py --parser biaffine --ordered --gpu \
--punctuation 'PUNCT' 'SYM' --out_filename analyzer.$cur_lang.out --model_name 'network.pt' \
--test "../data2.2/${cur_lang}_test.conllu" --model_path "./model/final_gtrans.sh_1/" --extra_embed "../data2.2/wiki.multi.${cur_lang}.vec" \
--decode mst --constraints_method PR --constraint_file "./constraints2.txt" --ratio_file "./model/constraints/${cur_lang}.constraint" --mt_log "./log/${cur_lang}.log" --tolerance 1.0 \
--summary_log "./summary.log"

}

for lang in cs de pl bg lv la et sv sl da no nl sk;
do
    run_lang $lang;
done

# RGPU=0 bash ../src/examples/run/run_analyze.sh |& tee log_test
# see the results?
# -> cat log_test | grep -E "python2|Running with lang|uas|Error"
# -> cat log_test | grep -E "Running with lang|uas"
# -> cat log_test | grep -E "Running with lang|test Wo Punct"
