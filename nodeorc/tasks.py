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
VIDEO_DATETIMEFMT = os.getenv("VIDEO_DATETIMEFMT", "%Y%m%d_%H%M%S")  # Format used to produce file names and datetime stamps in water level files
VIDEO_FILE_FMT = os.getenv("VIDEO_FILE_FMT")  # string format of files. space in {} is assumed to be filled with a datetime of format VIDEO_DATETIMEFMT
PARSE_DATE_FROM_FILENAME = bool(os.getenv("PARSE_DATE_FROM_FILENAME", "False").lower() == "true")  # if True, then the datetime
CALLBACK_URL = "http://127.0.0.1:1080"
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
    datetimefmt=VIDEO_DATETIMEFMT
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
    logger.info(f"Processing file: {file_path}")
    # determine time stamp
    timestamp = get_timestamp(file_path)

    # collect water level
    h_a = get_water_level(timestamp)

    # prepare input_files field in task definition
    input_files = {
        "videofile": models.File(
            remote_name=file_path,
            tmp_name=file_path
        )
    }
    callback_url = models.CallbackUrl(url=CALLBACK_URL)

    task = models.Task(
        time=timestamp,
        callback_url=callback_url,
        input_files=input_files,
        logger=logger,
        **task_template
    )

    # replace water level
    task.subtasks[0].kwargs["h_a"] = h_a

    # process the task
    task.execute(temp_path)

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

