import copy
import shutil
import sys
import threading
import concurrent.futures
import logging
import multiprocessing
import numpy as np
import os
import pandas as pd
import time
import datetime
import uuid
from urllib.parse import urljoin
from requests.exceptions import ConnectionError

from . import models, disk_management


REPLACE_ARGS = ["input_files", "output_files", "storage", "callbacks"]

class LocalTaskProcessor:
    def __init__(
            self,
            task_form_template,
            callback_url: models.CallbackUrl,
            storage: models.Storage,
            settings: models.Settings,
            temp_path: str,
            # incoming_path: str,
            # failed_path: str,
            # success_path: str,
            # results_path: str,
            # parse_dates_from_file: bool,
            # video_file_fmt: str,
            # water_level_fmt: str,
            # water_level_datetimefmt: str,
            # allowed_dt: float,
            # shutdown_after_task: bool,
            disk_management: models.DiskManagement,
            max_workers: int = 1,
            logger=logging,

    ):
        self.task_form_template = task_form_template
        self.settings = settings
        self.temp_path = temp_path
        # self.incoming_path = incoming_path
        # self.failed_path = failed_path
        # self.success_path = success_path
        # self.results_path = results_path
        # self.parse_dates_from_file = parse_dates_from_file
        # self.video_file_fmt = video_file_fmt
        self.video_file_ext = settings["video_file_fmt"].split(".")[-1]
        # self.water_level_ftm = water_level_fmt
        # self.water_level_datetimefmt = water_level_datetimefmt
        # self.allowed_dt = allowed_dt
        # self.shutdown_after_task = shutdown_after_task
        self.disk_management = disk_management
        self.callback_url = models.CallbackUrl(**callback_url)
        self.storage = models.Storage(**storage)
        self.max_workers = max_workers
        self.logger = logger
        # make a list for processed files or files that are being processed so that they are not duplicated
        self.processed_files = set()
        self.logger.info(f'Water levels will be searched for in {self.settings["water_level_fmt"]} using a datetime format "{self.settings["water_level_datetimefmt"]}')
        self.logger.info(f"Start listening to new videos in folder {self.settings['incoming_path']}")
        self.event = threading.Event()

        # Create and start the thread
        self.thread = threading.Thread(
            target=self.await_task,
        )
        self.thread.start()
        try:
            # Your main program can continue running here
            while not self.event.is_set():
                time.sleep(1)
            self.logger.info("await_task event was triggered. Exiting the program.")
        except KeyboardInterrupt:
            # Handle Ctrl+C to stop the program
            self.event.set()
            self.thread.join()
        # Cleanup and exit
        self.logger.info("Program terminated.")


    def await_task(self):
        # Get the number of available CPU cores
        max_workers = np.minimum(
            self.max_workers,
            multiprocessing.cpu_count()
        )
        # start the timer for the disk manager
        disk_mng_t0 = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            while not self.event.is_set():
                file_paths = disk_management.scan_folder(
                    self.settings["incoming_path"],
                    suffix=self.video_file_ext
                )
                for file_path in file_paths:
                    if os.path.isfile(file_path) and file_path not in self.processed_files:
                        self.logger.info(f"Found file: {file_path}")
                        # Submit the file processing task to the thread pool
                        executor.submit(
                            self.process_file,
                            file_path,
                        )
                        # make sure the file is in the list of processed files to ensure the task is not
                        # duplicated to another thread instance
                        self.processed_files.add(file_path)
                time.sleep(5)  # wait for 5 secs before re-investigating the monitored folder for new files
                if time.time() - disk_mng_t0 > self.disk_management["frequency"]:
                    # reset the disk management t0 counter
                    disk_mng_t0 = time.time()
                    self.logger.info(
                        f"Checking for disk space exceedance of {self.disk_management['min_free_space']}"
                    )
                    free_space = disk_management.get_free_space(
                        self.disk_management["home_folder"]
                    )
                    if free_space < self.disk_management["min_free_space"]:
                        self.cleanup_space(free_space=free_space)


    def cleanup_space(self, free_space):
        """
        Free up space on disk by removing oldest files first.
        First success and failed paths are cleaned, then results path is cleaned.

        Parameters
        ----------
        free_space : float
            GB amount of free space currently available

        """
        ret = disk_management.purge(
            [
                self.settings["success_path"],
                self.settings["failed_path"],
            ],
            free_space=free_space,
            min_free_space=self.disk_management["min_free_space"],
            logger=self.logger,
            home=self.disk_management["home_folder"]
        )
        # if returned is False then continue purging the results path
        if not ret:
            self.logger.warning(f"Space after purging still not enough, purging results folder")
            ret = disk_management.purge(
                [
                    self.settings["results_path"]
                ],
                free_space=free_space,
                min_free_space=self.disk_management["min_free_space"],
                logger=self.logger,
                home=self.disk_management["home_folder"]
            )
        if not ret:
            self.logger.warning(f"Not enough space freed up. Checking for critical space.")
            # final computation of free space
            free_space = disk_management.get_free_space(
                self.disk_management["home_folder"],
            )
            if free_space < self.disk_management["critical_space"]:
                # shutdown the service to secure the device!
                self.logger.error(
                    f"Free space is under critical threshold of {self.disk_management['critical_space']}. Shutting down NodeORC service"
                )
                os.system("/usr/bin/systemctl disable nodeorc")
                os.system("/usr/bin/systemctl stop nodeorc")
                sys.exit(1)
            else:
                self.logger.warning(
                    f"Free space is {free_space} which is not yet under critical space {self.disk_management['critical_space']}. Please contact your supplier for information.")


    def process_file(
            self,
            file_path,
    ):
        task_uuid = uuid.uuid4()
        task_path = os.path.join(
            self.temp_path,
            str(task_uuid)
        )
        # ensure the tmp path is in place
        if not(os.path.isdir(task_path)):
            os.makedirs(task_path)
        try:
            url, filename = os.path.split(file_path)
            cur_path = file_path
            self.logger.info(f"Processing file: {file_path}")
            # determine time stamp
            try:
                timestamp = get_timestamp(
                    file_path,
                    parse_from_fn=self.settings["parse_dates_from_file"],
                    fn_fmt=self.settings["video_file_fmt"],
                )
            except Exception as e:
                timestamp = None
                raise ValueError(f"Could not get a logical timestamp from file {file_path}. Reason: {e}")
            # create Storage instance
            self.logger.info(f"Timestamp for video found at {timestamp.strftime('%Y%m%dT%H%M%S')}")
            storage = models.Storage(
                url=str(self.settings["results_path"]),
                bucket_name=timestamp.strftime("%Y%m%d")
            )
            # move the file to the intended bucket
            if not(os.path.isdir(storage.bucket)):
                os.makedirs(storage.bucket)
            os.rename(file_path, os.path.join(storage.bucket, filename))
            # update the location of the current path of the video file (only used in exception)
            cur_path = os.path.join(storage.bucket, filename)
            # collect water level
            try:
                h_a = get_water_level(
                    timestamp,
                    file_fmt=self.settings["water_level_fmt"],
                    datetime_fmt=self.settings["water_level_datetimefmt"],
                    allowed_dt=self.settings["allowed_dt"]
                )
            except Exception as e:
                raise ValueError(
                    f"Could not obtain a water level for date {timestamp.strftime('%Y%m%d')} at timestamp {timestamp.strftime('%Y%m%dT%H%M%S')}. Reason: {e}"
                )
            # create the task object from all data
            task = create_task(
                self.task_form_template,
                task_uuid,
                task_path,
                storage,
                filename,
                timestamp,
                h_a,
                logger=self.logger
            )
            # set cur_path to tmp location (only used on exception)
            cur_path = os.path.join(task_path, filename)
            # process the task
            task.execute(task_path)
            # if the video was treated successfully, then we may move it to a location of interest if wanted
            if self.settings["success_path"]:
                dst_path = os.path.join(
                    self.settings["success_path"],
                    timestamp.strftime("%Y%m%d")
                )
            # perform the callbacks here
            self.execute_callbacks(task.callbacks)
        except Exception as e:
            self.logger.error(f"Error processing {file_path}: {str(e)}")
            # find back the file and place in the failed location, organised per day
            if timestamp:
                dst_path = os.path.join(self.settings["failed_path"], timestamp.strftime("%Y%m%d"))
            else:
                dst_path = self.settings["failed_path"]

        if not os.path.isdir(dst_path):
            os.makedirs(dst_path)
        dst = os.path.join(dst_path, filename)
        os.rename(cur_path, dst)
        self.logger.debug(f"Video file moved from {cur_path} to {dst_path}")

        if os.path.isdir(task_path):
            # remove any left over temporary files
            shutil.rmtree((task_path))
        # once done, the file is removed from list of considered files for processing
        self.processed_files.remove(file_path)
        # shutdown if configured to shutdown after task
        self.shutdown_or_not()


    def shutdown_or_not(self):
        if self.shutdown_after_task:
            self.logger.info("Task done! Shutting down...")
            os.system("/sbin/shutdown -h now")


    def execute_callbacks(self, callbacks): # callback_url, timestamp, tmp):
        # get the name of callback
        for callback in callbacks:
            url = urljoin(str(self.callback_url.url), callback.endpoint)
            self.logger.info(f"Sending {callback.func_name} callback to {url}")
            store_callback = False
            r = self.callback_url.send_callback(callback)
            if r is None:
                self.logger.error(
                    f"Connection to {url} failed, connection error"
                )
                store_callback = True
            elif r.status_code != 201 and r.status_code != 200:
                self.logger.error(
                    f'callback to {url} failed with error code {r.status_code}, storing callback in database'
                )
                store_callback = True
            if store_callback:
                # something went wrong while sending, store callback for a later re-try
                self.logger.info(f"Storing callback in database to prevent loss of data")
                callback.to_db()


def get_timestamp(
    fn,
    parse_from_fn,
    fn_fmt,
):
    if parse_from_fn:
        datetime_fmt = fn_fmt.split("{")[1].split("}")[0]
        fn_template = fn_fmt.replace(datetime_fmt, "")
        prefix, suffix = fn_template.split("{}")
        if not(prefix in fn) or not(suffix in fn):
            raise ValueError(f"File naming of video {fn} does not follow the template {fn_fmt}. . Please change settings.json")
        if len(prefix) > 0:
            timestr = fn.split(prefix)[1]
        else:
            timestr = os.path.basename(fn)
        if len(suffix) > 0:
            timestr = timestr.split(suffix)[0]
        try:
            timestamp = datetime.datetime.strptime(timestr, datetime_fmt)
        except:
            raise ValueError(f"datetime string {timestr} does not follow the datetime format {datetime_fmt}. Please change settings.json")
    else:
        timestamp = datetime.datetime.fromtimestamp(os.path.getmtime(fn))
    return timestamp


def read_water_level_file(fn, fmt):
    date_parser = lambda x: datetime.datetime.strptime(x, fmt)
    df = pd.read_csv(
        fn,
        parse_dates=True,
        index_col=[0],
        sep=" ",
        date_parser=date_parser,
        header=None,
        names=["water_level"]
    )
    return df

# Define the function to process a single file

def get_water_level(
    timestamp,
    file_fmt,
    datetime_fmt,
    allowed_dt=None,

):
    if "{" in file_fmt and "}" in file_fmt:
        datetimefmt = file_fmt.split("{")[1].split("}")[0]
        water_level_template = file_fmt.replace(datetimefmt, ":s")
        water_level_fn = water_level_template.format(timestamp.strftime(datetimefmt))
    else:
        # there is no date pattern, so assume the fmt is already a file path
        water_level_fn = file_fmt
    if not(os.path.isfile(water_level_fn)):
        raise IOError(f"water level file {os.path.abspath(water_level_fn)} does not exist.")
    df = read_water_level_file(water_level_fn, fmt=datetime_fmt)
    t = timestamp.strftime("%Y%m%d %H:%M:%S")
    # find the closest match
    i = np.minimum(np.maximum(df.index.searchsorted(t), 0), len(df) - 1)
    # check if value is within limits of time allowed
    if allowed_dt is not None:
        dt_seconds = abs(df.index[i] - timestamp).total_seconds()
        if dt_seconds > allowed_dt:
            raise ValueError(
                f"Timestamp of video {timestamp} is more than {allowed_dt} seconds off from closest "
                f"water level timestamp {df.index[i]}"
            )
    h_a = df.iloc[i].values[0]
    return h_a

def create_task(
    task_form_template,
    task_uuid,
    task_path,
    storage,
    filename,
    timestamp,
    h_a,
    logger=logging
):
    task_form = copy.deepcopy(task_form_template)
    # prepare input_files field in task definition
    input_files = {
        "videofile": models.File(
            remote_name=filename,
            tmp_name=filename
        )
    }
    # output file templates are filled in with the timestamp
    output_files = {
        k: models.File(
            remote_name=v["remote_name"].format(timestamp.strftime('%Y%m%dT%H%M%S')),
            tmp_name=v["tmp_name"]
        ) for k, v in task_form["output_files"].items()
    }
    # callback jsons are converted to Callback objects
    callbacks = []
    for cb in task_form["callbacks"]:
        if "file" in cb:
            cb["file"] = output_files[cb["file"]]
        if "files_to_send" in cb:
            cb["files_to_send"] = {fn: output_files[fn] for fn in cb["files_to_send"]}
        cb_obj = models.Callback(
            storage=storage,
            timestamp=timestamp,
            **cb
        )
        callbacks.append(cb_obj)

    # replace input and output files
    for repl_arg in REPLACE_ARGS:
        if repl_arg in task_form:
            del task_form[repl_arg]
    task = models.Task(
        id=task_uuid,
        timestamp=timestamp,
        storage=storage,
        input_files=input_files,
        output_files=output_files,
        callbacks=callbacks,
        logger=logger,
        **task_form
    )
    # replace a number of dynamic items, water level and output directory
    task.subtasks[0].kwargs["h_a"] = h_a
    # replace output to a uuid-formed output path
    task.subtasks[0].kwargs["output"] = os.path.join(task_path, "OUTPUT")
    return task
# def local_tasks(
#         task_template,
#         temp_path,
#         incoming_video_path=settings.incoming_path,
#         logger=logging
# ):
#     # Create an event object
#     if settings is None:
#         raise IOError("For local processing, a settings file must be present in /settings/config.json. Please create or modify your settings accordingly")
#     logger.info(f"Start listening to new videos in folder {incoming_video_path}")
#     nodeorc_event = threading.Event()
#     logger.info(f"I am monitoring {incoming_video_path}")
#
#     # make a list for processed files or files that are being processed so that they are not duplicated
#     processed_files = set()
#
#     # Create and start the thread
#     nodeorc_thread = threading.Thread(
#         target=folder_monitor,
#         args=(
#             incoming_video_path,
#             temp_path,
#             task_template,
#             logger,
#             processed_files,
#             nodeorc_event,
#             2
#         )
#     )
#     nodeorc_thread.start()
#     try:
#         # Your main program can continue running here
#         while not nodeorc_event.is_set():
#             time.sleep(1)
#         print("Folder monitor event was triggered. Exiting the program.")
#     except KeyboardInterrupt:
#         # Handle Ctrl+C to stop the program
#         nodeorc_event.set()
#         nodeorc_thread.join()
#     # Cleanup and exit
#     print("Program terminated.")
#
#
#
