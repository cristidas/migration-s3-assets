# migration-s3-assets

This is a script for migrating images between 2 S3 buckets and move the related database entries.

## Requirements
- aws cli
- Python libraries: boto3, mariadb
- AWS authentication details configured locally
- Database connection details configured locally

## How was this tested
- Local MariaDB database created
- 2 test buckets created in an AWS account
- seed.sh script was ran to populate the database and source bucket with test data

## What does it do
- Copies images from one S3 bucket to another, adding 2 tags to the images in the source bucket that were copied to destination, and setting one to True, to mark images copied over but not moved in the database:
```
'Copied': 'True'
'Database_updated': 'False'
```
- Updates the database with the bucket changes, only for files that have been moved to the destination bucket - checks if tags are set to `'Copied': 'True'` and `'Database_updated': 'False'`, and sets `'Database_updated': 'True'` for files successfully moved
- Deletes from source S3 bucket files that were successfully moved to destination bucket & migrated in the database - checks if tags are set to `'Copied': 'True'` and `'Database_updated': 'True'` before
