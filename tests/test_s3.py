import glob
import os


def test_s3_upload(s3_video_sample):
    # TODO: test if the file is present in bucket
    storage, filename = s3_video_sample
    f = list(storage.bucket.objects.filter(Prefix=filename))
    # check if there is one file with the filename in bucket
    assert(len(f) == 1)


def test_local_upload(local_video_sample):
    # TODO: test if the file is present in bucket
    storage, filename = local_video_sample
    f = glob.glob(os.path.join(storage.bucket, f"{filename}*"))
    # check if there is one file with the filename in bucket
    assert(len(f) == 1)


def test_s3_camconfig(camconfig):
    assert isinstance(camconfig, dict)



def test_s3_recipe(recipe):
    assert isinstance(recipe, dict)
