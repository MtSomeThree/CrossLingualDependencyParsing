#!/usr/bin/env bash

#
function run_lang () {

echo "======================"
echo "Running with lang = $1"

cur_lang=$1

# try them both, will fail on one

echo PYTHONPATH=../src/ CUDA_VISIBLE_DEVICES=$RGPU python2 ../src/examples/analyze.py --parser biaffine --ordered --gpu \
--punctuation 'PUNCT' 'SYM' --out_filename analyzer.$cur_lang.out --model_name 'network.pt' \
--test "../data2.2/${cur_lang}_test.conllu" --model_path "./model/" --extra_embed "../data2.2/wiki.multi.${cur_lang}.vec"
 
CUDA_VISIBLE_DEVICES=1 python ../src/examples/analyze.py --parser biaffine --ordered --gpu \
--punctuation 'PUNCT' 'SYM' --out_filename analyzer.$cur_lang.out --model_name 'network.pt' \
--test "../data2.2/${cur_lang}_test.conllu" --model_path "./model/final_gtrans.sh_1/" --extra_embed "../data2.2/wiki.multi.${cur_lang}.vec" \
--decode ilp --constraints_method Lagrange --constraint_file "./constraints.txt" --ratio_file "./model/constraints/${cur_lang}.constraint" --mt_log "./log/${cur_lang}.log"

#echo PYTHONPATH=../src/ CUDA_VISIBLE_DEVICES=$RGPU python2 ../src/examples/analyze.py --parser stackptr --beam 5 --ordered --gpu \
#--punctuation 'PUNCT' 'SYM' --out_filename analyzer.$cur_lang.out --model_name 'network.pt' \
#--test "../data2.2/${cur_lang}_test.conllu" --model_path "./model/" --extra_embed "../data2.2/wiki.multi.${cur_lang}.vec"
#
#PYTHONPATH=../src/ CUDA_VISIBLE_DEVICES=$RGPU python2 ../src/examples/analyze.py --parser stackptr --beam 5 --ordered --gpu \
#--punctuation 'PUNCT' 'SYM' --out_filename analyzer.$cur_lang.out --model_name 'network.pt' \
#--test "../data2.2/${cur_lang}_test.conllu" --model_path "./model/" --extra_embed "../data2.2/wiki.multi.${cur_lang}.vec"

echo PYTHONPATH=../src/ CUDA_VISIBLE_DEVICES=$RGPU python2 ../src/examples/analyze.py --parser stackptr --beam 16 --ordered --gpu \
--punctuation 'PUNCT' 'SYM' --out_filename analyzer.$cur_lang.out --model_name 'network.pt' \
--test "../data2.2/${cur_lang}_test.conllu" --model_path "./model/" --extra_embed "../data2.2/wiki.multi.${cur_lang}.vec"

#PYTHONPATH=../src/ CUDA_VISIBLE_DEVICES=$RGPU python2 ../src/examples/analyze.py --parser stackptr --beam 16 --ordered --gpu \
#--punctuation 'PUNCT' 'SYM' --out_filename analyzer.$cur_lang.out --model_name 'network.pt' \
#--test "../data2.2/${cur_lang}_test.conllu" --model_path "./model/" --extra_embed "../data2.2/wiki.multi.${cur_lang}.vec"

}

# example debug
#PYTHONPATH=../src/ CUDA_VISIBLE_DEVICES=1 python2 -m pdb ../src/examples/analyze.py --parser biaffine --ordered --gpu \
#--punctuation 'PUNCT' 'SYM' --out_filename analyzer.ca.out --model_name 'network.pt' \
#--test "../data2.2/ca_test.conllu" --model_path "../../branch0826/r0908_g100/model/" --extra_embed "../data2.2/wiki.multi.ca.vec"

# RGPU=0 bash -v ../src/examples/run/run_analyze.sh biaffine ca

for lang in en no sv fr pt da es it hr ca pl uk sl nl bg ru de he cs ro sk id lv fi et zh ar la ko hi ja;
do
    run_lang $lang;
done

# RGPU=0 bash ../src/examples/run/run_analyze.sh |& tee log_test
# see the results?
# -> cat log_test | grep -E "python2|Running with lang|uas|Error"
# -> cat log_test | grep -E "Running with lang|uas"
# -> cat log_test | grep -E "Running with lang|test Wo Punct"
