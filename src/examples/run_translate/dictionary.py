#

import sys
import os

ENGLISH_PREFIX = "!en_"

def main(input_file, output_file, input_lang):
    print("Change with dictionary for lang=" + input_lang)
    os.system("wget https://s3.amazonaws.com/arrival/dictionaries/%s-en.txt" % input_lang)
    with open("%s-en.txt" % input_lang) as fd:
        dictionary = {}
        for line in fd:
            w_input, w_en = line.split()
            if w_input in dictionary:
                print("repeat %s: %s -> %s" % (w_input, dictionary[w_input], w_en))
            dictionary[w_input] = w_en
    # change the file
    num_word, num_changed = 0, 0
    with open(input_file) as fd, open(output_file, "w") as wfd:
        for line in fd:
            fileds = line.split("\t")
            if len(fileds) == 10:
                num_word += 1
                w = fileds[1]
                if w in dictionary:
                    cc = ENGLISH_PREFIX + dictionary[w]
                    fileds[1] = cc
                    num_changed += 1
                elif str.lower(w) in dictionary:
                    cc = ENGLISH_PREFIX + dictionary[str.lower(w)]
                    fileds[1] = cc
                    num_changed += 1
                wfd.write("\t".join(fileds))
            else:
                wfd.write(line)
    print("Read %s, changed %s, perc=%s." % (num_word, num_changed, num_changed/(num_word+0.)))

if __name__ == '__main__':
    main(*sys.argv[1:])
