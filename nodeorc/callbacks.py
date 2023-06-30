import requests

import logging as logger
def post_discharge():
    raise NotImplementedError

def post_file_not_found(base_url, endpoint, task, fn, logger=logger):
    msg = f"File {fn} not found after task {task}"
    logger.error(msg)
    url = f"{base_url}/{endpoint}"
    requests.post(
        url,
        json={"error_message": msg}
    )


def post_error_from_task(base_url, endpoint, task, error, logger=logger):
    msg = f"Task {task} returned error {str(repr(error))}"
    logger.error(msg)
    url = f"{base_url}/{endpoint}"
    requests.post(
        url,
        json={"error_message": msg}
    )
