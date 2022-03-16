
import os,sys
import time
import json
import boto3
import yaml
import glob
from pprint import pprint
import shutil
import botocore
import datetime
from datetime import timezone
from dateutil.tz import tzlocal

import yaml
from collections import OrderedDict    

class literal(str): pass

def literal_presenter(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
yaml.add_representer(literal, literal_presenter)

def ordered_dict_presenter(dumper, data):
    return dumper.represent_dict(data.items())
yaml.add_representer(OrderedDict, ordered_dict_presenter)


sts = boto3.client('sts')
global STACK_SET_NAME
dir_path = os.path.dirname(os.path.realpath(__file__))
base = os.path.basename(dir_path)
global parentname 
parentname = os.path.basename(dir_path)
stsclient = boto3.client('sts')
global artifact 
artifact = 'axap-aws-ci-cd-artifact-store'

assume_role_cache: dict = {}
def assumed_role_session(role_arn: str, base_session: botocore.session.Session = None):
    base_session = base_session or boto3.session.Session()._session
    fetcher = botocore.credentials.AssumeRoleCredentialFetcher(
        client_creator = base_session.create_client,
        source_credentials = base_session.get_credentials(),
        role_arn = role_arn,
        extra_args = {
        #    'RoleSessionName': None # set this if you want something non-default
        }
    )
    creds = botocore.credentials.DeferredRefreshableCredentials(
        method = 'assume-role',
        refresh_using = fetcher.fetch_credentials,
        time_fetcher = lambda: datetime.datetime.now(timezone.utc)
    )
    botocore_session = botocore.session.Session()
    botocore_session._credentials = creds
    return boto3.Session(botocore_session = botocore_session)


# usage:
sts = boto3.client('sts')
global cf2

# starting point
def handler():
    print(sts.get_caller_identity())
    global cf
    global cf2
    global AWS_REGION
    AWS_REGION = "eu-central-1"
    #session = assumed_role_session("arn:aws:iam::{}:role/CB-entity-cicd-account".format('015961844859'))
    cf = boto3.client('cloudformation', region_name=AWS_REGION)#session.client('cloudformation', region_name=AWS_REGION)
    cf2 = boto3.client('cloudformation', region_name=AWS_REGION)
            
    p = os.listdir(dir_path)
    dir_list = (list(x for x in p if (os.path.isdir(x) and x.find(".") == -1)))
    
    if len(sys.argv) > 1:
        dir_list=[sys.argv[1]]
    
    #Upload product files
    #Upload product files
    uploadDirectory("pre-reqs",artifact)

    uploadDirectory("build",artifact)
    
    

    
    for folder in dir_list:
        if "application-poc" in folder or len(sys.argv) > 1:
            base = folder
            global STACK_SET_NAME
            STACK_SET_NAME = base
            print("STARTING..." + STACK_SET_NAME)
            print("the path is " + base)

            s3dir = folder + "/code"
            print("Processing stacks in folder: {}".format(folder))        
            upload_s3(s3dir)
            template = get_template(folder)
            stacks = get_stacks(folder)
            upload_s3(s3dir)
            print("{} stack(s) to create or update!".format(len(stacks)))
            for stack_path in stacks:
                stack_data = get_stack_data(stack_path)
                if stack_data:
                    try:
                        stack_name = save_stack(template, stack_data)
                        enable_termination_protection(stack_name)
                    except Exception as err:
                        print(err)
                        print("Stack save failed or no required updates determined! See earlier messages")                    
                else:
                    print("Stack save skipped. Invalid stack data or parser error")
            print("Finished processing stacks in folder: {}".format(folder))

        
            check_stack_set()    
            #check_stack_set_instances(all_account_ids)

    print("FINISHED!")

def check_stack_set_instances(account_ids):
    response = cf2.list_stack_instances(StackSetName=STACK_SET_NAME)

    supported_account_ids = []
    unsupported_account_ids = []

    for item in response['Summaries']:

        if item['Status'] == 'INOPERABLE':
            print("Following stack instance requires manual investigation to fix!")
            #pprint(item)
            print("Skipping account check for above stack instance....")
        elif item['Account'] in account_ids:
            supported_account_ids.append(item['Account'])
        else:
            unsupported_account_ids.append(item['Account'])

    if len(unsupported_account_ids) > 0:
        print("Stack instances unsupported for accounts: {}".format(unsupported_account_ids))
        delete_stack_set_instances(unsupported_account_ids)
    else:
        print("No stack instances in unsupported accounts")

    missing_account_ids = [x for x in account_ids if x not in supported_account_ids]

    if len(missing_account_ids) > 0:
        print("Stack instances missing for account(s): {}".format(missing_account_ids))
        create_stack_set_instances(missing_account_ids)
    else:
        print("No missing stack instances")

def delete_stack_set_instances(account_ids):

    check_stack_set_operations()

    print("Deleting stack set instances for tenants, {}".format(account_ids))

    response = cf.delete_stack_instances(
        StackSetName=STACK_SET_NAME,
        Accounts=account_ids,
        Regions=get_regions(),
        RetainStacks=False
    )

    print("Stack instances deleted, Operation Id: {}".format(response['OperationId']))

def create_stack_set_instances(missing_account_ids):
    check_stack_set()
    print("New stack instances created, Operation Id: {}".format(response['OperationId']))



def check_stack_set():
    
    print("Checking whether stackset named {} exists".format(STACK_SET_NAME))

    description = 'application ' + STACK_SET_NAME
    template = get_template(STACK_SET_NAME)
    if "Transform: AWS::Serverless-2016-10-31" in template:
        os.system("aws cloudformation package --template-file " + STACK_SET_NAME  + "/template.yml --s3-bucket axap-aws-ci-cd-artifacts --output-template-file " + STACK_SET_NAME + "/template.package.yml > out.log")
        template = get_template(STACK_SET_NAME, file=STACK_SET_NAME + "/template.package.yml") 
         
    print("True:#active_stack_set_exists():")             
    if active_stack_set_exists():
        cf2 = boto3.client('cloudformation', region_name=AWS_REGION)
        
        
        print("STACK SET EXISTS! UPDATING.....")
        #check_stack_set_operations()
        response = cf2.get_template(StackName=STACK_SET_NAME)

        d = OrderedDict(yaml=literal(yaml.dump(response['TemplateBody'])))
        current = yaml.dump(d)

        d = OrderedDict(yaml=literal(yaml.dump(template)))
        new = yaml.dump(d)

        if new != current:

            response = cf.update_stack(
                StackName=STACK_SET_NAME,
                TemplateBody=template,
                Capabilities=[ 'CAPABILITY_NAMED_IAM','CAPABILITY_AUTO_EXPAND'],
                Tags=get_tags()
            )
            print("UPDATE ISSUED: Operation Id: {}".format(json.dumps(response)))
        else: 
            print("UPDATE: No stack to update")
        
        print(response)
        

    else:

        print("STACK SET DOES NOT EXIST! CREATING.....")

        response = cf.create_stack(
            StackName=STACK_SET_NAME,
            TemplateBody=template,
            Capabilities=[ 'CAPABILITY_NAMED_IAM','CAPABILITY_AUTO_EXPAND' ],
            Tags=get_tags()
        )

        print("CREATE ISSUED: StackId: {}".format(response['StackId']))    

    in_progress = True

    while in_progress:
        if active_stack_set_exists():
            in_progress = False
            print("Stack named {} exists now!".format(STACK_SET_NAME))
        else:
            time.sleep(10)

# util functions#
def active_stack_set_exists():
    ## Hopefully fix
    print("Checking whether stack named {} exists/is ready".format(STACK_SET_NAME))

    stack_exists = False
    response = cf.list_stacks()
    ## item in response['StackSummaries']
    for item in response['StackSummaries']:
        #print(item['StackName'],)
        if item['StackName'] == STACK_SET_NAME and item['StackStatus'] not in ["DELETE_COMPLETE"]:
            stack_exists = True            
            break
        

    return stack_exists

def get_accounts():

    accounts = [
        {
            "name": "prod@partners.axa",
            "region": "eu-central-1",
            "id": "015961844859"
        }
        #729155443024
    ]

    return accounts

def get_operation_preferences():
    return {
        'RegionOrder': get_regions(),
        'FailureTolerancePercentage': 10,
        'MaxConcurrentPercentage': 100
    }

def get_template(folder_name, file=True):
    print(os.getcwd(),folder_name, file)
    #for root,dirs,files in os.walk("./"):
        #for d in dirs:
            #print(root,d)
    if file == True:
        template_file = "{}/template.yml".format(folder_name)
        with open(template_file, 'r') as f:
            return f.read()
    else:
        with open(file, 'r') as f:
            return f.read()

#upload files
def uploadDirectory(path,bucketname):
    client_s3 = boto3.client('s3')
    #print(path)
    for root,dirs,files in os.walk(path):
        for file in files:
            name="AXAP-Main-Pipeline" + "/artifacts" + '/' + file
            #print(name)
            result = client_s3.list_objects(Bucket=bucketname, Prefix=name)
            #print(name)
            if 'Contents' not in result:
                client_s3.upload_file(os.path.join(root,file),bucketname, name)

def upload_s3(folder):
    if (os.path.exists(folder)):
        shutil.make_archive(STACK_SET_NAME + "/code", 'zip', folder + "/")
        #os.system("zip -r -j ./" + STACK_SET_NAME + "-code.zip " + folder + "/*")
        for root,dirs,files in os.walk("*.*"):
            for d in dirs:
                print(root,d)
            for d in files:
                print(root,d)
        upload_file("" + STACK_SET_NAME + '/code.zip', artifact, STACK_SET_NAME + '/code.zip')
    
        
       
def upload_file(file_name, bucket, object_name=None):
        
    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = os.path.basename(file_name)

    # Upload the file
    # s3_resource = boto3.resource("s3")
    # response = s3_resource.Bucket(bucket).put_object(
    #     Key = file_name, 
    #     Body = open(file_name, 'rb')
    # )
    #Change
    s3 = boto3.client('s3')
    s3.upload_file(file_name, bucket, object_name)
    s3.get_object(
        Bucket = bucket,
        Key = object_name
    )

def get_tags():

    tags = {
        'environment' : 'prod',
        'program' : 'axap',
        'managed-by' : 'declan.mchugh.exe@axapartners.axa',
        'Name' : 'AWS-AXAP-Partners-Default',
        'project-admin-access':'true'
    }

    result = []

    for key in tags:
        result.append({
            'Key' : str(key),
            'Value' : str(tags[key])
        })

    return result

def get_regions():
    return ['eu-central-1']


def enable_termination_protection(stack_name):

    print("Enabling termination protection for stack: {}".format(stack_name))
    cf.update_termination_protection(
        EnableTerminationProtection=True,
        StackName=stack_name
    )
    print("Enabled!")

def save_stack(template, stack_data):
    stack_name = stack_data['Name']
    result = stack_exists(stack_name)
    if result:
        print("Stack, {}, exists! Updating...".format(stack_name))
        update_stack(template, stack_name, stack_data)
        time.sleep(5)
        check_stack_status(stack_name)

    else:
        print("Stack, {}, does not exist! Creating...".format(stack_name))        
        create_stack(template, stack_name, stack_data)
        time.sleep(10)
        check_stack_status(stack_name)

    return stack_name

def update_stack(template, stack_name, stack_data):
    check_stack_status(stack_name)
    print(('Transform' in template))
    if 'Transform' in template:
        print("has transform")
        description = 'application ' + STACK_SET_NAME
        os.system("aws cloudformation package --template-file " + STACK_SET_NAME  + "/template.yml --s3-bucket axap-application-artifacts --output-template-file " + STACK_SET_NAME + "/template.package.yml > out.log")
        with open(STACK_SET_NAME + "/template.package.yml", 'r') as stream:
            cf2 = boto3.client('cloudformation', region_name=AWS_REGION)
            stack = cf2.update_stack(
                StackName=STACK_SET_NAME,
                TemplateBody=template,
                Parameters=stack_data['Parameters'],
                Capabilities=[ 'CAPABILITY_NAMED_IAM', 'CAPABILITY_AUTO_EXPAND'],
                Tags=get_tags()
            )
    else:
        print("not a transform")
        # Read YAML file
        with open(template, 'r') as stream:
            print("Check template")
            cf2 = boto3.client('cloudformation', region_name=AWS_REGION)
            stack = cf2.update_stack(
                StackName=STACK_SET_NAME,
                TemplateBody=template,
                Parameters=stack_data['Parameters'],
                Capabilities=[ 'CAPABILITY_NAMED_IAM','CAPABILITY_AUTO_EXPAND' ],
                Tags=get_tags()
            )
            
    print("stack update called: {}".format(stack_name))
    pprint(stack)


def create_stack(template, stack_name, stack_data):
    
    print("Checking whether stack named {} exists".format(STACK_SET_NAME))
    print(('Transform' in template))
    #print(data_loaded.has_key('Transform'))
    if 'Transform' in template:
        print("has transform")
        description = 'application ' + STACK_SET_NAME
        os.system("aws cloudformation package --template-file " + STACK_SET_NAME  + "/template.yml --s3-bucket axap-application-artifacts --output-template-file " + STACK_SET_NAME + "/template.package.yml > out.log")
        with open(STACK_SET_NAME + "/template.package.yml", 'r') as stream:
            stack = cf2.create_stack(
                StackName=stack_name,
                TemplateBody=template,
                Parameters=stack_data['Parameters'],
                Capabilities=[ 'CAPABILITY_NAMED_IAM','CAPABILITY_AUTO_EXPAND' ],
                Tags=get_tags()
            )
    else:
        print("not a transform")
        # Read YAML file
        stack = cf2.create_stack(
                StackName=stack_name,
                TemplateBody=template,
                Parameters=stack_data['Parameters'],
                Capabilities=[ 'CAPABILITY_NAMED_IAM','CAPABILITY_AUTO_EXPAND'  ],
                Tags=get_tags()
            )
            
    print("New stack created called: {}".format(stack_name))
    #pprint(stack)

def check_stack_status(stack_name, show_message=True):

    if show_message:
        print("Checking status for {} to ensure operable or completed state".format(stack_name))

    blocking = [
        'CREATE_IN_PROGRESS',
        'UPDATE_IN_PROGRESS',
        'UPDATE_COMPLETE_CLEANUP_IN_PROGRESS',
        'UPDATE_ROLLBACK_IN_PROGRESS',
        'UPDATE_ROLLBACK_COMPLETE_CLEANUP_IN_PROGRESS'
    ]

    erroneous = [
        'CREATE_FAILED',
        'ROLLBACK_IN_PROGRESS', 
        'ROLLBACK_FAILED', 
        'ROLLBACK_COMPLETE',
        'DELETE_IN_PROGRESS',
        'DELETE_FAILED',
        'DELETE_COMPLETE',
        'UPDATE_ROLLBACK_FAILED',
        'REVIEW_IN_PROGRESS'
    ]
    print("Descibe Stack cf2.describe_stacks(StackName=stack_name)")
    response = cf2.describe_stacks(StackName=stack_name)
    status = response['Stacks'][0]['StackStatus']

    if status in erroneous:
        msg = "Status is erroneous for stack named {}; status: {}".format(stack_name, status)
        print(msg)
        print("Skipping any further operations on this stack! Resolve status!")
        raise ValueError(msg)
    elif status in blocking:
        wait = 15
        print("Stack has status: {}. Retrying in {} seconds...".format(status, wait))
        time.sleep(wait)
        return check_stack_status(stack_name, False)

def stack_exists(stack_name):    
    print("stack_exists(stack_name)")
    response = cf2.list_stacks()
    #print(json.dumps(response, indent=4, sort_keys=True, default=str))
    existing = [x for x in response['StackSummaries'] if x['StackName'] == stack_name]# and "DELETE_COMPLETE" != x['StackStatus']
    print("EXISTING", json.dumps(existing, indent=4, sort_keys=True, default=str))
    return len(existing) > 0

def get_stacks(folder_name):
    path = "{}/stacks/*.yml".format(folder_name)
    return glob.glob(path)

def get_stack_data(path):
    data = None
    #print('get_stack_data(path)', path)
    with open(path, 'r') as stream:
        try:
            data = yaml.load(stream,Loader=yaml.FullLoader)
        except yaml.YAMLError as err:
            data = None
            print("YAML error! Skipping save for: {}".format(path))
            print(err)
            
    return data






       
def upload_file(file_name, bucket, object_name=None):
    """Upload a file to an S3 bucket

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: True if file was uploaded, else False
    """
    
    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = os.path.basename(file_name)

    # Upload the file
    s3_resource = boto3.resource("s3")
    response = s3_resource.Bucket(bucket).put_object(
        Key = object_name, 
        Body = open(file_name, 'rb')
    )
    s3 = boto3.client('s3')
    print(s3.get_object(
        Bucket = bucket,
        Key = object_name
    ))
    #try:
    #import io
    #print(file_name, bucket, object_name)
    #file_binary = open(file_name, "rb")
    ##file_as_binary = io.BytesIO(file_binary.read())
    #response = s3_client.upload_fileobj(file_name, bucket, object_name)
    print("UPLOAD: ", response)
    
    #except ClientError as e:
    #    return False
    #return True

handler()