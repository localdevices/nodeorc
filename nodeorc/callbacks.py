import numpy as np
import os
import requests
import xarray as xr

import logging as logger
def discharge(output_files, tmp="."):
    # open the last file, which contains the transect
    fn = os.path.join(tmp, output_files["transect"].tmp_name)
    ds = xr.open_dataset(fn)
    flow = list(ds.river_flow.values)
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
        "h": h,
        "q_05": Q[0],
        "q_25": Q[1],
        "q_50": Q[2],
        "q_75": Q[3],
        "q_95": Q[4],
        "fraction_velocimetry": perc_measured[2]  # only pass the 50th percentile
    }
    return msg

def file_not_found(base_url, endpoint, task, fn, logger=logger):
    msg = f"File {fn} not found after task {task}"
    logger.error(msg)
    url = f"{base_url}/{endpoint}"
    requests.post(
        url,
        json={"error": msg}
    )


def error_from_task(base_url, endpoint, task, error, logger=logger):
    msg = f"Task {task} returned error {str(repr(error))}"
    logger.error(msg)
    url = f"{base_url}/{endpoint}"
    requests.post(
        url,
        json={"error": msg}
    )
