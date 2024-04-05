import sys
from datetime import datetime
import json
import logging
import os
import requests
import time
import traceback

from urllib.parse import urljoin
import uuid
import json

from ..models import Task
from ..db.models import TaskForm, TaskFormStatus, DeviceFormStatus
from .. import utils, __home__

config_file = os.path.join(__home__, "task_form.json")


def wait_for_task_form(session, callback_url, device, timeout=300, reboot_after=0., logger=logging):
    """
    Keep looking for a task form for the device, remotely and locally. When found, the service will shutdown
    and auto-reboot if running as service.

    Parameters
    ----------
    session : sqlalchemy session
    callback_url : CallBackUrl
        url and credentials to LiveORC server
    device : Device record
        required to hand-shake and update status messages on LiveORC side
    timeout : amount of seconds to try connection
    logger : Logging
        logger of nodeorc

    """
    reboot_t0 = time.time()
    while True:
        # keep on trying to get a new task form from configured server until successful
        task_form = request_task_form(session, callback_url, device, logger=logger)
        # also try to get a task form from local file
        # if not task_form:
        #     task_form = request_local_task(config_file, session, device, logger=logger)
        if task_form:
            # new task form found, reboot service
            logger.info("New task form setup. Reboot service...")
            os._exit(0)
        if time.time() - reboot_t0 > reboot_after:
            logger.info(f"Rebooting device after {reboot_after} seconds")
            utils.reboot_now()
        time.sleep(timeout)

def request_task_form(session, callback_url, device, logger=logging):
    """
    request a task form, trying both remote and local retrieval

    Parameters
    ----------
    session : sqlalchemy Session
    callback_url : CallbackUrl
            LiveORC URL and credentials
    device : Device record
        required to hand-shake and update status messages on LiveORC side
    logger: Logging
        NodeORC logger object

    Returns
    -------
    task_form: TaskForm
        database record containing all deserialized task form details
    """
    task_form = request_remote_task_form(
        session,
        callback_url,
        device,
        logger=logger
    )
    # also try to get a task form from local file
    if not task_form:
        task_form = request_local_task_form(
            session,
            config_file,
            device,
            logger=logger
        )
    return task_form

def request_remote_task_form(session, callback_url, device, logger=logging):
    """
    Request task from LiveORC server

    Parameters
    ----------
    session : sqlalchemy Session
    callback_url : CallbackUrl
            LiveORC URL and credentials
    device : Device record
        required to hand-shake and update status messages on LiveORC side
    logger: Logging
        NodeORC logger object

    Returns
    -------
    task_form: TaskForm
        database record containing all deserialized task form details

    """
    try:
        url = urljoin(str(callback_url.url), f"/api/device/{device.id}/get_task_form/")
        url_patch = urljoin(str(callback_url.url), f"/api/device/{device.id}/patch_task_form/")

        headers = {"Authorization": f"Bearer {callback_url.token_access}"}
        t_str = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        if datetime.utcnow() > callback_url.token_expiration:
            logger.info("Token expired, requesting new token...")
            # first refresh tokens
            callback_url.refresh_tokens()
            # update headers
            headers = {"Authorization": f"Bearer {callback_url.token_access}"}

        r = requests.get(
            url,
            data=device.as_dict,
            headers=headers
        )
        if r.status_code == 204:
            logger.info(f'No new task form found at {url}')
            return None
        if r.status_code == 200:
            # new message found, validate and if valid, exit(0)
            logger.info(f'New task form found at {t_str}, validating ...')
            task_form = r.json()
            # get rid of device
            task_form.pop("device")
            if validate_task_body(task_form["task_body"], logger):
                # pop any fields that are not required
                task_form.pop("creator")
                task_form.pop("institute")
                task_form["created_at"] = datetime.strptime(task_form["created_at"], "%Y-%m-%dT%H:%M:%S.%fZ")
                task_form["id"] = uuid.UUID(task_form["id"])
                task_form["status"] = TaskFormStatus.CANDIDATE
                device.form_status = DeviceFormStatus.VALID_FORM
                # store the task form in the database
                task_form_rec = TaskForm(**task_form)
                task_patch = {
                    "id": task_form["id"],
                    "status": TaskFormStatus.ACCEPTED.value
                }

            else:
                task_patch = {
                    "id": task_form["id"],
                    "status": TaskFormStatus.REJECTED.value
                }
            save_new_task_form(session, task_form_rec)

            # patch the task to get feedback on the other side of the line
            r = requests.patch(
                url_patch,
                data=task_patch,
                headers=headers
            )
            return task_form_rec

    except Exception as e:
        logger.error(f"Could not connect to server {callback_url.url}, with following information: {e}. check your connection...")
        traceback.print_exc()
        return None


def request_local_task_form(session, config_file, device, logger=logging):
    """

    Parameters
    ----------
    session : sqlalchemy Session
    config_file : str
         Path to file containing configuration
    device : Device record
        required to hand-shake and update status messages on LiveORC side
    logger: Logging
        NodeORC logger object

    Returns
    -------
    task_form: TaskForm
        database record containing all deserialized task form details


    """
    if not os.path.isfile(config_file):
        return None
    logger.info(f"config file found at {config_file}")
    try:
        with open(config_file, "r") as f:
            task_body = json.load(f)
        if validate_task_body(task_body, logger):
            # create a complete task form
            task_form = {
                "id": uuid.uuid4(),
                "created_at": datetime.utcnow(),
                "status": TaskFormStatus.CANDIDATE,
                "task_body": task_body
            }
            device.form_status = DeviceFormStatus.VALID_FORM
            task_form_rec = TaskForm(**task_form)
            save_new_task_form(session, task_form_rec)
        else:
            logger.error(f"Task form in {config_file} is not valid.")
            task_form_rec = None
        # after having tried the file remove.
    except Exception as e:
        logger.error(f"Problem while parsing task form, error {e}.")
        task_form_rec = None
    logger.info(f"Removing task form file {config_file}")
    os.remove(config_file)
    return task_form_rec


def validate_task_body(task_body: dict, logger=logging):
    """
    Validates a newly received task form. If valid, it stores the task form as "status.CANDIDATE" so as the form can be
    tried on a full run. Only after one run is finished successfully will the task form become the status.ACCEPTED

    Parameters
    ----------
    task_body: dict
        serialized task form details

    Returns
    -------
    bool
    """

    # check if the task form body is a valid task form template
    try:
        task_form_template = Task(**task_body)
    except Exception as e:
        logger.error(
            f"Task form found but task body is invalid. Reason: {str(e)}")
        return False
    return True


def save_new_task_form(session, task_form_rec):
    """
    Save a newly found task as CANDIDATE. also ensures that old CANDIDATE forms are made ANCIENT

    Parameters
    ----------
    session : sqlalchemy Session
    task_form_rec : TaskForm
        task form record to store


    """
    # find if there is a status.CANDIDATE task form
    query = session.query(TaskForm)
    query.filter_by(status=TaskFormStatus.CANDIDATE)
    if len(query.all()) > 0:
        for item in query:
            item.status = TaskFormStatus.ANCIENT
    # store the new validated task form as candidate
    session.add(task_form_rec)
    session.commit()
