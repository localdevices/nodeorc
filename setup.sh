#!/bin/bash
man_help(){

    echo "========================================================================"
    echo "Setup of nodeorc operational service Linux"
    echo "========================================================================"
    echo ''
    echo 'This script is meant to fully deploy NodeORC on a device or cloud '
    echo 'instance. It has been tested with Debian-like systems and Raspberry Pi.'
    echo 'If installation issues arise, then please submit an issue on '
    echo ''
    echo 'https://github.com/localdevices/nodeorc/issues'
    echo ''
    echo 'NOTES'
    echo "========================================================================"

    echo 'For Raspberry by you MUST use 64-bit Raspberry pi OS. The software does '
    echo 'not work with 32-bit Raspberry Pi OS. '
    echo ' '
    echo 'Updating packages and installing them may take a significant time and '
    echo 'requires a good internet connection. Please ensure that prerequisites'
    echo '(good internet, enough time, enough coffee) are met before continuing.'
    echo ' '
    echo "========================================================================"


    echo 'Options:'
    echo '        --all'
    echo '                         Install all dependencies, software and setup of service in one go'
    echo ''
    echo '        --dependencies'
    echo '                         Install all dependencies'
    echo ''
    echo '        --nodeorc'
    echo '                         Install nodeorc environment including all python dependencies'
    echo ''
    echo '        --service'
    echo '                         Install nodeorc operational service as systemd service with 15-minute timer'
    echo ''
    echo 'The order in which you should install is (1) --dependencies (2) --nodeorc, (3) --service.'
    exit 0
}

install_dependencies () {
    echo "========================================================================"
    echo 'INSTALLING DEPENDENCIES'
    echo "========================================================================"
    if [[ `hostnamectl` =~ .*"CentOS".* ]];
    then
        echo "CentOS system detected, running yum"
	sudo yum -y update
	sudo yum install ffmpeg libsm6 libxext6 libgl1 python3-venv libgdal-dev jq -y
    elif [[ `hostnamectl` =~ .*"Ubuntu".* ]] || [[ `hostnamectl` =~ .*"pop-os".* ]] || [[ `hostnamectl` =~ .*"Mint".* ]] || [[ `hostnamectl` =~ .*"Debian".* ]];
    then
        echo "Ubuntu-like system detected, trying apt"
        sudo apt -y update
        sudo apt -y upgrade
        sudo apt install ffmpeg libsm6 libxext6 libgl1 python3-venv libgdal-dev jq -y
    else
        echo "System unknown I can't help you with updating"
        exit 1
    fi
  echo 'Dependencies installed. Now install NodeORC.'
}

install_nodeorc () {
    echo "========================================================================"
    echo 'INSTALLING NODEOPENRIVERCAM'
    echo "========================================================================"
        python3 -m venv $HOME/venv/nodeorc
        # activate the new environment
        source $HOME/venv/nodeorc/bin/activate
        # install the current source code
        pip install --upgrade nodeorc
        deactivate
    echo ''
    echo '------------------------------------------------------------------------'
    echo 'NodeORC installed. Now setup the automated service.'
    echo '------------------------------------------------------------------------'
}

install_service () {
    # export variables for some static files below
    export SCRIPT_FOLDER=$PWD/$(dirname $0)
    export CONFIG_TEMPLATE="${HOME}/.nodeorc/config_template.json"
    export CONFIG_NEW="${HOME}/.nodeorc/config_device.json"
    export CONFIG_DBASE=${HOME}/.nodeorc/nodeorc_config.db

    echo "========================================================================"
    echo 'CONFIGURE AND SETUP NODEORC AS A BACKGROUND SERVICE '
    echo "========================================================================"
    echo ""
    echo "In this installation part, NodeORC will be configured, and converted into an automatically running"
    echo "background service"
    echo ' '
    if ! test -f ${HOME}/venv/nodeorc/bin/activate
    then
        echo 'No virtual environment exists for nodeorc. please run ./setup.sh --nodeorc first.'
        exit 1
    fi
    source ${HOME}/venv/nodeorc/bin/activate
    if ! command -v nodeorc
    then
        echo 'NodeORC is not yet successfully installed, please run ./setup.sh --nodeorc first'
        deactivate
        exit 1
    fi
    deactivate
    echo 'is where NodeORC is detected and installed. Continue to install service ...'
    echo ''
    echo 'USER INPUT'
    echo '------------------------------------------------------------------------'
    echo 'We will need to collect some input from you to get NodeORC setup as a service.'
    echo ''
    echo 'The name of your device must be unique and well recognizable in the LiveORC front-end.'
    DEVICE_NAME="$(hostname)"
    echo "The current name of your device is ${DEVICE_NAME}. Do you want to change this? [Y/n] "
    read -s -N 1 CHANGE_DEVICE
    case $CHANGE_DEVICE in
        [Yy]* ) read -e -p "Enter your new device name: " DEVICE_NAME; export CHANGE_DEVICE="Yes";;
        * ) echo "No changes in device name will be made";export CHANGE_DEVICE="No";;
    esac
    echo "Your device name will be $DEVICE_NAME"
    echo ''
    # collect all information on LiveORC
    get_liveorc_data;
    # ask for info on storage options
    echo ''
    echo 'For portable devices running from SD-cards such as Raspberry-Pis we highly recommend to use an external device'
    echo 'for all the storage, including temporary storage of e.g. video files. We allow for use of USB drives or'
    echo 'pen drives that you can hot plug, and remove and replace as the drive may get full. If you use USB drives,'
    echo "then you don't need to specify a folder, as automatically the root of the USB drive will be used."
    echo 'If you wish to use another specific folder on your device (e.g. a separate SSD hard drive or other) then'
    echo 'you must specify that folder'
    echo ' '
    echo "Do you want to use portable hot pluggable USB storage? [Y/n] "
    read -s -N 1 USE_USB
    case $USE_USB in
        [Yy]* ) echo "USB storage will be used and mounted on /mnt/usb/. PLEASE INSERT YOUR USB DRIVE NOW!"; export USE_USB="Yes"; NODEORC_DATA_PATH="/mnt/usb";;
        * ) read -e -p "Please provide a valid path: " NODEORC_DATA_PATH; export USE_USB="No"; if [ ! -d $NODEORC_DATA_PATH ]; then echo "$NODEORC_DATA_PATH does not exist, please first make a valid data folder"; exit 1; fi;;
    esac

    echo '------------------------------------------------------------------------'
    echo "The NodeORC service will be setup with the following settings:"
    echo '------------------------------------------------------------------------'
    echo "Device name                               : ${DEVICE_NAME}"
    echo "LiveORC server                            : ${URL}"
    echo "LiveORC username                          : ${LOGIN}"
    echo "LiveORC password                          : ${PASSWD_STRING}"
    echo "Use USB storage Y/N                       : ${USE_USB}"
    echo "NodeORC storage path                      : ${NODEORC_DATA_PATH}"
    echo
    echo "Do you wish to continue with these settings? [Y/n] "
    read -s -N 1 CONTINUE
    if [[ ! $CONTINUE == [Yy] ]]
    then
        echo "You decided to stop the setup of the service. We hope to see you later."
        exit 0
    fi
    echo ""

    if [[ $USE_USB == "Yes" ]]
    then
        setup_usb_mount;
    fi
    if [[ $CHANGE_DEVICE == "Yes" ]]
    then
        echo "Setting hostname to ${DEVICE_NAME}"
        sudo hostnamectl set-hostname $DEVICE_NAME
        # also add hostname to list of hosts (2> /dev/null suppresses unknown host error)
        echo -e "127.0.1.1\t$(hostname)" | sudo tee -a /etc/hosts 2> /dev/null
    fi
    setup_nodeorc_config;
    setup_service_files;
    echo "If no error messages appeared, you should be all set. If you want to login again, please use the command: "
    echo ""
    echo "$ ssh $USER@$(hostname).local"
    echo ""
    echo "After logging in, you can check live what's going on using the following command: "
    echo ""
    echo "$ sudo journalctl -u nodeorc.service -f"
    echo ""
    echo "Device needs to reboot. Do you want to reboot now? [Y/n] "
    echo ""
    read -s -N 1 CONTINUE
    if [[ $CONTINUE == [Yy] ]]
    then
        echo "Thank you for this setup. Bye bye."
        echo "Rebooting device $(hostname)"
        sudo reboot now
        exit 0
    fi
}

main() {
    #display parameters
    echo 'Installation options provided: ' "$@"
    array=("$@")
    # if no parameters display help
    if [ -z "$array" ]                    ; then man_help                        ;fi
    for i in "${array[@]}"
    do
        if [ "$1" == "--help" ]           ; then man_help                        ;fi
        if [ "$i" == "--dependencies" ]   ; then install_dependencies            ;fi
        if [ "$i" == "--nodeorc" ]        ; then install_nodeorc                 ;fi
        if [ "$i" == "--service" ]        ; then install_service                 ;fi
        if [ "$i" == "--all" ]            ; then install_dependencies            && \
                                                 install_nodeorc                 && \
                                                 install_service                 ;fi
    done
}

get_liveorc_data(){
    echo 'This NodeORC device can connect to a LiveORC server, give status updates, receive new tasks and submit'
    echo 'results with callbacks. To enable this, you need to provide your LiveORC credentials. If you simply want to'
    echo 'use the device stand-alone and configure it via SSH, and pick up data physically, then you can skip this step.'
    echo ''
    echo 'Do you want to connect to a LiveORC server? [Y/n] '
    read -s -N 1 LIVEORC_YN
    case $LIVEORC_YN in
        [Yy]* ) export LIVEORC_YN="Yes";;
        * ) export LIVEORC_YN="No";;
    esac
    if [ $LIVEORC_YN == "Yes" ]
    then
        read -p "Provide an ip-address or remote hostname (without /api/) where your LiveOpenRiverCam is available: " URL
        # remove trailing slash if any
        if [ "${URL: -1}" == "/" ] ; then export URL=${URL:0:-1} ; fi
        read -p "Provide your email login to ${URL}: " LOGIN
        read -s -p "Provide your password to ${URL}: " PASSWD
        echo ''
        export data="{\"email\": \"${LOGIN}\", \"password\": \"${PASSWD}\"}"
        echo "Trying to receive access and refresh tokens from ${URL}/api/token/"
        export TOKEN=$(curl --silent --max-time 5 --location "${URL}/api/token/" --header 'Content-Type: application/json' --data-raw "$data")

        if [[ $TOKEN = *"No active account"* ]]
        then
            echo "No active account found with provided credentials on ${URL}. Please contact your system administrator."
            exit 1
        fi
        if [ "$TOKEN" = "" ]
        then
            echo "Host name ${URL} does not exist. Please contact your system administrator or check if you are "
            echo "connected to internet."
            exit 1
        fi
        if [[ $TOKEN != *"access"* ]]
        then
            echo "Tried to contact ${URL}/api/token/. The OpenRiverCam server exists,, but the end point seems "
            echo "incorrect. Ensure you are not referring to any end points."
            exit 1
        fi
        export ACCESS=$(echo $TOKEN | grep -o '"access":"[^"]*' | grep -o '[^"]*$')
        export REFRESH=$(echo $TOKEN | grep -o '"refresh":"[^"]*' | grep -o '[^"]*$')
        echo ''
        echo "Successfully connected to ${URL}/api/token and I found a access and refresh token for you. These will be "
        echo 'stored in the configuration.'
        echo ''
        export PASSWD_STRING="provided and valid (but not shown here :-)"
    else
        export LOGIN="N/A"
        export URL="N/A"
        export PASSWD_STRING="N/A"
    fi

}

setup_usb_mount() {
    export usb_mount_script="${SCRIPT_FOLDER}/service/usb-mount.sh"
    export usb_mount_service="${SCRIPT_FOLDER}/service/usb-mount@.service"
    export udev_rule_usb="${SCRIPT_FOLDER}/service/10-toggleusbstick.rules"

    # move usb mount in place and make executable
    echo "Making USB mount script available for running as a service"
    sudo cp $usb_mount_script /usr/local/bin
    # make usb mount script executable
    sudo chmod +x /usr/local/bin/usb-mount.sh

    # setup a systemctl service for mounting USB drives
    echo "Setup USB mount service as systemd service"
    sudo cp $usb_mount_service /etc/systemd/system
    sudo systemctl daemon-reload
    # setup new udev rules.
    echo "Making new udev rules for mounting and unmounting USB storage"
    sudo cp $udev_rule_usb /etc/udev/rules.d
    echo "Reloading udev rules."
    sudo udevadm control --reload-rules

    # now loop through usb devices and try to mount them using the new service
    for device in /dev/sd[a-z]*
    do
        sudo systemctl start usb-mount@${device##*/} > /dev/null 2>&1
    done
    # if no USB devices are found, then exit
    if [[ ! -d /mnt/usb ]]; then
        echo "I was not able to find a USB device. Did you forget to insert one? I am shutting down..."
        exit 1
    fi

}
setup_nodeorc_config(){
    source ${HOME}/venv/nodeorc/bin/activate
	cat > ${CONFIG_TEMPLATE} <<EOF
{
    "callback_url": {
        "url": "http://127.0.0.1:8000",
        "token_refresh_end_point": "/api/token/refresh/",
        "token_refresh": "",
        "token_access": ""
    },
    "storage": {
        "url": "./tmp",
        "bucket_name": "examplevideo"
    },
    "settings": {
        "parse_dates_from_file": true,
        "video_file_fmt": "{%Y%m%d_%H%M%S}.mp4",
        "water_level_fmt": "all_levels.txt",
        "water_level_datetimefmt": "%Y%m%d_%H%M%S",
        "allowed_dt": 3600,
        "shutdown_after_task": false,
        "reboot_after": 86400

    },
    "disk_management": {
        "home_folder": "",
        "min_free_space": 2,
        "critical_space": 1,
        "frequency": 3600
    }
}
EOF

    echo "Setting up configuration with LiveORC connection to ${URL}..."
    jq ".callback_url.url=\"${URL}\" | .callback_url.token_refresh=\"${REFRESH}\" | .callback_url.token_access=\"${ACCESS}\" | .disk_management.home_folder=\"${NODEORC_DATA_PATH}\"" ${CONFIG_TEMPLATE} > ${CONFIG_NEW}

    # we now have a solid configuration file, now initialize the database, and upload this to the database
    if [[ -f ${CONFIG_DBASE} ]]
    then
        echo "Removing old database file ${CONFIG_DBASE}"
        rm ${CONFIG_DBASE}
    fi
    echo "Uploading configuration to a fresh database"
    echo ""
    echo '------------------------------------------------------------------------'
    echo "Your first NodeORC logs will appear below."
    echo '------------------------------------------------------------------------'
    nodeorc upload-config ${CONFIG_NEW}
    # deactivate python environment
    echo '------------------------------------------------------------------------'
    deactivate
}

setup_service_files(){
    echo "Preparing nodeorc.service file for user ${USER}"
    cat > nodeorc.service <<EOF
[Unit]
Description=NodeOpenRiverCam operational edge or cloud compute instance
After=network.target

[Service]
User=${USER}
WorkingDirectory=${PWD}
Environment="PATH=${HOME}/venv/nodeorc/bin"
ExecStart=${HOME}/venv/nodeorc/bin/nodeorc start --storage local --listen local
Restart=always

[Install]
WantedBy=multi-user.target
EOF

    echo 'moving systemd files to /etc/systemd/system'
    sudo mv nodeorc.service /etc/systemd/system/
    # ensuring credentials are set correctly
    sudo chmod 644 /etc/systemd/system/nodeorc.service
    echo 'starting and enabling the pyorc service with systemd'
    sudo systemctl daemon-reload
    sudo systemctl start nodeorc.service
    sudo systemctl enable nodeorc.service
}

logo(){
    echo '
              +++++++++++++++************* %%%              @%%%%%%%%             %%%%%%%%%          @%%%@        %%%%
          +++++**************+++**********%%%%            %%%%%%%%%%%%%%       @%%%%%%%%%%%%%        %%%%%        %%%%
        +++********++***********+++*******%%%%          %%%%%%     %%%%%%     %%%%%%     @%%%       %%%%%%%       %%%%
      +++******+:::::::+**********+++*****%%%%         @%%%%          %%%%   %%%%%                 %%%%@%%%%      %%%%
     ++****#%%#+=-::::::+***********++****%%%%         %%%%           %%%%%  %%%%                 @%%%% %%%%@     %%%%
  @@%@@@@@@@@@@@@@@@@@@@%##**********++***%%%%         %%%%           %%%%%  %%%%                 %%%%   %%%%     %%%%
@@@@@@@@@%@@%%%##%@%####@@@%##########++**%%%%         %%%%           %%%%%  %%%%                %%%%@    %%%%    %%%%
  ++##%@@@%#@@@@@%*-+#=################++ %%%%         %%%%@          %%%%   %%%%%              %%%%%%%%%%%%%%@   %%%%
 ++*#####%%@@@%########################*+ %%%%          %%%%%        %%%%%   %%%%%@        %%   %%%%%%%%%%%%%%%   %%%%
 ++########%@@################%%%%@@%###++%%%%%%%%%%%%%  %%%%%%@ @%%%%%%%      %%%%%%% %%%%%%  %%%%        %%%%%  %%%%%%%%%%%%
 ++#########%%**########@@@@%@@@@@@@@@#*++%%%%%%%%%%%%%    %%%%%%%%%%%%         @%%%%%%%%%%%% %%%%%         %%%%% %%%%%%%%%%%%
 ++****@#***%@********##@@@@*@@@@@@@@@@*++                                           
 ++#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@#+  %%%%%%%%       %%%%%%%%% @%%%       %%%  %%%      %%%%%%%@    %%%%%%%%%    %%%%%%%
  ++%@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@%++ %%%%%%%%%%%%    %%%%%%%%%% %%%@     %%%%  %%%    %%%%%%%%%%%   %%%%%%%%%% @%%%%%%%%%
   +*%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%*+**%%%%     %%%%   %%%        @%%%     %%%@  %%%   %%%%      @%   %%%        %%%
    +*#######*######%#%#*#########*##*+***%%%%      %%%%  %%%         %%%%   %%%%   %%%  %%%%            %%%        @%%%%
     ++***#*#***#**##*#*###++##***+*++****%%%%       %%%  %%%%%%%%%    %%%@ %%%%    %%%  %%%@            %%%%%%%%%    %%%%%%%
      +++#***********+*****+*+*+**+++*****%%%%      @%%%  %%%%         @%%% %%%     %%%  %%%@            %%%@            %%%%%
        +++******+*********####*+++*******%%%%     %%%%@  %%%           %%%%%%%     %%%   %%%@       @   %%%               %%%
          ++++++*************++++*********%%%%%%%%%%%%    %%%%%%%%%%     %%%%%      %%%   @%%%%%%%%%%%%  %%%%%%%%%% %%%% @%%%%
              +++++++++++++++************* %%%%%%%%@      %%%%%%%%%@      %%%       %%%     @%%%%%%%%@   %%%%%%%%%% @%%%%%%%%
  '
}

logo "$@"

main "$@"
exit 0
