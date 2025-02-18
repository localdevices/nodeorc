import concurrent.futures
import copy
import datetime
import logging
import multiprocessing
import os
import shutil
import sys
import threading
import time
import uuid
from urllib.parse import urljoin

import numpy as np

from nodeorc.tasks import request_task_form
from nodeorc import models, disk_mng, db, db_ops, utils, water_level, __home__
from tests.test_cross_section import camera_config

session = db_ops.get_session()
device = session.query(db.Device).first()

REPLACE_ARGS = ["input_files", "output_files", "storage", "callbacks"]

class LocalTaskProcessor:
    def __init__(
            self,
            task_form_template,
            callback_url: db.CallbackUrl,
            settings: db.Settings,
            water_level_settings: dict,
            disk_management: db.DiskManagement,
            max_workers: int = 1,
            auto_start_threads: bool = True,
            logger=logging,

    ):
        self.task_form_template = task_form_template
        self.settings = settings
        self.video_file_ext = settings.video_file_fmt.split(".")[-1]
        self.disk_management = disk_management
        self.callback_url = callback_url.pydantic
        self.water_level_settings = water_level_settings
        self.max_workers = max_workers  # for now we always only do one job at the time
        self.logger = logger
        self.processing = False  # state for checking if any processing is going on
        self.reboot = False  # state that checks if a scheduled reboot should be done
        self.water_level_file_template = os.path.join(self.disk_management.water_level_path, self.water_level_settings["file_template"])
        # make a list for processed files or files that are being processed so that they are not duplicated
        self.processed_files = set()
        self.logger.info(f'Water levels will be searched for in {self.water_level_file_template} using a datetime format "{water_level_settings["datetime_fmt"]}')
        self.logger.info(f"Start listening to new videos in folder {self.disk_management.incoming_path}.")
        self.event = threading.Event()

        # Create and start the thread
        self.thread = threading.Thread(
            target=self.await_task,
        )
        # add a thread for regular retrieval of water levels
        self.water_level_thread = threading.Thread(
            target=self.add_water_level
        )
        if auto_start_threads:
            # automatically start threads
            self.start_threads()

    def start_threads(self):
        self.thread.start()
        self.water_level_thread.start()
        try:
            # No events would mean the program can stop
            while not self.event.is_set():
                time.sleep(1)
            self.logger.info("await_task event was triggered. Exiting the program.")
        except KeyboardInterrupt:
            # Handle Ctrl+C to stop the program
            self.event.set()
            self.thread.join()
        # Cleanup and exit
        self.logger.info("Program terminated.")


    def await_task(self, single_task=False):
        # Get the number of available CPU cores
        max_workers = np.minimum(
            self.max_workers,
            multiprocessing.cpu_count()
        )
        # start the timer for the disk manager
        disk_mng_t0 = time.time()
        reboot_t0 = time.time()
        get_task_form_t0 = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            while not self.event.is_set():
                if not os.path.isdir(self.disk_management.home_folder):
                    # usually happens when USB drive is removed
                    self.logger.info(
                        f"Home folder {self.disk_management.home_folder} is not "
                        f"available, probably disk is removed. Reboot to try to find "
                        f"disk. "
                    )
                    os._exit(1)

                file_paths = disk_mng.scan_folder(
                    self.disk_management.incoming_path,
                    suffix=self.video_file_ext
                )
                for file_path in file_paths:
                    # each file is checked if it is not yet in the queue and not
                    # being written into
                    if os.path.isfile(file_path) and \
                            file_path not in self.processed_files and \
                            not utils.is_file_size_changing(file_path):
                        self.logger.info(f"Found file: {file_path}")
                        # Submit the file processing task to the thread pool
                        executor.submit(
                            self.process_file,
                            file_path,
                        )
                        # make sure the file is in the list of processed files to ensure the task is not
                        # duplicated to another thread instance
                        self.processed_files.add(file_path)
                        if single_task:
                            # only one task must be performed, return
                            return True
                time.sleep(5)  # wait for 5 secs before re-investigating the monitored folder for new files
                # do housekeeping, reboots, new task forms, disk management
                if self.settings.reboot_after != 0:
                    if time.time() - reboot_t0 > max(self.settings.reboot_after, 3600) and not self.reboot:
                        self.logger.info(f"Reboot scheduled after any running task after {max(self.settings['reboot_after'], 3600)} seconds")
                        self.reboot = True
                self.reboot_now_or_not()
                if time.time() - get_task_form_t0 > 300:
                    get_task_form_t0 = time.time()
                    self.get_new_task_form()
                if time.time() - disk_mng_t0 > self.disk_management.frequency:
                    # reset the disk management t0 counter
                    disk_mng_t0 = time.time()
                    self.logger.info(
                        f"Checking for disk space exceedance of {self.disk_management.min_free_space}"
                    )
                    free_space = disk_mng.get_free_space(
                        self.disk_management.home_folder
                    )
                    if free_space < self.disk_management.min_free_space:
                        self.cleanup_space(free_space=free_space)

    def add_water_level(self, single_task=False):
        session = db_ops.get_session()
        self.logger.info("Starting thread for retrieving water levels")
        # TODO: retrieve water level parameters and only if available run this!
        if self.water_level_settings:
            while not self.event.is_set():
                try:
                    self.logger.info("Checking for water levels.")
                    timestamp, level = water_level.execute_water_level_script(
                        script=self.water_level_settings["script"],
                        script_type=self.water_level_settings["script_type"].name,
                    )
                    self.logger.info(f"Water level found for timestamp {timestamp} with value {level}. Will add to database if not already existing.")
                    db_ops.add_water_level(session=session, timestamp=timestamp, level=level)
                    if single_task:
                        return timestamp, level
                except Exception as e:
                    self.logger.error(f"Error in retrieval of water levels: {e}")
                # sleep for configured amount of seconds
                time.sleep(self.water_level_settings["frequency"])
            self.logger.info("Water level thread terminated.")
        else:
            self.logger.info("No water level parameters configured, skipping retrieval.")


    def cleanup_space(self, free_space):
        """
        Free up space on disk by removing oldest files first.
        First success and failed paths are cleaned, then results path is cleaned.

        Parameters
        ----------
        free_space : float
            GB amount of free space currently available

        """
        ret = disk_mng.purge(
            [
                str(self.disk_management.failed_path)
            ],
            free_space=free_space,
            min_free_space=self.disk_management.min_free_space,
            logger=self.logger,
            home=self.disk_management.home_folder
        )
        # if returned is False then continue purging the results path
        if not ret:
            self.logger.warning(f"Space after purging still not enough, purging results folder")
            ret = disk_mng.purge(
                [
                    str(self.disk_management.results_path)
                ],
                free_space=free_space,
                min_free_space=self.disk_management.min_free_space,
                logger=self.logger,
                home=self.disk_management.home_folder
            )
        if not ret:
            self.logger.warning(f"Not enough space freed up. Checking for critical space.")
            # final computation of free space
            free_space = disk_mng.get_free_space(
                self.disk_management.home_folder,
            )
            if free_space < self.disk_management.critical_space:
                # shutdown the service to secure the device!
                self.logger.error(
                    f"Free space is under critical threshold of {self.disk_management.critical_space}. Shutting down NodeORC service"
                )
                os.system("/usr/bin/systemctl disable nodeorc")
                os.system("/usr/bin/systemctl stop nodeorc")
                sys.exit(1)
            else:
                self.logger.warning(
                    f"Free space is {free_space} which is not yet under critical space {self.disk_management.critical_space}. Please contact your supplier for information.")

    def get_new_task_form(self):
        new_task_form_row = request_task_form(
            session=session,
            callback_url=self.callback_url,
            device=device,
            logger=self.logger
        )
        if new_task_form_row:
            # replace the task form template
            self.task_form_template = new_task_form_row.task_body

    def process_file(
            self,
            file_path,
    ):

        # before any processing, check for new task forms online
        self.get_new_task_form()


        task_uuid = uuid.uuid4()
        task_path = os.path.join(
            self.disk_management.tmp_path,
            str(task_uuid)
        )
        # ensure the tmp path is in place
        if not(os.path.isdir(task_path)):
            os.makedirs(task_path)
        # now we really start processing
        self.processing = True
        try:
            url, filename = os.path.split(file_path)
            cur_path = file_path
            self.logger.info(f"Processing file: {file_path}")
            # determine time stamp
            try:
                timestamp = get_timestamp(
                    file_path,
                    parse_from_fn=self.settings.parse_dates_from_file,
                    fn_fmt=self.settings.video_file_fmt,
                )
            except Exception as e:
                timestamp = None
                message = f"Could not get a logical timestamp from file {file_path}. Reason: {e}"
                device.message = message
                session.commit()
                raise ValueError(message)
                # set message on device
            # create Storage instance
            self.logger.info(f"Timestamp for video found at {timestamp.strftime('%Y%m%dT%H%M%S')}")

            # create a preliminary video record in database
            video = db.Video(
                timestamp=timestamp,
                status=db.VideoStatus.TASK,
            )
            session.add(video)
            session.commit()
            session.refresh(video)

            # change storage to match nodeorc api requirements
            storage = models.Storage(
                url=os.path.join(__home__, "uploads", "videos", timestamp.strftime("%Y%m%d")),
                bucket_name=str(video.id)
            )
            #
            # storage = models.Storage(
            #     url=str(self.disk_management.results_path),
            #     bucket_name=timestamp.strftime("%Y%m%d")
            # )
            # move the file to the intended bucket
            if not(os.path.isdir(storage.bucket)):
                os.makedirs(storage.bucket)
            os.rename(file_path, os.path.join(storage.bucket, filename))
            # update the location of the current path of the video file (only used in exception)
            cur_path = os.path.join(storage.bucket, filename)
            # collect water level
            # timestamp_level, h_a = get_water_level(
            rec = get_water_level(
                timestamp,
                file_fmt=self.water_level_file_template,
                datetime_fmt=self.water_level_settings["datetime_fmt"],
                allowed_dt=self.settings.allowed_dt,
                logger=self.logger
            )
            # retrieve water level from time series record
            h_a = rec.h
            # create the task object from all data
            task = create_task(
                self.task_form_template,
                task_uuid,
                task_path,
                storage,
                filename,
                timestamp,
                h_a,
                logger=self.logger
            )
            # set cur_path to tmp location (only used on exception)
            cur_path = os.path.join(task_path, filename)
            # process the task
            task.execute(task_path)

            if self.disk_management.results_path:
                dst_path = os.path.join(
                    self.disk_management.results_path,
                    timestamp.strftime("%Y%m%d")
                )
            # video is success, if task form is still CANDIDATE, upgrade to ACCEPTED
            db_ops.patch_active_config_to_accepted()
            # perform the callbacks here only when video was successfully completed
            # set files and cleanup
            self._set_results_to_final_path(cur_path, storage.bucket, filename, task_path)
            # if the video was treated successfully, then store a record in the database
            rel_path_name = os.path.relpath(storage.bucket, os.path.join(__home__, "uploads"))
            video.time_series_id = rec.id,
            video.file = f"{rel_path_name}/{filename}"
            video.image = f"{rel_path_name}/{task.output_files['jpg'].remote_name}"
            video.status = db.VideoStatus.DONE
            session.commit()
            # very finally, perform the callback
            callback_success = self._post_callbacks(task.callbacks)
            if callback_success:
                video.sync_status = True
            else:
                video.sync_status = False
            session.commit()

        except Exception as e:
            callback_success = False  # video was unsuccessful so callbacks are also not successful
            message = f"Error processing {file_path}: {str(e)}"
            device.message = message
            video.status = db.VideoStatus.ERROR
            session.commit()
            self.logger.error(message)
            # find back the file and place in the failed location, organised per day
            if timestamp:
                dst_path = os.path.join(self.disk_management.failed_path, timestamp.strftime("%Y%m%d"))
            else:
                dst_path = self.disk_management.failed_path
            # set files and cleanup
            self._set_results_to_final_path(cur_path, dst_path, filename, task_path)
            # also check if the current form is a CANDIDATE form. If so report to device and roll back to the ACCEPTED FORM
            task_form_template = db_ops.get_active_task_form(session, parse=False)

        # once done, the file is removed from list of considered files for processing
        self.processed_files.remove(file_path)
        # if callbacks were successful, try to send off old callbacks that were not successful earlier
        if callback_success:
            self.logger.debug("Checking for old callbacks to send")
            self._post_old_callbacks()
        # processing done, so set back to False
        self.logger.debug("Processing done, setting processing state to False")
        self.processing = False
        # shutdown if configured to shutdown after task
        self._shutdown_or_not()
        # check if any reboots are needed and reboot
        self.reboot_now_or_not()

    def _set_results_to_final_path(self, cur_path, dst_path, filename, task_path):
        """ move the results from temp to final destination and cleanup """
        if not os.path.isdir(dst_path):
            os.makedirs(dst_path)
        dst = os.path.join(dst_path, filename)
        os.rename(cur_path, dst)
        self.logger.debug(f"Video file moved from {cur_path} to {dst_path}")

        if os.path.isdir(task_path):
            # remove any left over temporary files
            shutil.rmtree(task_path)

    def _shutdown_or_not(self):
        if self.settings.shutdown_after_task:
            self.logger.info("Task done! Shutting down in 15 seconds")
            os.system("/usr/bin/sleep 15 && /sbin/shutdown -h now")
            os.system("/usr/bin/sleep 15 && /bin/sudo /sbin/shutdown -h now")
            os.system("/usr/bin/sleep 15 && /usr/bin/sudo /sbin/shutdown -h now")

    def _post_callbacks(self, callbacks):
        """
        Performs callbacks in a list, and returns True when all were successful

        Parameters
        ----------
        callbacks : list[Callback]

        Returns
        -------
        True / False (all successful or not)
        """
        # get the name of callback
        success = True
        for callback in callbacks:

            url = urljoin(str(self.callback_url.url), callback.endpoint)
            self.logger.info(f"Sending {callback.func_name} callback to {url}")
            store_callback = False
            r = self.callback_url.send_callback(callback)
            if r is None:
                success = False
                self.logger.error(
                    f"Connection to {url} failed, connection error"
                )
                store_callback = True
            elif r.status_code != 201 and r.status_code != 200:
                success = False
                self.logger.error(
                    f'callback to {url} failed with error code {r.status_code}, storing callback in database'
                )
                store_callback = True
            if store_callback:
                # something went wrong while sending, store callback for a later re-try
                self.logger.info(f"Storing callback in database to prevent loss of data")
                callback.to_db()

        return success

    def reboot_now_or_not(self):
        """
        Check for reboot requirement and reboot if nothing is being processed
        """
        if self.reboot:
            # check if any processing is happening, if not, then reboot, else wait
            if not self.processing:
                self.logger.info("Rebooting now")
                utils.reboot_now()


    def _post_old_callbacks(self):
        """
        Try to post remaining non-posted callbacks and change their states in database
        if successful
        """
        callback_records = session.query(db.Callback)
        callbacks = [cb.callback for cb in callback_records]
        # send off
        success = True
        for callback_record in callback_records:
            callback = callback_record.callback
            url = urljoin(str(self.callback_url.url), callback.endpoint)
            self.logger.info(f"Sending {callback.func_name} callback to {url}")
            r = self.callback_url.send_callback(callback)
            if r is None:
                success = False
                self.logger.error(
                    f"Connection to {url} failed, connection error, stopping posts"
                )
            elif r.status_code != 201 and r.status_code != 200:
                self.logger.error(
                    f'callback to {url} failed with error code {r.status_code}, skipping record'
                )
            if not(success):
                # immediately stop the processing of callbacks
                break
            session.delete(callback_record)
            session.commit()


def get_timestamp(
    fn,
    parse_from_fn,
    fn_fmt,
):
    """
    Find time stamp from file name using expected file name template with datetime fmt

    Parameters
    ----------
    fn : str
        filename path
    parse_from_fn : bool
        If set to True, filename is used to parse timestamp using a filename template,
        if False, timestamp is retrieved from the last change datetime of the file
    fn_fmt : filename template with datetime format between {}

    Returns
    -------
    datetime
        timestamp of video file

    """
    if parse_from_fn:
        datetime_fmt = fn_fmt.split("{")[1].split("}")[0]
        fn_template = fn_fmt.replace(datetime_fmt, "")
        prefix, suffix = fn_template.split("{}")
        if not(prefix in fn) or not(suffix in fn):
            raise ValueError(f"File naming of video {fn} does not follow the template {fn_fmt}. . Please change settings.json")
        if len(prefix) > 0:
            timestr = fn.split(prefix)[1]
        else:
            timestr = os.path.basename(fn)
        if len(suffix) > 0:
            timestr = timestr.split(suffix)[0]
        try:
            timestamp = datetime.datetime.strptime(timestr, datetime_fmt)
        except:
            raise ValueError(f"datetime string {timestr} does not follow the datetime format {datetime_fmt}. Please change settings.json")
    else:
        timestamp = datetime.datetime.fromtimestamp(os.path.getmtime(fn))
    return timestamp


def get_water_level(
    timestamp,
    file_fmt,
    datetime_fmt,
    allowed_dt=10,
    session=session,
    logger=logging
):
    try:
        # first try to get water level from database
        rec = db_ops.get_water_level(session, timestamp, allowed_dt)
        logger.info(f"Water level found in database at closest timestamp {timestamp} with value {h_a} m.")
    except Exception as db_ex:
        logger.warning(f"Failed to fetch water level from database at timestamp {timestamp.strftime('%Y%m%dT%H%M%S')}. Trying data file.")
        try:
            # fallback to getting water level from file
            h_a = water_level.get_water_level_file(
                timestamp,
                file_fmt=file_fmt,
                datetime_fmt=datetime_fmt,
                allowed_dt=allowed_dt
            )

            logger.info(f"Water level found in file with value {h_a} m.")
            rec = db_ops.add_water_level(session, timestamp, h_a)
        except Exception as e:
            message = f"Could not obtain a water level for date {timestamp.strftime('%Y%m%d')} at timestamp {timestamp.strftime('%Y%m%dT%H%M%S')}. Reason: {e}"
            device.message = message
            session.commit()
            raise ValueError(message)
    return rec


def create_task(
    task_form_template,
    task_uuid,
    task_path,
    storage,
    filename,
    timestamp,
    h_a,
    logger=logging
):
    """
    Create task for specific video file from generic task form

    Parameters
    ----------
    task_form_template : dict
        task form with specifics to be filled in
    task_uuid : uuid
        unique task id
    task_path : str
        path to temporary location where task is conducted
    storage : permanent storage for results
    filename : str
        name of video file
    timestamp : datetime
        timestamp of video
    h_a : float
        actual water level during video
    logger : logging
        logger object

    Returns
    -------
    Task
        specific task for video

    """
    task_form = copy.deepcopy(task_form_template)
    # prepare input_files field in task definition
    input_files = {
        "videofile": models.File(
            remote_name=filename,
            tmp_name=filename
        )
    }
    # output file templates are filled in with the timestamp
    output_files = {
        k: models.File(
            remote_name=v["remote_name"].format(timestamp.strftime('%Y%m%dT%H%M%S')),
            tmp_name=v["tmp_name"]
        ) for k, v in task_form["output_files"].items()
    }
    all_files = dict(**input_files, **output_files)
    # callback jsons are converted to Callback objects
    callbacks = []
    for cb in task_form["callbacks"]:
        # replace/remove time stamp
        if "timestamp" in cb:
            cb.pop("timestamp")
        if "storage" in cb:
            cb.pop("storage")
        if "file" in cb:
            file = cb.pop("file")
            if file:
                cb["file"] = output_files[file]
        if "files_to_send" in cb:
            files_to_send = cb.pop("files_to_send")
            if files_to_send:
                cb["files_to_send"] = {fn: all_files[fn] for fn in files_to_send}
        cb_obj = models.Callback(
            storage=storage,
            timestamp=timestamp,
            **cb
        )
        callbacks.append(cb_obj)

    # remove instantaneous keys
    if "id" in task_form:
        task_form.pop("id")
    if "timestamp" in task_form:
        task_form.pop("timestamp")
    # replace input and output files
    for repl_arg in REPLACE_ARGS:
        if repl_arg in task_form:
            del task_form[repl_arg]
    task = models.Task(
        id=task_uuid,
        timestamp=timestamp,
        storage=storage,
        input_files=input_files,
        output_files=output_files,
        callbacks=callbacks,
        logger=logger,
        **task_form
    )
    # replace a number of dynamic items, water level and output directory
    task.subtasks[0].kwargs["h_a"] = h_a
    # replace output to a uuid-formed output path
    task.subtasks[0].kwargs["output"] = os.path.join(task_path, "OUTPUT")
    return task
