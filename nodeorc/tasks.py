import threading
import concurrent.futures
import logging
import numpy as np
import os
import time
import datetime
import models
import pandas as pd

WATER_LEVEL_WILDCARD = os.getenv("WATER_LEVEL_WILDCARD")  # full file path template with a wildcard {} at the end for seeking a file. Within {} a %Y%m%d string is expected
VIDEO_DATETIMEFMT = os.getenv("VIDEO_DATETIMEFMT", "%Y%m%dT%H%M%S")  # Format used to produce file names and datetime stamps in water level files
WATER_LEVEL_DATETIMEFMT = os.getenv("WATER_LEVEL_DATETIMEFMT", "%Y%m%d_%H%M%S")  # Format used to produce file names and datetime stamps in water level files
VIDEO_FILE_FMT = os.getenv("VIDEO_FILE_FMT")  # string format of files. space in {} is assumed to be filled with a datetime of format VIDEO_DATETIMEFMT
PARSE_DATE_FROM_FILENAME = bool(os.getenv("PARSE_DATE_FROM_FILENAME", "False").lower() == "true")  # if True, then the datetime
CALLBACK_URL = "http://172.0.0.2:1080"
VIDEO_RESULTS = "/home/hcwinsemius/nodeorc/results"
FAILED_PATH = os.getenv("FAILED_PATH")
SUCCESS_PATH = os.getenv("SUCCESS_PATH")
# is taken from the filename, otherwise datetime is taken from the file's metadata. The last is adviced when power
# cycling without a Real-Time-Clock is used, as then the time on the filename is not correct


def get_timestamp(
    fn,
    parse_from_fn=PARSE_DATE_FROM_FILENAME,
    fn_fmt=VIDEO_FILE_FMT,
    datetimefmt=VIDEO_DATETIMEFMT
):
    if parse_from_fn:
        prefix, suffix = fn_fmt.split("{}")
        timestr = fn.split(prefix)[1].split(suffix)[0]
        timestamp = datetime.datetime.strptime(timestr, datetimefmt)
    else:
        timestamp = datetime.datetime.fromtimestamp(os.path.getmtime(fn))
    return timestamp


def read_water_level_file(fn, fmt):
    date_parser = lambda x: pd.datetime.strptime(x, fmt)
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
    fn_wildcard=WATER_LEVEL_WILDCARD,
    datetimefmt=WATER_LEVEL_DATETIMEFMT
):
    # get the file belonging to current date, water levels MUST be stored per day!
    fn = fn_wildcard.format(timestamp.strftime("%Y%m%d"))
    df = read_water_level_file(fn, fmt=datetimefmt)
    t = timestamp.strftime("%Y%m%d %H:%M:%S")
    # find the closest match
    i = np.minimum(np.maximum(df.index.searchsorted(t), 0), len(df) - 1)
    h_a = df.iloc[i].values[0]
    return h_a


def process_file(file_path, temp_path, task_template, processed_files, logger=logging):
    try:
        url, filename = os.path.split(file_path)
        cur_path = file_path
        logger.info(f"Processing file: {file_path}")
        # determine time stamp
        try:
            timestamp = get_timestamp(file_path)
        except:
            raise ValueError(f"Could not get a logical timestamp from file {file_path}")
        # create Storage instance
        storage = models.Storage(url=VIDEO_RESULTS, bucket_name=timestamp.strftime("%Y%m%d"))
        # move the file to the intended bucket
        if not os.path.isdir(storage.bucket):
            os.makedirs(storage.bucket)
        os.rename(file_path, os.path.join(storage.bucket, filename))
        # update the location of the current path of the video file
        cur_path = os.path.join(storage.bucket, filename)
        # collect water level
        try:
            h_a = get_water_level(timestamp)
        except:
            raise ValueError(f"Could not obtain a water level for date {timestamp.strftime('%Y%m%d')} at timestamp {timestamp.strftime('%Y%m%dT%H%M%S')}")

        # prepare input_files field in task definition
        input_files = {
            "videofile": models.File(
                remote_name=filename,
                tmp_name=filename
            )
        }
        output_files = {
            "piv": models.File(
                remote_name=f"piv_{timestamp.strftime('%Y%m%dT%H%M%S')}.nc",
                tmp_name="OUTPUT/piv.nc"
            ),
            "piv_mask": models.File(
                remote_name=f"piv_mask_{timestamp.strftime('%Y%m%dT%H%M%S')}.nc",
                tmp_name="OUTPUT/piv_mask.nc"
            ),
            "transect": models.File(
                remote_name=f"transect_1_{timestamp.strftime('%Y%m%dT%H%M%S')}.nc",
                tmp_name="OUTPUT/transect_transect_1.nc"
            ),
            "jpg": models.File(
                remote_name=f"plot_quiver_{timestamp.strftime('%Y%m%dT%H%M%S')}.jpg",
                tmp_name="OUTPUT/plot_quiver.jpg"
            ),

        }
        callback_url = models.CallbackUrl(url=CALLBACK_URL)

        task = models.Task(
            time=timestamp,
            callback_url=callback_url,
            storage=storage,
            input_files=input_files,
            output_files=output_files,
            logger=logger,
            **task_template
        )

        # replace water level
        task.subtasks[0].kwargs["h_a"] = h_a
        # set cur_path to tmp location
        cur_path = os.path.join(temp_path, filename)
        # process the task
        task.execute(temp_path)


    except Exception as e:
        logger.error(f"Error processing {file_path}: {str(e)}")
        # find back the file and place in the failed location
        dst = os.path.join(FAILED_PATH, filename)
        os.rename(cur_path, dst)


    # once done, the file is removed from list of considered files for processing
    processed_files.remove(file_path)


def local_tasks(task_template, incoming_video_path, temp_path, logger=logging):
    # Create an event object

    nodeorc_event = threading.Event()
    logger.info(f"I am monitoring {incoming_video_path}")

    # make a list for processed files or files that are being processed so that they are not duplicated
    processed_files = set()

    # Create and start the thread
    nodeorc_thread = threading.Thread(
        target=folder_monitor,
        args=(
            incoming_video_path,
            temp_path,
            task_template,
            logger,
            processed_files,
            nodeorc_event,
            2
        )
    )
    nodeorc_thread.start()
    try:
        # Your main program can continue running here
        while not nodeorc_event.is_set():
            time.sleep(1)
        print("Folder monitor event was triggered. Exiting the program.")
    except KeyboardInterrupt:
        # Handle Ctrl+C to stop the program
        nodeorc_event.set()
        nodeorc_thread.join()
    # Cleanup and exit
    print("Program terminated.")


# Define the function that will run in the thread to monitor the folder
def folder_monitor(folder_path, temp_path, task_template, logger, processed_files, event, max_workers=1):
    # Get the number of available CPU cores
    # num_cores = multiprocessing.cpu_count()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        while not event.is_set():
            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)
                if os.path.isfile(file_path) and file_path not in processed_files:
                    print(f"Found file: {file_path}")
                    # Submit the file processing task to the thread pool
                    executor.submit(process_file, file_path, temp_path, task_template, processed_files, logger)
                    processed_files.add(file_path)
                    # # Optionally, you can move or delete the processed file
                    # os.remove(file_path)
            time.sleep(1)  # Adjust the sleep interval as needed

