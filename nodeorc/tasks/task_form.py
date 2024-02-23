import sys
from datetime import datetime
import json
import logging
import os
import requests
import time
from urllib.parse import urljoin
import uuid

from nodeorc.models import Task
from nodeorc.db.models import TaskForm, TaskFormStatus, DeviceFormStatus


def wait_for_task_form(session, callback_url, device, timeout=5, logger=logging):
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

    while True:
        # keep on trying to get a new task form until successful
        task_form = request_task_form(session, callback_url, device, logger=logger)
        # r = requests.get(
        #     url,
        #     data=device.as_dict,
        #     headers=headers
        # )
        # if r.status_code == 204:
        #     logger.info(f'No new task form found at {t_str}')
        # if r.status_code == 200:
        #     # new message found, validate and if valid, exit(0)
        #     logger.info(f'New task form found at {t_str}, validating ...')
        #     task_form = r.json()
        #     # get rid of device
        #     task_form.pop("device")
        #     if validate_task_form(task_form, logger):
        #         # pop any fields that are not required
        #         task_form.pop("creator")
        #         task_form.pop("institute")
        #         task_form["created_at"] = datetime.strptime(task_form["created_at"], "%Y-%m-%dT%H:%M:%S.%fZ")
        #         task_form["id"] = uuid.UUID(task_form["id"])
        #         task_form["status"] = TaskFormStatus.CANDIDATE
        #         device.form_status = DeviceFormStatus.VALID_FORM
        #         # store the task form in the database
        #         task_form_rec = TaskForm(**task_form)
        #     # find if there is a status.CANDIDATE task form
        #     query = session.query(TaskForm)
        #     query.filter_by(status=TaskFormStatus.CANDIDATE)
        #     if len(query.all()) > 0:
        #         for item in query:
        #             item.status = TaskFormStatus.ANCIENT
        #     # store the new validated task form as candidate
        #     session.add(task_form_rec)
        #     session.commit()
        if task_form:
            # new task form found, reboot service
            logger.info("Rebooting service...")
            os._exit(0)

        time.sleep(timeout)


def request_task_form(session, callback_url, device, logger=logging):
    try:
        url = urljoin(str(callback_url.url), f"/api/device/{device.id}/get_task_form/")
        headers = {"Authorization": f"Bearer {callback_url.token_access}"}
        t_str = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        if datetime.utcnow() > callback_url.token_expiration:
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
            logger.info(f'No new task form found at {t_str}')
            return None
        if r.status_code == 200:
            # new message found, validate and if valid, exit(0)
            logger.info(f'New task form found at {t_str}, validating ...')
            task_form = r.json()
            # get rid of device
            task_form.pop("device")
            if validate_task_form(task_form, logger):
                # pop any fields that are not required
                task_form.pop("creator")
                task_form.pop("institute")
                task_form["created_at"] = datetime.strptime(task_form["created_at"], "%Y-%m-%dT%H:%M:%S.%fZ")
                task_form["id"] = uuid.UUID(task_form["id"])
                task_form["status"] = TaskFormStatus.CANDIDATE
                device.form_status = DeviceFormStatus.VALID_FORM
                # store the task form in the database
                task_form_rec = TaskForm(**task_form)
            # find if there is a status.CANDIDATE task form
            query = session.query(TaskForm)
            query.filter_by(status=TaskFormStatus.CANDIDATE)
            if len(query.all()) > 0:
                for item in query:
                    item.status = TaskFormStatus.ANCIENT
            # store the new validated task form as candidate
            session.add(task_form_rec)
            session.commit()
            return task_form_rec

    except:
        logger.error(f"Could not connect to server {callback_url.url}, check your connection...")
        return None


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

