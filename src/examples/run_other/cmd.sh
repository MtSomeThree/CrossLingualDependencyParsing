#!/usr/bin/env bash


# prepare
for cur_lang in ar bg ca zh hr cs da nl en et "fi" fr de he hi id it ja ko la lv no pl pt ro ru sk sl es sv uk;
do
    python3 truncate.py "../data2.2_more/${cur_lang}_train.conllu" "./${cur_lang}_train.conllu" 4000
done

# run all
for cur_lang in ar bg ca zh hr cs da nl en et "fi" fr de he hi id it ja ko la lv no pl pt ro ru sk sl es sv uk;
do
    RGPU=0 bash -v run_other.sh ${cur_lang}
done

# actual run with groups
# Server1(N)
for cur_lang in ar bg ca zh hr cs da nl;
do
    RGPU=1 bash -v run_other.sh ${cur_lang}
done
# Server1(N)
for cur_lang in en et "fi" fr de he hi id;
do
    RGPU=2 bash -v run_other.sh ${cur_lang}
done
# Server2(S)
for cur_lang in it ja ko la lv no pl pt;
do
    RGPU=0 bash -v run_other.sh ${cur_lang}
done
# Server3(C)
for cur_lang in ro ru sk sl es sv uk;
do
    RGPU=0 bash -v run_other.sh ${cur_lang}
done

# Run2: for those with errors in first run
for cur_lang in ar ca es pt;
do
    RGPU=0 bash -v run_other.sh ${cur_lang}
done
