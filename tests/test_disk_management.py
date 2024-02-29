import os
from nodeorc import disk_mng
import logging

def test_scan_folder(local_video_sample):
    storage, filename = local_video_sample
    path = storage.bucket
    # check contents
    fns = disk_management.scan_folder(path, clean_empty_dirs=True)
    assert(len(fns) != 0)


def test_delete_file(local_video_sample):
    storage, filename = local_video_sample
    fn = os.path.join(storage.bucket, filename)
    ret = disk_management.delete_file(fn, logging)
    assert(ret==True)

def test_get_free_space(path="/home"):
    free_space = disk_management.get_free_space(path)
    assert(isinstance(free_space, float))

def test_purge(local_video_sample):
    storage, filename = local_video_sample
    path = storage.bucket
    disk_management.purge(
        path,
        free_space=1e9,
        min_free_space=0.01,
        logger=logging,
        home="/home"
    )
