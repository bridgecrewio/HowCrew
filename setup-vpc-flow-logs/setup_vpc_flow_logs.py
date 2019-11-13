import boto3

from texttable import Texttable
import argparse
import logging
import os
import sys

# define logger
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# default region is used only to query global params. The code logic iterates over all regions
DEFAULT_REGION = "us-west-2"


def get_account_id():
    """

    :return: current AWS account id
    """
    # region name is not necessary here, using a default one
    client = boto3.client("sts", region_name=DEFAULT_REGION)
    return client.get_caller_identity()["Account"]


def get_all_vpcs(region):
    """

    :return: describe vpc for all active VPCs established in the current aws account
    """
    client = boto3.client('ec2', region_name=region)
    account_id = get_account_id()

    logger.debug("searching for VPCs in region {} for AWS account {}".format(region, account_id))
    return client.describe_vpcs(Filters=[
        {
            'Name': 'owner-id',
            'Values': [
                account_id,
            ]
        },
        {
            'Name': 'state',
            'Values': [
                'available',
            ]
        },

    ], MaxResults=1000)


def categorize_vpc_flow_log_status(region):
    """

    :param region: region to scan
    :return: dictionary containing list of vpc's with flow log enabled and once without
    """
    client = boto3.client('ec2', region_name=region)

    all_vpcs = get_all_vpcs(region)
    vpc_id_dict = {}
    if all_vpcs['Vpcs']:
        for x in all_vpcs['Vpcs']:
            vpc_id_dict[x['VpcId']] = x
    categorized_vpcs = {
        "flow_log_enabled": {},
        "flow_log_disabled": {}
    }

    all_flow_logs = client.describe_flow_logs()
    for flow_log in all_flow_logs['FlowLogs']:
        resource_id = flow_log['ResourceId']
        if resource_id in vpc_id_dict.keys() and flow_log['FlowLogStatus'] == 'ACTIVE':
            categorized_vpcs['flow_log_enabled'][resource_id] = vpc_id_dict[resource_id]
    for vpc_id, vpc_obj in vpc_id_dict.items():
        if vpc_id not in categorized_vpcs['flow_log_enabled'].keys():
            categorized_vpcs['flow_log_disabled'][vpc_id] = vpc_obj
    logger.debug("Region {} vpcs: flow_log_enabled:{} flow_log_disabled:{}".format(region, len(
        categorized_vpcs['flow_log_enabled']), len(categorized_vpcs['flow_log_disabled'])))
    return categorized_vpcs


def tags_to_str(vpc):
    if 'Tags' in vpc:
        return ', '.join("{" + d['Key'] + "=" + d['Value'] + "}" for d in vpc['Tags'])
    else:
        return ""


def describe_vpcs_flow_log(print_table=True):
    """
    Prints prettified table with the following columns:'VpcId', 'Vpc Enabled', 'Region', 'Tags'
    """
    logger.info("Scanning all VPCs - this might take some time... ")

    t = Texttable()
    t.add_row(['VpcId', 'Flow log Enabled', 'Region', 'Tags'])
    client = boto3.client("ec2", region_name=DEFAULT_REGION)
    regions = [region['RegionName'] for region in client.describe_regions()['Regions']]
    all_categorized_vpcs = {}
    for region in regions:
        categorized_vpcs_in_region = categorize_vpc_flow_log_status(region)
        all_categorized_vpcs[region] = categorized_vpcs_in_region
        for vpc_key, vpc_obj in categorized_vpcs_in_region['flow_log_enabled'].items():
            t.add_row([vpc_key, 'TRUE', region, tags_to_str(vpc_obj)])
        for vpc_key, vpc_obj in categorized_vpcs_in_region['flow_log_disabled'].items():
            t.add_row([vpc_key, 'FALSE', region, tags_to_str(vpc_obj)])
    if print_table:
        print(t.draw())
    return all_categorized_vpcs


def enable_flow_logs(bucket, vpc_ids):
    """
    Creates new s3 bucket with lifecycle policy of 1 year and enable flow log on all vpc's without flow log to write
    into that bucket
    :param bucket: name of bucket to create
    """
    s3 = boto3.client("s3")
    create_flow_log_bucket(bucket, s3)
    vpcs = describe_vpcs_flow_log(print_table=False)
    bucket_arn = 'arn:aws:s3:::{}'.format(bucket)
    flow_logs_cnt = 0
    for region in vpcs.keys():
        region_vpcs = vpcs[region]
        region_vpcs_without_flow_log = region_vpcs['flow_log_disabled']
        region_client = boto3.client("ec2", region_name=region)

        for vpc_key, vpc_obj in region_vpcs_without_flow_log.items():
            if vpc_ids is None or len(vpc_ids) == 0 or vpc_key in vpc_ids:
                flow_logs_resp = region_client.create_flow_logs(ResourceIds=[vpc_key], ResourceType='VPC',
                                                                TrafficType='ALL',
                                                                LogDestinationType='s3', LogDestination=bucket_arn)
                if len(flow_logs_resp['Unsuccessful']) > 0:
                    logger.error(
                        "Failed to create flow log for vpc={} in region={} error message={}".format(vpc_key, region,
                                                                                                    flow_logs_resp[
                                                                                                        'Unsuccessful'][0][
                                                                                                        'Error'][
                                                                                                        'Message']))
                else:
                    flow_logs_cnt += 1
    if flow_logs_cnt > 0:
        logger.info("successfully created {} flow logs".format(flow_logs_cnt))


def create_flow_log_bucket(bucket, s3):
    """
        creates a bucket with lifecycle expiration policy of 1 year
    :param bucket: name of bucket to create
    :param s3: s3 boto3 client
    """
    s3.create_bucket(Bucket=bucket)
    s3.put_bucket_lifecycle_configuration(
        Bucket=bucket,
        LifecycleConfiguration={
            'Rules': [
                {
                    'Expiration': {
                        'Days': 365,
                    },
                    'Prefix': '',
                    'ID': bucket + '_lifecycle_conf',

                    'Status': 'Enabled',
                }
            ]
        }
    )

    s3.put_public_access_block(Bucket=bucket,
                               PublicAccessBlockConfiguration={
                                   'BlockPublicAcls': True ,
                                   'IgnorePublicAcls': True ,
                                   'BlockPublicPolicy': True ,
                                   'RestrictPublicBuckets': True
                               })
    bucket_versioning = boto3.resource('s3').BucketVersioning(bucket)
    bucket_versioning.enable()


def disable_flow_logs(vpc_ids):
    """
    Creates new s3 bucket with lifecycle policy of 1 year and enable flow log on all vpc's without flow log to write
    into that bucket
    :param bucket: name of bucket to create
    """
    s3 = boto3.client("s3")
    vpcs = describe_vpcs_flow_log(print_table=False)
    flow_logs_cnt = 0
    for region in vpcs.keys():
        region_vpcs = vpcs[region]
        region_vpcs_with_flow_log = region_vpcs['flow_log_enabled']
        region_client = boto3.client("ec2", region_name=region)

        for vpc_key, vpc_obj in region_vpcs_with_flow_log.items():
            if vpc_ids is None or len(vpc_ids) == 0 or vpc_key in vpc_ids:
                flow_logs = region_client.describe_flow_logs(Filters=[{"Name": "resource-id", "Values": [vpc_key]}])
                log_id = flow_logs['FlowLogs'][0]['FlowLogId']
                flow_logs_resp = region_client.delete_flow_logs(FlowLogIds=[log_id])
                if len(flow_logs_resp['Unsuccessful']) > 0:
                    logger.error(
                        "Failed to disable flow log for vpc={} in region={}; error message={}".format(vpc_key, region,
                                                                                                      flow_logs_resp[
                                                                                                        'Unsuccessful'][0][
                                                                                                        'Error'][
                                                                                                        'Message']))
                else:
                    flow_logs_cnt += 1
    if flow_logs_cnt > 0:
        logger.info("successfully disabled {} flow logs".format(flow_logs_cnt))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='subparser')

    parser_describe_vpcs_flow_log = subparsers.add_parser('describe_vpcs_flow_log',
                                                          help='List all vpc instances and their flow log status '
                                                               'along side related region and tags. '
                                                          )

    parser_b = subparsers.add_parser('enable_flow_logs', help='Enables flow logs to all VPCs that do not have '
                                                              'flow log enabled (unless --vpcs is specified).')
    parser_b.add_argument('--vpcs', dest='vpc_ids', type=lambda l: l.split(','),
                          help="Specify a comma-separated (no spaces) list of VPCs to update. If omitted,"
                               "all VPCs are updated.")
    
    # By default, all arguments starting with - or -- are grouped under "optional arguments" in the help text, even if
    # they are marked as required during construction. This workaround makes them show under a separate header in the
    # help text.
    required_args = parser_b.add_argument_group('required arguments')
    required_args.add_argument(
        '-b', '--bucket', dest='bucket', required=True,
        help='The name of the new flow log bucket. \n All flow logs will be listed in '
             'the path pattern: '
             'bucket_ARN/optional_folder/AWSLogs/aws_account_id/vpcflowlogs/region/year/month'
             '/day/aws_account_id_vpcflowlogs_region_flow_log_id_timestamp_hash.log.gz'
             '\n Bucket is created with lifecycle rule to expire logs older then 365 days'
             '\n Bucket will have versioning turned on.'
             '\nBucket will have Block all public access turned on.')

    parser_disable = subparsers.add_parser('disable_flow_logs', help='Disables flow logs for all VPCs that have '
                                                                     'them enabled (unless --vpcs is specified).')
    parser_disable.add_argument('--vpcs', dest='vpc_ids', type=lambda l: l.split(','),
                                help="Specify a comma-separated (no spaces) list of VPCs to update. If omitted,"
                                     "all VPCs are updated.")

    kwargs = vars(parser.parse_args())
    if not kwargs['subparser']:
        parser.print_help()
        exit('Missing positional arguments')
    globals()[kwargs.pop('subparser')](**kwargs)
