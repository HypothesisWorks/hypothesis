#!/usr/bin/env bash

for _ in $(seq 5); do
    if $@ ; then 
        exit 0
    fi
    echo "Command failed. Retrying..."
    sleep $[ ( $RANDOM % 10)  + 1 ].$[ ( $RANDOM % 100) ]s
done

echo "Command failed five times. Giving up now"

exit 1
