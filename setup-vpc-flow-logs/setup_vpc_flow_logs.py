import boto3
# from tabulate import tabulate
import json
from texttable import Texttable
import argparse


def get_account_id():
    """

    :return: current AWS account id
    """
    client = boto3.client("sts")
    return client.get_caller_identity()["Account"]


def get_all_vpcs():
    """

    :return: describe vpc for all active VPCs established in the current aws account
    """
    client = boto3.client('ec2')
    return client.describe_vpcs(Filters=[
        {
            'Name': 'owner-id',
            'Values': [
                get_account_id(),
            ]
        },
        {
            'Name': 'state',
            'Values': [
                'available',
            ]
        },
    ])


def categorize_vpc_flow_log_status():
    client = boto3.client('ec2')

    all_vpcs = get_all_vpcs()
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
    return categorized_vpcs


def tags_to_str(tags):
    return ', '.join("{" + d['Key'] + "=" + d['Value'] + "}" for d in tags)


def describe_vpcs_flow_log():
    """
    Prints prettified table with the following columns:'VpcId', 'Vpc Enabled', 'Region', 'Tags'
    """
    t = Texttable()
    t.add_row(['VpcId', 'Vpc Enabled', 'Region', 'Tags'])

    categorized_vpcs = categorize_vpc_flow_log_status()
    for vpc_key, vpc_obj in categorized_vpcs['flow_log_enabled'].items():
        t.add_row([vpc_key, 'TRUE', 'Region', tags_to_str(vpc_obj['Tags'])])
    for vpc_key, vpc_obj in categorized_vpcs['flow_log_disabled'].items():
        t.add_row([vpc_key, 'FALSE', 'Region', tags_to_str(vpc_obj['Tags'])])
    print(t.draw())


def enable_flow_logs(bucket):
    print('task b', bucket)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='subparser')

    parser_describe_vpcs_flow_log = subparsers.add_parser('describe_vpcs_flow_log',
                                                          help='List all vpc instances and their flow log status '
                                                               'along side related region and tags. '
                                                          )

    parser_b = subparsers.add_parser('enable_flow_logs', help='Enables flow logs to VPCs that do not have '
                                                              'flow log enabled')
    parser_b.add_argument(
        '-b', '--bucket', dest='bucket',
        help='determines the name of the new flow log bucket. \n All flow logs will be listed in '
             'the path pattern: '
             'bucket_ARN/optional_folder/AWSLogs/aws_account_id/vpcflowlogs/region/year/month'
             '/day/aws_account_id_vpcflowlogs_region_flow_log_id_timestamp_hash.log.gz'
             '\n Bucket is created with lifecycle rule to expire logs older then 365 days')

    kwargs = vars(parser.parse_args())
    if not kwargs['subparser']:
        parser.print_help()
        exit('Missing positional arguments')
    globals()[kwargs.pop('subparser')](**kwargs)

#

# print(tabulate(list(vpc_with_flowlog.values())))
