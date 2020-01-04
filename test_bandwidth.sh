#!/bin/bash -i

EXEC="mpimstw"
ARGS1="python -u src/run_perf_amb.py cifar10 fmb sgd 128 --last_step 100 --test_size 1"
ARGS2="python -u src/test_bandwidth.py"

log () { echo "$1"; }
run () { log ">> $1"; eval "$1"; }
exc () { run "$EXEC $1 $ARGS2 $2"; }

for len in '100' '10000' '100000' '1000000'; do
    for bcast in '--no_bcast' ''; do
        for barr in '--barrier' ''; do
            for i in 1 2 4 8 16 25 30 35 40 45 50 55 60 65 70 75 80 85 90 95 99; do
                exc $i "$len $barr $bcast";
                sleep 5s;
            done
        done
    done
done
