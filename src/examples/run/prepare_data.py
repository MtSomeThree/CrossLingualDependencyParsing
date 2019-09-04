#

# 'bg ca cs nl en fr de it no ro ru es pt sv zh ja'
LANGUAGE_LIST = (
    # ACL17
    ["bg", ["UD_Bulgarian-BTB"]],
    ["ca", ["UD_Catalan-AnCora"]],
    ["cs", ["UD_Czech-PDT", "UD_Czech-CAC", "UD_Czech-CLTT", "UD_Czech-FicTree"]],
    ["nl", ["UD_Dutch-Alpino", "UD_Dutch-LassySmall"]],
    ["en", ["UD_English-EWT"]],
    ["fr", ["UD_French-GSD"]],
    ["de", ["UD_German-GSD"]],
    ["it", ["UD_Italian-ISDT"]],
    ["no", ["UD_Norwegian-Bokmaal", "UD_Norwegian-Nynorsk"]],
    ["ro", ["UD_Romanian-RRT"]],
    ["ru", ["UD_Russian-SynTagRus"]],
    ["es", ["UD_Spanish-GSD", "UD_Spanish-AnCora"]],
    # AAAI16
    ["pt", ["UD_Portuguese-Bosque", "UD_Portuguese-GSD"]],
    ["sv", ["UD_Swedish-Talbanken"]],
    # Others
    ["zh", ["UD_Chinese-GSD"]],
    ["ja", ["UD_Japanese-GSD"]],
    # ["ja", ["UD_Japanese-GSD", "UD_Japanese-BCCWJ"]],     # no texts for BCCWJ
)

TRAIN_LANG = "en"

# confs
UD2_DIR = "../data/ud-treebanks-v2.2/"
OUT_DIR = "./data2.2/"

# ===== help
import os, subprocess, sys, gzip

printing = lambda x: print(x, file=sys.stderr, flush=True)

def system(cmd, pp=False, ass=False, popen=False):
    if pp:
        printing("Executing cmd: %s" % cmd)
    if popen:
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        n = p.wait()
        output = str(p.stdout.read().decode())
    else:
        n = os.system(cmd)
        output = None
    if pp:
        printing("Output is: %s" % output)
    if ass:
        assert n==0
    return output

def zopen(filename, mode='r', encoding="utf-8"):
    if filename.endswith('.gz'):
        # "t" for text mode of gzip
        return gzip.open(filename, mode+"t", encoding=encoding)
    else:
        return open(filename, mode, encoding=encoding)
# =====

#
def deal_conll_file(fin, fout):
    for line in fin:
        line = line.strip()
        fields = line.split("\t")
        if len(line) == 0:
            fout.write("\n")
        else:
            try:
                z = int(fields[0])
                fields[4] = fields[3]
                fields[3] = "_"
                fout.write("\t".join(fields)+"\n")
            except:
                pass

#
def main():
    for lang, fnames in LANGUAGE_LIST:
        printing("Dealing with lang %s." % lang)
        for curf in ["train", "dev", "test"]:
            out_fname = "%s/%s_%s.conllu" % (OUT_DIR, lang, curf)
            fout = zopen(out_fname, "w")
            for fname in fnames:
                last_name = fname.split("-")[-1].lower()
                fin = zopen("%s/%s/%s_%s-ud-%s.conllu" % (UD2_DIR, fname, lang, last_name, curf))
                deal_conll_file(fin, fout)
                fin.close()
            fout.close()
            # stat
            system('cat %s | grep -E "^$" | wc' % out_fname, pp=True)
            system('cat %s | grep -Ev "^$" | wc' % out_fname, pp=True)
            system("cat %s | grep -Ev '^$' | cut -f 5 -d $'\t'| grep -Ev 'PUNCT|SYM' | wc" % out_fname, pp=True)
        system("wget -nc -O %s/wiki.multi.%s.vec https://s3.amazonaws.com/arrival/embeddings/wiki.multi.%s.vec" % (OUT_DIR, lang, lang), pp=True)

if __name__ == '__main__':
    main()

# python3 prepare_data.py |& grep -v "s$" | tee data2.2/log
