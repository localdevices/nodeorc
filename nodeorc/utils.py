import boto3
import os
import logging

def check_bucket(s3, bucket_name):
    try:
        bucket = s3.Bucket(bucket_name)
        s3.meta.client.head_bucket(Bucket=bucket_name)
        return {
            "code": 200,
            "message": "Bucket is accessible"
        }
    # except botocore.exceptions.ClientError as e:
    except Exception as e:
        # If a client error is thrown, then check that it was a 404 error.
        # If it was a 404 error, then the bucket does not exist.
        error_code = 404 # int(e.response['Error']['Code'])
        if error_code == 403:
            # TODO: fix that forbidden buckets are given an alternative error
            msg = "Private Bucket. Forbidden Access!"
        elif error_code == 404:
            msg = "Bucket Does Not Exist!"
        return {
            "code": error_code,
            "message": msg
        }

def get_s3(
    endpoint_url,
    aws_access_key_id,
    aws_secret_access_key,
):
    return boto3.resource(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        config=boto3.session.Config(signature_version="s3v4"),
        verify=False
    )


def get_bucket(
    url,
    bucket_name,
    **kwargs
):
    s3 = get_s3(
        endpoint_url=url,
        **kwargs
    )
    if s3.Bucket(bucket_name) not in s3.buckets.all():
        s3.create_bucket(Bucket=bucket_name)

    # first check if bucket is available
    r = check_bucket(s3, bucket_name)
    if r["code"] == 200:
        return s3.Bucket(bucket_name)
    else:
        return None

def upload_io(obj, bucket, dest=None, logger=logging):
    """
    Uploads BytesIO obj representation of data in file 'fn' in bucket
    """

    r = bucket.upload_fileobj(obj, dest)
    logger.info(f"{bucket}/{dest} created")
    return r