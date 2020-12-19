#!/usr/bin/python3

import boto3
import os

old_bucket_name = "cd-old-bucket"
new_bucket_name = "cd-new-bucket"
old_suffix = "legacy-url"
new_suffix = "modern-url"

session = boto3.Session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_SECRET_KEY"),
)

s3 = session.resource('s3')
s3_client = session.client('s3')
old_bucket=s3.Bucket(old_bucket_name)
new_bucket=s3.Bucket(new_bucket_name)


def copy(obj):
    if obj.key != old_suffix+'/':
        print("-------Copying " + obj.key + "-------")
    old_source = {
        'Bucket': old_bucket_name,
        'Key': obj.key
    }
    new_key = new_suffix + obj.key[len(old_suffix):]
    new_obj = new_bucket.Object(new_key)
    new_obj.copy(old_source)
    tag = s3_client.put_object_tagging(
        Bucket = old_bucket_name,
        Key = obj.key,
        Tagging = {
            'TagSet':[
                {
                    'Key' : 'Copied',
                    'Value': 'True'
                }
            ]
        }
    )
    return True

def uploadFile(obj):
    tagCheck = s3_client.get_object_tagging(
        Bucket=old_bucket_name,
        Key=obj.key,
    )
    if len(tagCheck['TagSet']) != 0:
        if tagCheck['TagSet'][0]['Value'] == 'True':
            print("-------Skipping (Already Copied) " + obj.key + "-------")
        else:
            return copy(obj)
    else:
        return copy(obj)


for obj in old_bucket.objects.filter(Prefix=old_suffix):
    uploadFile(obj)
