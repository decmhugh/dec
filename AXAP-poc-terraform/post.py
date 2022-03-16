import os,sys
import time
import json
import boto3
import yaml
import glob


from pprint import pprint
import requests
import sys
import uuid

def handler():

    if len(sys.argv) < 2:
        exit(1)
        sys.argv[0]
        sys.argv[1]

    headers = {'user': sys.argv[1],'key': 'declan'}
    headers["Content-Type"]="multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxkTrZu0gW"
    headers["Authorization"]="Bearer " + uuid.uuid4().hex
    headers["Content-Disposition"]="form-data; name=\"file\"; filename=\""+sys.argv[1]
    headers["Content-Type"]="application/octet-stream"
    headers["Content-Transfer-Encoding"]= "base64"
    file2 = sys.argv[1]

    #with open(file, 'rb') as f:
    with open(file2, 'rb') as f2:
        r = requests.post('https://jjp1kr2yxb.execute-api.cn-north-1.amazonaws.com.cn/api/', 
        files={sys.argv[1]: f2},
        headers=headers)
        print(r.text)

handler()

