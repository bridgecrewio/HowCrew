# Setup Flow Logs in your VPCs
"VPC Flow Logs is a feature that enables you to capture information about the IP traffic going to and from network interfaces in your VPC. Flow log data can be published to Amazon CloudWatch Logs and Amazon S3." (source: [here](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html))

The following tool enables:
 1. Detection of VPC's without flow log audit enabled
 2. Remediation by enabling auditing of all new VPC's into a single new s3 bucket with lifecycle rule of 365 days.
## Pre requisites:
* Valid access keys at `~/.aws/credentials` with a default profile configured or  matching [AWS Environment Variables](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-envvars.html)  
* `Python` and `Pipenv` installed on the host running the tool

## Install
 
```bash
git clone https://github.com/bridgecrewio/HowCrew.git
cd HowCrew/
pipenv install
pipenv run python setup-vpc-flow-logs/setup_vpc_flow_logs.py --help
```
## How To Use
#### Help output sample
```
$ pipenv run python setup-vpc-flow-logs/setup_vpc_flow_logs.py --help
  usage: setup_vpc_flow_logs.py [-h]
                                {describe_vpcs_flow_log,enable_flow_logs} ...
  
  positional arguments:
    {describe_vpcs_flow_log,enable_flow_logs}
      describe_vpcs_flow_log
                          List all vpc instances and their flow log status along
                          side related region and tags.
      enable_flow_logs    Enables flow logs to VPCs that do not have flow log
                          enabled
  
  optional arguments:
    -h, --help            show this help message and exit

```
## Script execution steps:
### Command: describe_vpcs_flow_log 
```bash
pipenv run python setup-vpc-flow-logs/setup_vpc_flow_logs.py describe_vpcs_flow_log
```
#### Sample Output
```
| VpcId    | Flow log Enabled |  Region   | Tags                              |
|----------+------------------+-----------+-----------------------------------|
| vpc-09aa | TRUE             | us-west-2 | {cf-stack=app-stack},{stage=prod} |
| vpc-09bb | TRUE             | us-west-2 | {cf-stack=db-stack},{stage=dev}   |
| vpc-09cc | FALSE            | us-east-1 | {cf-stack=es-stack}               |

```
### Command: enable_flow_logs
#### Help output sample
```$ pipenv run python setup-vpc-flow-logs/setup_vpc_flow_logs.py enable_flow_logs --help
   usage: setup_vpc_flow_logs.py enable_flow_logs [-h] [-b BUCKET]
   
   optional arguments:
     -h, --help            show this help message and exit
     -b BUCKET, --bucket BUCKET
                           determines the name of the new flow log bucket. All
                           flow logs will be listed in the path pattern: bucket_A
                           RN/optional_folder/AWSLogs/aws_account_id/vpcflowlogs/
                           region/year/month/day/aws_account_id_vpcflowlogs_regio
                           n_flow_log_id_timestamp_hash.log.gz Bucket is created
                           with lifecycle rule to expire logs older then 365 days. 
                           Bucket will have versioning turned on.
                           Bucket will have Block all public access turned on.
                           NOTICE: flow logs will be created for all VPCs that do not have one 
```
#### Sample Output
Flow logs configured for all VPCs that did not have one enabled:

![vpc flow log](https://raw.githubusercontent.com/bridgecrewio/HowCrew/master/setup-vpc-flow-logs/images/vpc_with_flowlog.png)

A new s3 bucket with vpc flow logs:

![vpc flow log s3 bucket](https://raw.githubusercontent.com/bridgecrewio/HowCrew/master/setup-vpc-flow-logs/images/s3_bucket.png)

Lifecycle expiration policy on the s3 bucket:

![bucket lifecycle](https://raw.githubusercontent.com/bridgecrewio/HowCrew/master/setup-vpc-flow-logs/images/lifecycle.png)


#### Investigating VPC Flow log
For forensic purposes, you can configure to view VPC flow data via AWS Athena (or any other forensic tool).
For further details see the [official guide]( https://docs.aws.amazon.com/athena/latest/ug/vpc-flow-logs.html).

