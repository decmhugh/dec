import os,sys
import time
import json
import yaml
import glob
import boto3
from pprint import pprint
import shutil
import botocore
import datetime
from datetime import timezone
from dateutil.tz import tzlocal
from python_terraform import *


client = boto3.client('connect', region_name='eu-central-1')

response = client.list_instances()

for instance in response['InstanceSummaryList']:
    print(instance['Id'])
    list_phone_numbers = client.list_phone_numbers(
        InstanceId=instance['Id']
    )

    list_users = client.list_users(
        InstanceId=instance['Id']
    )
    #print(list_phone_numbers)
    #PhoneNumberSummaryList
    for users in list_users['UserSummaryList']:
        print("Users",users['Id'])
        res=response = client.describe_user(
            UserId=users['Id'],
            InstanceId=instance['Id']
        )
        print("describe_user",res)
    id = ""
    next = True
    import datetime
    while next:
        response = client.get_metric_data(
            InstanceId='string',
            StartTime=datetime.datetime(2015, 1, 1),
            EndTime=datetime.datetime(2023, 1, 1),
            NextToken="{0}".format(id),
            MaxResults=1,
            Filters={
                'Channels': ['VOICE']},
            HistoricalMetrics=[
                {
                    'Name': 'CONTACTS_HANDLED',
                    'Threshold': {
                        'Comparison': 'LT',
                        'ThresholdValue': 123.0
                    },
                    'Statistic': 'MAX',
                    'Unit': 'SECONDS'
                }]
            
        )
        print(response)
        if id == response: 
            next = False


    # for phone in list_phone_numbers['PhoneNumberSummaryList']:
    #     print("Phone",phone)
    #     res=get_contact_attributes = client.get_contact_attributes(
    #         InstanceId=instance['Id'],
    #         InitialContactId=phone['Id']
    #     )
    #     print("get_contact_attributes",res)

    


# response = client.list_users(
#     InstanceId='string',
#     NextToken='string',
#     MaxResults=123
# )

# describe_agent_status()
# describe_contact()
# describe_contact_flow()
# describe_contact_flow_module()
# describe_hours_of_operation()
# describe_instance()
# describe_instance_attribute()
# describe_instance_storage_config()
# describe_queue()
# describe_quick_connect()
# describe_routing_profile()
# describe_security_profile()
# describe_user()
# describe_user_hierarchy_group()
# describe_user_hierarchy_structure()
# describe_vocabulary()
# disassociate_approved_origin()
# disassociate_bot()
# disassociate_instance_storage_config()
# disassociate_lambda_function()
# disassociate_lex_bot()
# disassociate_queue_quick_connects()
# disassociate_routing_profile_queues()
# disassociate_security_key()
# get_contact_attributes()
# get_current_metric_data()
# get_federation_token()
# get_metric_data()
# get_paginator()
# get_waiter()
# list_agent_statuses()
# list_approved_origins()
# list_bots()
# list_contact_flow_modules()
# list_contact_flows()
# list_contact_references()
# list_default_vocabularies()
# list_hours_of_operations()
# list_instance_attributes()
# list_instance_storage_configs()
# list_instances()
# list_integration_associations()
# list_lambda_functions()
# list_lex_bots()
# list_phone_numbers()
# list_prompts()
# list_queue_quick_connects()
# list_queues()
# list_quick_connects()
# list_routing_profile_queues()
# list_routing_profiles()
# list_security_keys()
# list_security_profile_permissions()
# list_security_profiles()
# list_tags_for_resource()
# list_use_cases()
# list_user_hierarchy_groups()
# list_users()