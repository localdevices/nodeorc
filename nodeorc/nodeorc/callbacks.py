import numpy as np
import os
import requests
import xarray as xr

import logging as logger
def post_discharge(output_files, tmp="."):
    # open the last file, which contains the transect
    fn = os.path.join(tmp, output_files["transect"].tmp_name)
    ds = xr.open_dataset(fn)
    flow = list(ds.river_flow.values)
    Q = np.abs(ds.river_flow.values)
    if "q_nofill" in ds:
        ds.transect.get_river_flow(q_name="q_nofill")
        Q_nofill = np.abs(ds.river_flow.values)
        perc_measured = Q_nofill / Q * 100  # fraction that is truly measured compared to total
    else:
        perc_measured = np.nan * Q
    msg = {
        "values": list(Q),
        "perc_measured": list(perc_measured)
    }
    print(f"CALLBACK: {msg}")
    # make a json message
    return msg

def post_file_not_found(base_url, endpoint, task, fn, logger=logger):
    msg = f"File {fn} not found after task {task}"
    logger.error(msg)
    url = f"{base_url}/{endpoint}"
    requests.post(
        url,
        json={"error": msg}
    )


def post_error_from_task(base_url, endpoint, task, error, logger=logger):
    msg = f"Task {task} returned error {str(repr(error))}"
    logger.error(msg)
    url = f"{base_url}/{endpoint}"
    requests.post(
        url,
        json={"error": msg}
    )
