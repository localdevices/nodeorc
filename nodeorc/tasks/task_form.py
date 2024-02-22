from datetime import datetime
import logging
import os
import requests
import time
from urllib.parse import urljoin

from nodeorc.models import Task
from nodeorc.db.models import TaskForm, TaskFormStatus


def fetch_task_form(session, callback_url, device, timeout=5, logger=logging):
    """
    Keep looking for a task form for the device

    Parameters
    ----------
    session
    config
    timeout

    Returns
    -------

    """
    url = urljoin(str(callback_url.url), f"/api/device/{device.id}/get_task_form/")
    headers = {"Authorization": f"Bearer {callback_url.token_access}"}

    while True:
        t_str = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            if datetime.now() > callback_url.token_expiration:
                # first refresh tokens
                callback_url.refresh_tokens()
                # update headers
                headers = {"Authorization": f"Bearer {callback_url.token_access}"}
            r = requests.get(
                url,
                json=device.as_dict,
                headers=headers
            )
            if r.status_code == 204:
                logger.info(f'No new task form found at {t_str}')
            if r.status_code == 200:
                # new message found, validate and if valid, exit(0)
                logger.info(f'New task form found at {t_str}, validating ...')
                task_form = r.json()
                # get rid of device
                task_form.pop("device")
                if validate_task_form(task_form, logger):
                    # pop any fields that are not required
                    # store the task form in the database
                    task_form = TaskForm(**task_form)
                # find if there is a status.CANDIDATE task form
                query = session.query(TaskForm)
                query.filter_by(status=TaskFormStatus.CANDIDATE)
                if len(query.all()) > 0:
                    for item in query:
                        item.status = TaskFormStatus.ANCIENT
                # now set the current one
                task_form.status = TaskFormStatus.CANDIDATE
                # and finally store the new validated task form as candidate
                session.add(task_form)
                session.commit()

        except:
            logger.error(f"Could not connect to server {callback_url.url} at {t_str}, check your connection...")
        time.sleep(timeout)


def validate_task_form(task_form: dict, logger=logging):
    """
    Validates a newly received task form. If valid, it stores the task form as "status.CANDIDATE" so as the form can be
    tried on a full run. Only after one run is finished successfully will the task form become the status.ACCEPTED

    Parameters
    ----------
    task_form

    Returns
    -------

    """
    # check if the task form body is a valid task form template
    try:
        task_form_template = Task(**task_form["task_body"])
    except Exception as e:
        logger.error(
            f"Task file in {os.path.abspath(task_form)} cannot be formed into a valid Task instance. Reason: {str(e)}")
        return False
    return True

