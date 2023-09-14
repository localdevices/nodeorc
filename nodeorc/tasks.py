import copy
import dask
import shutil
import threading
import concurrent.futures
import logging
import multiprocessing
import numpy as np
import os
import time
import datetime
from . import models
import pandas as pd
from dask.distributed import Client

REPLACE_ARGS = ["input_files", "output_files", "storage"]
class LocalTaskProcessor:
    def __init__(
            self,
            task_form,
            temp_path: str,
            incoming_path: str,
            failed_path: str,
            success_path: str,
            results_path: str,
            parse_dates_from_file: bool,
            video_file_fmt: str,
            water_level_fmt: str,
            water_level_datetimefmt: str,
            max_workers: int = 1,
            logger=logging,
    ):
        self.task_form = task_form
        self.temp_path = temp_path
        self.incoming_path = incoming_path
        self.failed_path = failed_path
        self.success_path = success_path
        self.results_path = results_path
        self.parse_dates_from_file = parse_dates_from_file
        self.video_file_fmt = video_file_fmt
        self.water_level_ftm = water_level_fmt
        self.water_level_datetimefmt = water_level_datetimefmt
        self.max_workers = max_workers
        self.logger = logger
        # make a list for processed files or files that are being processed so that they are not duplicated
        self.processed_files = set()
        self.logger.info(f"Start listening to new videos in folder {self.incoming_path}")
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
        max_workers = np.minimum(self.max_workers, multiprocessing.cpu_count())
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            while not self.event.is_set():
                for filename in os.listdir(self.incoming_path):
                    file_path = os.path.join(self.incoming_path, filename)
                    if os.path.isfile(file_path) and file_path not in self.processed_files:
                        print(f"Found file: {file_path}")
                        # Submit the file processing task to the thread pool
                        executor.submit(
                            self.process_file,
                            file_path,
                        )
                        # make sure the file is in the list of processed files to ensure the task is not
                        # duplicated to another thread instance
                        self.processed_files.add(file_path)
                        # # Optionally, you can move or delete the processed file, usually not needed
                        # os.remove(file_path)
                time.sleep(1)  # wait for a sec before re-investigating the monitored folder for new files

    def process_file(
            self,
            file_path,
    ):
        # ensure the tmp path is in place
        if not(os.path.isdir(self.temp_path)):
            os.makedirs(self.temp_path)
        try:
            url, filename = os.path.split(file_path)
            cur_path = file_path
            self.logger.info(f"Processing file: {file_path}")
            # determine time stamp
            try:
                timestamp = get_timestamp(
                    file_path,
                    parse_from_fn=self.parse_dates_from_file,
                    fn_fmt=self.video_file_fmt
                )
            except Exception as e:
                raise ValueError(f"Could not get a logical timestamp from file {file_path}. Reason: {e}")
            # create Storage instance
            self.logger.info(f"Timestamp for video found at {timestamp.strftime('%Y%m%dT%H%M%S')}")
            storage = models.Storage(
                url=str(self.results_path),
                bucket_name=timestamp.strftime("%Y%m%d")
            )
            # move the file to the intended bucket
            if not os.path.isdir(storage.bucket):
                os.makedirs(storage.bucket)
            os.rename(file_path, os.path.join(storage.bucket, filename))
            # update the location of the current path of the video file (only used in exception)
            cur_path = os.path.join(storage.bucket, filename)
            # collect water level
            try:
                h_a = get_water_level(
                    timestamp,
                    file_fmt=self.water_level_ftm,
                    datetime_fmt=self.water_level_datetimefmt
                )
            except Exception as e:
                raise ValueError(f"Could not obtain a water level for date {timestamp.strftime('%Y%m%d')} at timestamp {timestamp.strftime('%Y%m%dT%H%M%S')}. Reason: {e}")
            task_form = copy.deepcopy(self.task_form)
            # prepare input_files field in task definition
            input_files = {
                "videofile": models.File(
                    remote_name=filename,
                    tmp_name=filename
                )
            }
            output_files = {
                k: models.File(
                    remote_name = v["remote_name"].format(timestamp.strftime('%Y%m%dT%H%M%S')),
                    tmp_name = v["tmp_name"]
                ) for k, v in task_form["output_files"].items()
            }
            # replace input and output files
            for repl_arg in REPLACE_ARGS:
                if repl_arg in task_form:
                    del task_form[repl_arg]
            task = models.Task(
                timestamp=timestamp,
                storage=storage,
                input_files=input_files,
                output_files=output_files,
                logger=self.logger,
                **task_form
            )

            # replace water level
            task.subtasks[0].kwargs["h_a"] = h_a
            # replace output
            task.subtasks[0].kwargs["output"] = self.temp_path + "/OUTPUT"
            # set cur_path to tmp location (only used on exception)
            cur_path = os.path.join(self.temp_path, filename)
            # process the task
            task.execute(self.temp_path)
            # if the video was treated successfully, then we may move it to a location of interest if wanted
            if self.success_path:
                # move the video
                [input_file.move(self.temp_path, self.success_path) for key, input_file in task.input_files.items()]


        except Exception as e:
            self.logger.error(f"Error processing {file_path}: {str(e)}")
            # find back the file and place in the failed location
            dst = os.path.join(self.failed_path, filename)
            os.rename(cur_path, dst)
        finally:
            if os.path.isdir(self.temp_path):
                # remove any left over temporary files
                shutil.rmtree((self.temp_path))
        # once done, the file is removed from list of considered files for processing
        self.processed_files.remove(file_path)


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
        timestr = fn.split(prefix)[1].split(suffix)[0]
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

):
    datetimefmt = file_fmt.split("{")[1].split("}")[0]
    water_level_template = file_fmt.replace(datetimefmt, ":s")
    water_level_fn = water_level_template.format(timestamp.strftime(datetimefmt))
    df = read_water_level_file(water_level_fn, fmt=datetime_fmt)
    t = timestamp.strftime("%Y%m%d %H:%M:%S")
    # find the closest match
    i = np.minimum(np.maximum(df.index.searchsorted(t), 0), len(df) - 1)
    h_a = df.iloc[i].values[0]
    return h_a


# def local_tasks(
#         task_template,
#         temp_path,
#         incoming_video_path=settings.incoming_path,
#         logger=logging
# ):
#     # Create an event object
#     if settings is None:
#         raise IOError("For local processing, a settings file must be present in /settings/settings.json. Please create or modify your settings accordingly")
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
# # Define the function that will run in the thread to monitor the folder
# def folder_monitor(
#         folder_path,
#         temp_path,
#         task_template,
#         logger,
#         processed_files,
#         event,
#         max_workers=1
# ):
#     # Get the number of available CPU cores
#     max_workers = np.minimum(max_workers, multiprocessing.cpu_count())
#     with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
#         while not event.is_set():
#             for filename in os.listdir(folder_path):
#                 file_path = os.path.join(folder_path, filename)
#                 if os.path.isfile(file_path) and file_path not in processed_files:
#                     print(f"Found file: {file_path}")
#                     # Submit the file processing task to the thread pool
#                     executor.submit(process_file, file_path, temp_path, task_template, processed_files, logger)
#                     processed_files.add(file_path)
#                     # # Optionally, you can move or delete the processed file
#                     # os.remove(file_path)
#             time.sleep(1)  # Adjust the sleep interval as needed
#
