#!/usr/bin/python3

import boto3
import mariadb
import sys
import os
from concurrent import futures
import faulthandler; faulthandler.enable()

db_host = "127.0.0.1"
db_port = 3306
db_user = "root"
db_password = "secret"
db_name = "frontend"


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
    '''Objects for copping and putting tags'''
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
                },
                {
                    'Key' : 'Database_updated',
                    'Value': 'False'
                },
            ]
        }
    )
    return True

def uploadFile(obj):
    '''Check tag value and copy file to new s3 bucket'''
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

def updateDatabase(obj):
    '''Update the database entries for the moved objects'''
    try:
        conn = mariadb.connect(
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port,
            database=db_name
        )
    except mariadb.Error as e:
        print(f"Error connecting to the database: {e}")
        sys.exit(1)
    cur = conn.cursor()
    tagCheck = s3_client.get_object_tagging(
        Bucket=old_bucket_name,
        Key=obj.key,
    )
    if tagCheck['TagSet'][0]['Value'] == 'True':
        if tagCheck['TagSet'][1]['Value'] == 'False':
            if obj.key != old_suffix+'/':
                print("-------Updating database url " + obj.key + "-------")
            query = 'UPDATE frontend.images set base_url = "'+new_bucket_name+'" , url=REPLACE (url, "'+old_suffix+'", "'+new_suffix+'") where url like "%'+obj.key.split("/", 1)[-1]+'%";'
            try:
                cur.execute(query)
                conn.commit()
                conn.close()
                tag = s3_client.put_object_tagging(
                    Bucket = old_bucket_name,
                    Key = obj.key,
                    Tagging = {
                        'TagSet':[
                            {
                                'Key' : 'Copied',
                                'Value': 'True'
                            },
                            {
                                'Key' : 'Database_updated',
                                'Value': 'True'
                            },
                        ]
                    }
                )
                return True
            except mariadb.Error as e:
                print(f"Error: {e}")
                return False
        else:
            if obj.key != old_suffix+'/':
                print("-------Skipping database url (Already Updated) " + obj.key + "-------")


def deleteObjects(obj):
    '''Delete objects from old s3 bucket if they were successfully moved'''
    tagCheck = s3_client.get_object_tagging(
        Bucket=old_bucket_name,
        Key=obj.key,
    )
    if tagCheck['TagSet'][0]['Value'] == 'True':
        if tagCheck['TagSet'][1]['Value'] == 'True':
            if obj.key != old_suffix+'/':
                print("-------Deleting Object " + obj.key + "-------")
                s3_client.delete_object(
                Bucket=old_bucket_name,
                Key=obj.key,
                )


with futures.ThreadPoolExecutor() as executor:
    print("###########  COPYING OBJECTS  ###########")
    print("\n>>>>> Source S3 Bucket: " + old_bucket_name)
    size = sum(1 for _ in old_bucket.objects.filter(Prefix=old_suffix))
    print("\n>>>>> Total Matching Objects Found: " + str(size-1) + "\n")
    futures.wait(
        [executor.submit(uploadFile, obj) for obj in old_bucket.objects.filter(Prefix=old_suffix)],
        return_when=futures.FIRST_EXCEPTION,
    )
    print("###########  UPDATING DATABASE  ###########")
    futures.wait(
        [executor.submit(updateDatabase, obj) for obj in old_bucket.objects.filter(Prefix=old_suffix)],
        return_when=futures.FIRST_EXCEPTION,
    )
    print("###########  DELETING OBJECTS  ###########")
    futures.wait(
        [executor.submit(deleteObjects, obj) for obj in old_bucket.objects.filter(Prefix=old_suffix)],
        return_when=futures.FIRST_EXCEPTION,
    )
