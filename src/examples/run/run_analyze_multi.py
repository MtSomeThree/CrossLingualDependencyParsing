#!/bin/python3

# run them all and print averaged

#

# TODO(?): strangely, things will get "blocked/stucked" when running this script,
# THUS, do not use this!

import sys, re, os, subprocess

def main():
    dir_name = os.path.dirname(os.path.abspath(__file__))
    run_shell = os.path.join(dir_name, "run_analyze.sh")
    their_uas = []
    their_las = []
    #
    cmd = "RGPU=$RGPU bash %s |& tee log_test" % run_shell
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    n = p.wait()
    output = str(p.stdout.read().decode())
    for line in output.split("\n"):
        cur_math = re.match("test Wo Punct.*uas: ([0-9.]+)%, las: ([0-9.]+)%", line)
        if cur_math:
            print(line)
            their_uas.append(float(cur_math.group(1)))
            their_las.append(float(cur_math.group(2)))
    #
    print("# ===== Finally")
    print("UAS: avg: %.3f, details: %s" % (sum(their_uas)/len(their_uas), their_uas))
    print("LAS: avg: %.3f, details: %s" % (sum(their_las)/len(their_las), their_las))

if __name__ == '__main__':
    main()
