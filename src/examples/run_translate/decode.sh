#!/usr/bin/env bash

#
function run_lang () {

echo "======================"
echo "Running with lang = $1_$2"
echo "Going with params = $1_$2_$3_$4"

cur_lang=$1
test_path=$2
which_model=$3
model_path=$4

# try them both, will fail on one

if [ "$which_model" == "biaffine" ]; then

echo PYTHONPATH=../src/ CUDA_VISIBLE_DEVICES=$RGPU python2 ../src/examples/analyze.py --parser biaffine --ordered --gpu \
--punctuation 'PUNCT' 'SYM' --out_filename analyzer.$cur_lang.$which_set.out --model_name 'network.pt' \
--test ${test_path} --model_path ${model_path} --extra_embed "../data2.2_more/wiki.multi.${cur_lang}.vec" --extra_embed_src "../data2.2_more/wiki.multi.en.vec"

PYTHONPATH=../src/ CUDA_VISIBLE_DEVICES=$RGPU python2 ../src/examples/analyze.py --parser biaffine --ordered --gpu \
--punctuation 'PUNCT' 'SYM' --out_filename analyzer.$cur_lang.$which_set.out --model_name 'network.pt' \
--test ${test_path} --model_path ${model_path} --extra_embed "../data2.2_more/wiki.multi.${cur_lang}.vec" --extra_embed_src "../data2.2_more/wiki.multi.en.vec"

elif [ "$which_model" == "stackptr" ]; then

echo PYTHONPATH=../src/ CUDA_VISIBLE_DEVICES=$RGPU python2 ../src/examples/analyze.py --parser stackptr --beam 5 --ordered --gpu \
--punctuation 'PUNCT' 'SYM' --out_filename analyzer.$cur_lang.$which_set.out --model_name 'network.pt' \
--test ${test_path} --model_path ${model_path} --extra_embed "../data2.2_more/wiki.multi.${cur_lang}.vec" --extra_embed_src "../data2.2_more/wiki.multi.en.vec"

PYTHONPATH=../src/ CUDA_VISIBLE_DEVICES=$RGPU python2 ../src/examples/analyze.py --parser stackptr --beam 5 --ordered --gpu \
--punctuation 'PUNCT' 'SYM' --out_filename analyzer.$cur_lang.$which_set.out --model_name 'network.pt' \
--test ${test_path} --model_path ${model_path} --extra_embed "../data2.2_more/wiki.multi.${cur_lang}.vec" --extra_embed_src "../data2.2_more/wiki.multi.en.vec"

fi

}

# =====

echo "Run them all with () $1_$2"

#which_model=$1
#model_path=$2

# running with which dev, which set?
for cur_lang in ar bg ca zh hr cs da nl en et "fi" fr de he hi id it ja ko la lv no pl pt ro ru sk sl es sv uk;
do
test_file="${cur_lang}_test.dict.conllu"
#test_file="${cur_lang}_test.near.conllu"
if [ -f $test_file ]; then
    run_lang $cur_lang $test_file $1 $2;
fi
done

# RGPU=0 bash ../src/examples/run_more/run_analyze.sh |& tee log_test
# see the results?
# -> cat log_test | grep -E "python2|Running with lang|uas|Error"
# -> cat log_test | grep -E "Running with lang|uas"
# -> cat log_test | grep -E "Running with lang|test Wo Punct"
# -> cat log_test | python3 print_log_test.py

# RGPU=0 bash -v decode.sh biaffine ./gtrans1 |& tee log.dict.gtrans1
