#!/usr/bin/env bash
aws cloudformation update-stack --stack-name ledstrip-pipeline --template-body file://infra_s3pipeline.yaml --parameters file://param_s3pipeline.json --capabilities CAPABILITY_NAMED_IAM --profile awsapp_admin
