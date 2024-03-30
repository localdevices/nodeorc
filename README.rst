.. _readme::

================
NodeOpenRiverCam
================

|pypi| |piwheels| |docs_latest| |license|


  Both NodeOpenRiverCam and LiveOpenRiverCam are currently under development for their first release. The first
  release of both OpenRiverCam components is planned in May 2024. Until that time please stay up to date on this
  page. The documentation will change significantly during this period. We do not provide any feedback on questions
  until the first release is out.

What is NodeOpenRiverCam
========================

NodeOpenRiverCam enables velocimetry analysis and discharge estimation of videos in the cloud or directly on a site,
using the underlying pyOpenRiverCam library. It is meant to operate together with a LiveOpenRiverCam server which
collects data from multiple nodeOpenRiverCam instances, orchestrates and distributes new tasks to them. You
can connect as many NodeOpenRiverCam devices to a LiveOpenRiverCam server as you want.

NodeOpenRiverCam is being developed in the TEMBO Africa project. The TEMBO Africa project has received funding from the
European Union's Horizon Europe research and innovation programme under greant agreement No. 101086209.

.. figure:: docs/static/front.jpg
    :height: 600px

    NodeOpenRiverCam site with processing occurring on the fly, and data sent to the LiveOpenRiverCam platform.
    Credits SEBA and Photrack for site setup and the hardware.

Getting started
===============

To get started with NodeOpenRivercam, you will need the following:

* A device on which to setup NodeORC. This can be a local device running on the site where videos are collected or a
  cloud device. The device should be connected to internet. For local processing, the device should also have sufficient
  storage available.
* For edge-processing (i.e. on the site itself), a camera is needed that can take videos regularly and store this on a
  designated location on the device. If you use a raspberry pi, we recommend using on the same device a raspberry pi
  camera.
* Also for edge processing, water levels must be automatically collected and stored in a predefined file format. Water
  levels will then automatically be read and matched against incoming videos.
* A LiveOpenRiverCam server from which to configure the device. If you want to collect videos on a laptop, and
  connect that laptop in the field to the device, then you can also setup LiveOpenRiverCam with Docker on your laptop.
  Please visit LiveORC_ for more information how to set this up. You have to make sure that the local LiveOpenRiverCam
  instance and the device are on the same network. If you plan to configure the device in the field, we recommend to
  ensure the device can connect to a WiFi hotspot, which is available in the field. Note that no internet connection is
  needed, only a local network.
* A username and password for the LiveOpenRiverCam server. Please set this up following the documentation of LiveORC_.

And that's it! With these in place you are ready to go.

Installation
============

To install the latest release of NodeOpenRiverCam on your device, there are two options, native installation (only
on linux devices) or a docker installation (also on Windows or Mac):

Native installation
-------------------

    NodeOpenRiverCam is entirely rasperry pi compliant. You do need an ARM64 bit device (Raspberry Pi 4 or higher)
    and about 1.5GB storage for the software, excluding the operating system. We recommend a SD card of 16GB, but
    at the very least you will require 8 GB. For storage of videos and results we strongly recommend NOT to use
    the SD card as many I/O operations on SD cards are known to corrupt the SD card in due time. We recommend to
    use a USB-drive. This drive can be hot swapped if you wish to keep raw data and videos.

A native installation is highly recommended on a local device as it reduces overhead significantly. For a native
installation, please download the setup.sh script from the latest release on the device on which you wish to install it,
make the script executable and execute the script on a command line interface with the option ``--all``. The steps
are outlined below:

.. code-block:: shell

    # get script from latest release
    wget https://github.com/localdevices/nodeorc/releases/latest/setup.sh
    # make the setup script executable
    chmod +x setup.sh
    # execute script
    ./setup.sh --all

The setup procedure will ask several inputs including the url and your username and password for the LiveOpenRiverCam
server. Note that these credentials will not be stored on the device, but only used to receive a temporary access token
and refresh token. If you use a local LiveOpenRiverCam instance, then this will report on https://127.0.0.1:8000
Please use this URL and ensure that the local LiveOpenRiverCam instance is running on your computer in the same network.

You can also perform installation steps one-by-one. If you wish to see the options of the setup script, then simply
use:

.. code-block:: shell

    ./setup.sh

without any arguments.

Docker installation
-------------------
We are still working on a docker image for NodeORC. Please stay tuned. Once the docker image is there you can install
docker on your device or cloud instance and pull the image using a command such as (exact location of the image is
still to be determined):

.. code-block:: shell

    docker pull localdevice/nodeorc

We will ensure that you can also use the setup script for a docker installation, so that you can supply the required
information for setup in a similar way as a native installation.

Usage
=====

Cloud processing
----------------

    We are still working on cloud-usage of NodeOpenRiverCam. Currently only edge processing is supported. Once this
    is supported, you can setup NodeOpenRiverCam on one or more cloud-nodes, connected to a LiveOpenRiverCam platform
    and have the nodes process individual videos that are uploaded to the LiveOpenRiverCam server. This will work
    through a queueu manager.

Edge processing
---------------

If you have followed the setup script for deploying NodeOpenRiverCam, then the device should have a name, defined by
yourself, and it should be able to receive tasks and report to a LiveOpenRiverCam instance. If your device is able to
communicate to the configured LiveOpenRiverCam instance, it will announce its existence automatically. As it
is freshly configured it does not have any tasks to perform yet, and therefore it will regularly report in
(every 5 minutes) to see if any new task is available. If so, it will download and validate the task, and if the task
is valid, store it and start using it. Storing of tasks and configurations is done through a local database.

For preparing task forms (i.e. templates for performing tasks on any video coming in) we refer to the LiveORC_
documentation.

During the setup procedure, you will have identified a location to store any information related to NodeORC.
This is the "home folder" of NodeORC.
After you have set this up, everything, including the database of processed videos, callbacks, the raw videos,
processed result files (NetCDF data files, JPG images), log files, and so on, will all be stored under that same
folder. If you have selected USB-drive storage, then the USB drive is *always* mounted under ``/mnt/usb`` and this
folder will automatically be configured as the "home folder"
The subfolder structure under this home folder is as follows:

.. code-block::

    .
    ├── nodeorc_data.db     <- database holding records of nodeorc videos and callbacks.
    ├── log                 <- folder holding log files in subfolders. One subfolder is created per calendar day.
    ├── results             <- folder holding result files in subfolders. One subfolder is created per calendar day.
    ├── incoming            <- folder in which new video files are expected. You must configure your camera such that it
    │                          writes videos in THIS folder, using a specified naming convention with a datetime string.
    ├── failed              <- if a video fails, then the raw video will be stored here in subfolders. One subfolder is
    │                          created per calendar day.
    ├── success             <- if a video is successfully processed it will be stored here in subfolders after
    │                          processing. One subfolder is created per calendar day.
    ├── tmp                 <- during processing, a temporary folder will be created here in which the raw video and
    │                          output files will be stored. Once successful, the tmp content will be moved to
    │                          results (output) and success (raw video)
    ├── water_level         <- text or csv files are expected under this folder, holding the water level. The text
    │                          files can have specific naming conventions that include a datestring so that
    │                          water levels may be stored in files per day. The format in the files can be
    │                          defined in a configuration message.

We follow this structure to allow a better understanding of the working methods.

Getting videos into the right folder
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
If you have for instance identified the USB-drive as location for storage, then incoming videos must be reported
in ``/mnt/usb/incoming``. If you for instance have a raspberry pi setup, and you want to make a regular video upon
booting the device, you may for instance run a script upon boot that looks as follows (make sure your raspi camera
is switched on and that the necessary libraries are installed). The script can be run e.g. through a cronjob or
by adding it to your profile.

.. code-block::

    #!/bin/bash
    # NOTE! THIS CODE HAS NOT BEEN TESTED.
    # make a datetime string, to identify the utc time of the video
    export trg_path="/mnt/usb/incoming"
    export dt=`date '+%Y%m%d_%H%M%S'`
    filename=${trg_path}/${dt}.h264
    # record the video
    raspivid --height 1080 --bitrate 20000000 --timeout 5 --framerate 30 --output ${filename}

For other camera setups, the manner in which you get videos in the right folder may strongly depend on the brand and
type. Most likely camera-specific settings are needed.

Supplying water levels
^^^^^^^^^^^^^^^^^^^^^^
At this moment, NodeORC cannot (yet) read water levels optically. This means that some form of water levels must be
supplied in a text file. We support a simple text file that contains no header, and a space separated set of water
levels. By default, NodeORC will look for a file called ``all_levels.txt`` in the ``water_level`` folder under your
supplied home folder. For reconfiguration of this file, we refer to the reconfiguration section written below.
Within this file, it is expected that water levels are written in a high enough frequency to be able to match
them against dates and times of incoming videos. The closest date and time found will be used. The format of the content
of this file is a space-separated .csv file without headers with 2 columns in it: the first column contains a date-time
string (without spaces). The second column contains the water levels. See for example the series shown below.

.. code-block::

    20221222_000000 92.367
    20221222_001500 92.367
    20221222_004500 92.367
    20221222_010000 92.367
    20221222_011500 92.368
    20221222_013000 92.37
    20221222_014500 92.378
    20221222_020000 92.384
    20221222_021500 92.386
    20221222_024500 92.384
    20221222_030000 92.378
    20221222_031500 92.374
    20221222_033000 92.373
    20221222_034500 92.373
    20221222_040000 92.377
    20221222_041500 92.383
    20221222_044500 92.389
    20221222_050000 92.391
    20221222_051500 92.398
    20221222_053000 92.419
    20221222_054500 92.44
    20221222_060000 92.444
    20221222_061500 92.444
    20221222_064500 92.463
    20221222_070000 92.468
    20221222_071500 92.473
    20221222_073000 92.475
    20221222_074500 92.476
    20221222_080000 92.481
    20221222_081500 92.489

TODO COMPLETE

Reconfiguring NodeORC
=====================

General instructions
--------------------

If you wish to modify the configuration after you have installed NodeORC, you can currently only do this on the device
itself. You must login to the device (e.g. headless via SSH or graphically via a VNC connection or Teamviewer
connection) move to the folder of installation and then execute:

.. code-block:: shell

    $ python nodeorc upload-config <NAME OF JSON-FILE>

Here you should replace <NAME OF JSON-FILE> by a JSON file that contains the relevant details. You can find the
JSON file with your settings from the setup procedure in the ``settings`` folder under the name ``config_device.json``.
From here you can modify the settings. In the subsections below you can find instructions for several settings.
If a settings is not passing through validation, for instance because you use strings where numbers are expected
(or vice versa) or the format of the JSON-file contains syntax errors, you will receive an error message. Please
read this carefully before continuing. Below we describe the most important cases for changing the configuration.

  We are working on allowing for changes in configurations within the LiveORC front end. Soon you will also be able
  to reconfigure remotely using the LiveORC web platform. Please stay posted.


Configuring the file locations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

During the setup, you have identified a logical file path under which incoming videos, results, and water levels are
stored. If you have opted for use of a USB-drive, then this location is always ``/mnt/usb``.

Configuring the home folder
^^^^^^^^^^^^^^^^^^^^^^^^^^^
The home folder is the folder in which all incoming videos are stored, where results of video analyses are stored,
where the database with callbacks is stored, and where videos that have been successful or not are stored. These
different files are all located in different subfolders, as shown above with the example for the home folder being
``/mnt/usb``. If you wish to alter the home folder location then you can do this by modifying the ``home_folder``
in the subsection ``disk_management``. For instance, if you have an edge device with an SSD drive you could use your
user-home folder and point it to ``/home/user/nodeorc_data``. We here assume that ``user`` is the username of the
current device.

This would look as follows in the JSON-configuration file.

.. code-block::

    {
       ...
        "disk_management": {
            "home_folder": "/home/user/nodeorc_data",
            ...
        }
    }

Configuring the file naming convention of videos
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
While you may store videos in the ``incoming`` folder, nodeorc has to be able to extract the exact datetime format
from the file name. You will need to specify the file naming convention in the configuration of NodeORC. This can
be configured during the installation process, but you can also alter the video naming convention in the
LiveOpenRiverCam platform by making a new configuration message for the device.

A typical file (taken from our raspberry camera example) may for instance be:

.. code-block::

    20240229_100003.h264

Where year (2024), month (02), day (29), hour (10), minute (00) and second (03) are supplied as datestring.
You can instruct NodeORC to parse the date and time following a datetime template. In this example, the template
would be

.. code-block::

    {%Y%m%d_%H%M%S}.h264

Here ``%Y`` means the 4-digit year, ``%m`` is the 2-digit month, ``%d`` is the 2-digit day in the month, ``%H`` the
2-digit hour, ``%M`` the 2-digit minute and ``%S`` the 2-digit second. NodeORC will try to parse a date using the
string template between the curly braces (i.e. ``{`` and ``}``). The assumed time is always UTC!!! This is crucial
in order to ensure that there is never a timezone issue between the platform on which videos are read and treated
(NodeORC) and the platform where results are stored, displayed and redistributed (LiveORC).

This file naming convention can be configured by altering the field ``video_file_fmt`` under the ``settings`` section in
the JSON file.

.. code-block::

    {
       ...
        "settings": {
            ...,
            "video_file_fmt": "{%Y%m%d_%H%M%S}.h264",
            ...
        }
    }

The above example would configure the file naming convention as shown in the example.

  Don't forget to place commas between each field inside a JSON section, and no comma after the last field of a section.
  Also don't forget to open a section with a curly brace ``{`` and close it with a curly brace ``}``.



.. _LiveORC: https://github.com/localdevices/LiveORC

.. |pypi| image:: https://badge.fury.io/py/nodeopenrivercam.svg
    :alt: PyPI
    :target: https://pypi.org/project/nodeopenrivercam/

.. |piwheels| image:: https://img.shields.io/piwheels/v/:wheel
   :alt: PiWheels Version
   :target: https://localdevice.github.io/nodeorc/latest

.. |docs_latest| image:: https://img.shields.io/badge/docs-latest-brightgreen.svg
    :alt: Latest documentation
    :target: https://localdevice.github.io/nodeorc/latest


.. |license| image:: https://img.shields.io/github/license/localdevices/nodeorc?style=flat
    :alt: License
    :target: https://github.com/localdevices/nodeorc/blob/main/LICENSE

