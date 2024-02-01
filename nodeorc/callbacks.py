import numpy as np
import os
import requests
import xarray as xr
import logging as logger

# all functions in this files are meant to create callbacks for end points
# # Inputs must be as follows: task, subtask, tmp
# Each function MUST return a message body as serializable dict and a files set in the form:
# {'<name of field>': ('<name of file>', file_pointer), '<name of other field>': ... etcetera}]
# [('<name of field>', ('<name of file>', file_pointer))]

# if no files are returned, then simply make files=None

def discharge(callback):
    # open the last file, which contains the transect
    fn = os.path.join(
        callback.storage.url,
        callback.storage.bucket_name,
        callback.file.remote_name
    )
    ds = xr.open_dataset(fn)
    h = float(ds.h_a)
    Q = np.abs(ds.river_flow.values)
    if "q_nofill" in ds:
        ds.transect.get_river_flow(q_name="q_nofill")
        Q_nofill = np.abs(ds.river_flow.values)
        perc_measured = Q_nofill / Q * 100  # fraction that is truly measured compared to total
    else:
        perc_measured = np.nan * Q
    # make a json message
    msg = {
        "timestamp": callback.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "h": h if np.isfinite(h) else None,
        "q_05": Q[0] if np.isfinite(Q[0]) else None,
        "q_25": Q[1] if np.isfinite(Q[1]) else None,
        "q_50": Q[2] if np.isfinite(Q[2]) else None,
        "q_75": Q[3] if np.isfinite(Q[3]) else None,
        "q_95": Q[4] if np.isfinite(Q[4]) else None,
        "fraction_velocimetry": perc_measured[2] if np.isfinite(perc_measured[2]) else None  # only pass the 50th percentile
    }
    # add the static kwargs
    msg = {**msg, **callback.kwargs}
    files = None
    return msg, files

def video(callback):
    """
    Creates a video callback of an already processed video. Assumes that the processing status is DONE

    Parameters
    ----------
    task
    subtask
    tmp
    kwargs

    Returns
    -------

    """
    video_fn = os.path.join(
        callback.storage.url,
        callback.storage.bucket_name,
        callback.files_to_send["videofile"].remote_name
    )
    video_name = callback.files_to_send["videofile"].remote_name
    img_fn = os.path.join(
        callback.storage.url,
        callback.storage.bucket_name,
        callback.files_to_send["jpg"].remote_name
    )
    img_name = callback.files_to_send["jpg"].remote_name
    files = {
        "file": (video_name, open(video_fn, "rb")),
        "image": (img_name, open(img_fn, "rb"))
    }
    msg = {
        "timestamp": callback.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": 4,
    }
    msg = {**msg, **callback.kwargs}
    return msg, files

def video_no_file(callback):
    img_fn = os.path.join(
        callback.storage.url,
        callback.storage.bucket_name,
        callback.files_to_send["jpg"].remote_name
    )
    img_name = callback.files_to_send["jpg"].remote_name
    files = {
        "image": (img_name, open(img_fn, "rb"))
    }
    msg = {
        "timestamp": callback.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": 4,
    }
    msg = {**msg, **callback.kwargs}
    return msg, files


# def file_not_found(base_url, endpoint, task, fn, logger=logger):
#     msg = f"File {fn} not found after task {task}"
#     logger.error(msg)
#     url = f"{base_url}/{endpoint}"
#     requests.post(
#         url,
#         json={"error": msg}
#     )
#
#
# def error_from_task(base_url, endpoint, task, error, logger=logger):
#     msg = f"Task {task} returned error {str(repr(error))}"
#     logger.error(msg)
#     url = f"{base_url}/{endpoint}"
#     requests.post(
#         url,
#         json={"error": msg}
#     )
