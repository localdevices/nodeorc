import os
import shutil
from typing import Optional, Dict, Any
from pydantic import BaseModel, AnyHttpUrl
# nodeodm specific imports

from .. import callbacks, utils

class Storage(BaseModel):
    url: str = "./tmp"
    bucket_name: str = "video"

    @property
    def bucket(self):
        return os.path.join(self.url, self.bucket_name)

    @property
    def delete(self):
        shutil.rmtree(self.bucket)

    def upload_io(self, obj, dest):
        """
        Upload a BytesIO object to a file on storage location

        Parameters
        ----------
        obj : io.BytesIO
            bytes to be written to file
        dest : str
            destination filename (only name, full path is formed from self.bucket)

        Returns
        -------

        """
        obj.seek(0)
        fn = os.path.join(self.bucket, dest)
        path = os.path.split(fn)[0]
        if not(os.path.isdir(path)):
            os.makedirs(path)
        # create file
        with open(fn, "wb") as f:
            f.write(obj.read())

    def download_file(self, src, trg, keep_src=False):
        """
        Download file from one local location to another target file (entire path inc. filename)

        Parameters
        ----------
        src : str
            file within local bucket

        trg : str
            file as it should be named locally
        keep_src : bool
            if set, the file is copied, if not set, a rename will be performed instead.

        Returns
        -------

        """
        if keep_src:
            shutil.copyfile(
                os.path.join(self.bucket, src),
                trg
            )
        else:
            os.rename(
                os.path.join(self.bucket, src),
                trg
            )

class S3Storage(Storage):
    url: AnyHttpUrl = "http://127.0.0.1:9000"
    options: Dict[str, Any]


    @property
    def bucket(self):
        return utils.get_bucket(
            url=str(self.url),
            bucket_name=self.bucket_name,
            **self.options
        )

    def upload_io(self, obj, dest, **kwargs):
        utils.upload_io(obj, self.bucket, dest=dest, **kwargs)

    def download_file(self, src, trg):
        """
        Download file from bucket to specified target file (entire path inc. filename)

        Parameters
        ----------
        src : str
            file within bucket

        trg : file as it should be named locally

        Returns
        -------

        """
        self.bucket.download_file(src, trg)



class File(BaseModel):
    """
    Definition of the location, naming of raw result on tmp location, and in/output file name for cloud storage
    Also defined if the result should be uploaded after processing is done or not
    """
    remote_name: Optional[str] = "video.mp4"
    tmp_name: str = "video.mp4"

    def move(self, src, trg):
        """
        Moves the file from src folder to trg folder

        Parameters
        ----------
        src : str
            Source folder, where File is expected as tmp file
        trg :
            Target folder, where File must be moved to

        Returns
        -------

        """
        src_fn = os.path.join(src, self.tmp_name)
        trg_fn = os.path.join(trg, self.tmp_name)
        os.rename(src_fn, trg_fn)
