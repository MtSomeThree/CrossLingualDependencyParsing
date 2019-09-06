# Target Language-Aware Constrained Inference for Cross-lingual Dependency Parsing
Here we have the code and models for the following paper
[Target Language-Aware Constrained Inference for Cross-lingual Dependency Parsing](https://arxiv.org/abs/1909.01482) by Tao Meng, Nanyun Peng and Kai-Wei Chang published in EMNLP 2019.

**This repository is still under construction**

- ### Abstract
Prior work on cross-lingual dependency parsing often focuses on capturing the commonalities between source and target languages and overlooks the potential of leveraging linguistic properties of the languages to facilitate the transfer. In this paper, we show that weak supervisions of linguistic knowledge for the target languages can improve a cross-lingual graph-based dependency parser substantially. Specifically, we explore several types of corpus linguistic statistics and compile them into corpus-wise constraints to guide the inference process during the test time. We adapt two techniques, Lagrangian relaxation and posterior regularization, to conduct inference with corpus-statistics constraints. Experiments show that the Lagrangian relaxation and posterior regularization inference improve the performances on 15 and 17 out of 19 target languages, respectively. The improvements are especially significant for target languages that have different word order features from the source language. 

**About data**

You should download the UD Tree Bank and multilingual embedding data from PLACEHOLDER and save them in ./data2.2 first. 

**How to use it**

We have two techniques to incorporate the corpus-wise constraints: Lagrangian relaxation and posterior relaxation. 
