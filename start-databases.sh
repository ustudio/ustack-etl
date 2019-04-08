#!/usr/bin/env bash


if ! kubectl get namespace ustack-etl-testing > /dev/null 2>&1
then
    kubectl create namespace ustack-etl-testing
fi

kubectl create -f dev-deployment
