def test_s3_upload(s3_video_sample):
    # TODO: test if the file is present in bucket
    bucket, filename = s3_video_sample
    f = list(bucket.objects.filter(Prefix=filename))
    # check if there is one file with the filename in bucket
    assert(len(f) == 1)
