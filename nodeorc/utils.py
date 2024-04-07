import boto3
import os
import logging
import time

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


def is_file_size_changing(fn, delay=1):
    """
    Check if the file size changes over a certain amount of time. Can be used to check
    if a file is being written into by another process.

    Parameters
    ----------
    fn : str
        path to file
    delay : float
        amount of delay time to check if file size changes

    Returns
    -------
    bool
        True (False) if file does (not) change

    """
    if not(os.path.isfile(fn)):
        raise IOError(f"File {fn} does not exist")
    # check if file is being written into, by checking changes in file size over a delay
    size1 = os.path.getsize(fn)
    time.sleep(delay)
    if size1 != os.path.getsize(fn):
        return True
    else:
        return False


def reboot_now():
    os.system("/sbin/shutdown -r now")
    # in case this fails, do a sudo shutdown
    os.system("sudo /sbin/shutdown -r now")
