#

# truncate and get the first N sentences from a conll file

import sys

def iter_mutlilines(fin):
    ret = []
    for line in fin:
        line = line.strip()
        # yield and reset
        if len(line) == 0 or line[0] == "#":
            if len(ret) > 0:
                yield ret
            ret = []
        else:
            ret.append(line)
    if len(ret) > 0:
        yield ret

def main():
    in_file, out_file, N, MaxLen = sys.argv[1:]
    #
    c = 0
    c2 = 0
    N = int(N)
    MaxLen = int(MaxLen)
    with open(in_file) as fin, open(out_file, "w") as fout:
        for ones in iter_mutlilines(fin):
            if c2 < N and len(ones)<=MaxLen:
                c2 += 1
                fout.write("\n".join(ones))
                fout.write("\n\n")
            c += 1
    print("Truncate %s -> %s: %s -> %s." % (in_file, out_file, c, c2))

# python3 truncate.py in.conllu out.conllu 4000 50
if __name__ == '__main__':
    main()
