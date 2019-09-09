# Target Language-Aware Constrained Inference for Cross-lingual Dependency Parsing
This repository contains the source code to reproduce the experiments in the EMNLP 2019 paper
[Target Language-Aware Constrained Inference for Cross-lingual Dependency Parsing](https://arxiv.org/abs/1909.01482) by Tao Meng, [Nanyun Peng](http://www.cs.jhu.edu/~npeng/) and [Kai-Wei Chang](http://web.cs.ucla.edu/~kwchang/).

- ### Abstract
Prior work on cross-lingual dependency parsing often focuses on capturing the commonalities between source and target languages and overlooks the potential of leveraging linguistic properties of the languages to facilitate the transfer. In this paper, we show that weak supervisions of linguistic knowledge for the target languages can improve a cross-lingual graph-based dependency parser substantially. Specifically, we explore several types of corpus linguistic statistics and compile them into corpus-wise constraints to guide the inference process during the test time. We adapt two techniques, Lagrangian relaxation and posterior regularization, to conduct inference with corpus-statistics constraints. Experiments show that the Lagrangian relaxation and posterior regularization inference improve the performances on 15 and 17 out of 19 target languages, respectively. The improvements are especially significant for target languages that have different word order features from the source language. 

- ### Data

Firstly, you should download the UD Tree Bank data from [Universal Dependencies v2](https://universaldependencies.org/) (.conllu files),
and multilingual embedding data from [FastText](https://fasttext.cc/docs/en/crawl-vectors.html) (.vec files) and save them in ./data2.2 first. Now in ./data2.2 we only have dummy files of Hebrew(he).

- ### Running experiments

**Requirements**

```bash
python == 2.7
pytorch == 0.3.1
```

**WALS settings**

To use WALS features to compile constraints, please refer to ./run/run_WALS.sh. The WALS is stored in pickle file WALS_extra.pkl. The model will automatically load the WALS features and compile them into C1,C2,C3 three corpus-wise constraints mentioned in paper.

```bash
./run/run_WALS.sh
```

```bash
Alternative arguments:
  --decode [proj/mst]     adding projective constraints or not
  --constraints_method [PR/Lagrange] 
                          algorithms
```


**oracle settings**

To use oracle settings, please refer to ./run/run_ratio.sh. It will load constraints in constraints.txt. The exact ratio is stored in ./run/model/constraint

```bash
./run/run_ratio.sh
```

```bash
Alternative arguments:
  --decode [proj/mst]     adding projective constraints or not
  --threshold THETA       the margin
```
