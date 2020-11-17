#!/bin/bash

LOCUST="/usr/local/bin/locust"
LOCUS_OPTS="-f /locust-tasks/tasks.py --host=$TARGET_HOST"
LOCUST_MODE=${LOCUST_MODE:-standalone}

if [[ "$LOCUST_MODE" = "master" ]]; then
    LOCUS_OPTS="$LOCUS_OPTS --master"
    if [[ "$LOCUST_STEP" = true ]]; then
      LOCUS_OPTS="$LOCUS_OPTS --step-load"
    fi
elif [[ "$LOCUST_MODE" = "worker" ]]; then
    LOCUS_OPTS="$LOCUS_OPTS --slave --master-host=$LOCUST_MASTER_HOST"
fi

echo "$LOCUST $LOCUS_OPTS"

$LOCUST $LOCUS_OPTS
