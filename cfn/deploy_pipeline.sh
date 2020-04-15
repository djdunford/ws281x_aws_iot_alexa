#!/usr/bin/env bash
aws cloudformation update-stack --stack-name ledstrip-pipeline-s3infra --template-body file://infra_s3pipeline.yml --parameters file://param_s3pipeline.json --capabilities CAPABILITY_NAMED_IAM --profile ledstrip_admin
