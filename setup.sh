#!/bin/bash
man_help(){

    echo "========================================================================"
    echo "Setup of nodeorc operational service Linux"
    echo "========================================================================"
    echo ''
    echo ''
    echo 'Options:'
    echo '        --all'
    echo '                         Install all dependencies, and software and libraries as is'
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
        sudo apt install ffmpeg libsm6 libxext6 libgl1 python3-venv jq -y
    else
        echo "System unknown I can't help you with updating"
    fi
}


install_nodeorc () {
    echo "========================================================================"
    echo 'INSTALLING NODEOPENRIVERCAM'
    echo "========================================================================"
        pip3 install virtualenv
        python3 -m venv $HOME/venv/nodeorc
        # activate the new environment
        source $HOME/venv/nodeorc/bin/activate
        # install the current source code
        pip install .
}

install_service () {
    # export variables for some static files below
    export SCRIPT_FOLDER=$PWD/$(dirname $0)
    export CONFIG_TEMPLATE="${SCRIPT_FOLDER}/settings/config_template.json"
    export CONFIG_NEW="${SCRIPT_FOLDER}/settings/config_device.json"
    export CONFIG_DBASE=${HOME}/.nodeorc/nodeorc_config.db

    echo "========================================================================"
    echo 'INSTALLING SYSTEMD SERVICE '
    echo "========================================================================"
    echo ' '
    if ! test -f ${HOME}/venv/nodeorc/bin/activate
    then
        echo 'No virtual environment exists for nodeorc. please run ./setup.sh --nodeorc first.'
        exit 1
    fi
    source ${HOME}/venv/nodeorc/bin/activate
    if ! command -v nodeorc
    then
        echo 'NodeORC is not yet installed, please run ./setup.sh --nodeorc first'
        deactivate
        exit 1
    fi
    deactivate
    echo 'NodeORC is detected and installed. Continue to install service ...'
    echo ''
    echo 'USER INPUT'
    echo '------------------------------------------------------------------------'
    echo 'We will need to collect some input from you to get NodeORC setup as a service.'
    echo ''
    echo 'The name of your device must be unique and well recognizable in the LiveORC front-end.'
    DEVICE_NAME="$(hostname)"
    echo "The current name of your device is ${DEVICE_NAME}."
    read -p "Do you want to change this? [Y/n]" CHANGE_DEVICE
    case $CHANGE_DEVICE in
        [Yy]* ) read -e -p "Enter your new device name: " DEVICE_NAME; export CHANGE_DEVICE="Yes";;
        * ) echo "No changes in device name made";export CHANGE_DEVICE="No";;
    esac
    echo "Your device name will be $DEVICE_NAME"
    # collect all information on LiveORC
    get_liveorc_data;
    # ask for info on storage options
    echo ''
    echo 'For portable devices runnbing from SD-cards such as Raspberry-Pis we highly recommend to use an external device'
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
    echo "Device name                               : ${DEVICE}"
    echo "LiveORC server                            : ${URL}"
    echo "LiveORC username                          : ${LOGIN}"
    echo "LiveORC password                          : provided and valid (but not shown here :-)"
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
    echo "We are now here"

    if [[ $USE_USB == "Yes" ]]
    then
        setup_usb_mount;
    fi
    if [[ $CHANGE_DEVICE == "Yes" ]]
    then
        echo "Setting hostname to ${DEVICE_NAME}"
        hostnamectl set-hostname $DEVICE_NAME
    fi
    setup_nodeorc_config;
    setup_service_files;
    echo "You are all set, no need to reboot. To check out live what is going on in the back end you may always type:"
    echo ""
    echo "sudo journalctl -u nodeorc.service -f"
}

main() {
    #display parameters
    echo 'Installation options: ' "$@"
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
    read -p "Provide an ip-address or remote hostname (without /api/) where your LiveOpenRiverCam is available: " URL
    # remove trailing slash if any
    if [ "${URL: -1}" == "/" ] ; then export URL=${URL:0:-1} ; fi
    read -p "Provide your email login to ${URL}: " LOGIN
    read -s -p "Provide your password to ${URL}: " PASSWD
#    export URL="https://openrivercam.com"
#    export LOGIN="winsemius@rainbowsensing.com"
#    export PASSWD='^7JF!k93oqf$2EAl'
    export data="{\"email\": \"${LOGIN}\", \"password\": \"${PASSWD}\"}"
    export TOKEN=$(curl --silent --max-time 5 --location "${URL}/api/token/" --header 'Content-Type: application/json' --data-raw "$data")

#    export TOKEN=$(curl --silent --max-time 5 --location "${URL}/api/token/" --header 'Content-Type: application/json' --data-raw "{
#        \"email\": \"${LOGIN}\",
#        \"password\": \"${PASSWD}\"
#    }")
    if [[ $TOKEN = *"No active account"* ]]
    then
        echo "No active account found with provided credentials on ${URL}. Please contact your system administrator."
        exit 1
    fi
    if [ "$TOKEN" = "" ]
    then
        echo "Host name ${URL} does not exist. Please contact your system administrator or check if you are connected to internet."
        exit 1
    fi
    if [[ $TOKEN != *"access"* ]]
    then
        echo "${URL} seems to point to a OpenRiverCam server, but not to the right end point. Ensure you are not referring to any end points."
        exit 1
    fi
    export ACCESS=$(echo $TOKEN | grep -o '"access":"[^"]*' | grep -o '[^"]*$')
    export REFRESH=$(echo $TOKEN | grep -o '"refresh":"[^"]*' | grep -o '[^"]*$')
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

    echo "Setting up configuration with LiveORC connection to ${URL}..."
    jq ".callback_url.url=\"${URL}\" | .callback_url.token_refresh=\"${REFRESH}\" | .callback_url.token_access=\"${ACCESS}\"" ${CONFIG_TEMPLATE} > ${CONFIG_NEW}

    # we now have a solid configuration file, now initialize the database, and upload this to the database
    if [[ -f ${CONFIG_DBASE} ]]
    then
        echo "Removing old database file ${CONFIG_DBASE}"
        rm ${CONFIG_DBASE}
    fi
    echo "Uploading configuration to a fresh database"
    nodeorc upload-config ${CONFIG_NEW}
    # deactivate python environment
    deactivate
}

setup_service_files(){
    echo "Preparing nodeorc.service file for user ${USER}"
    cat > nodeorc.service <<EOF
[Unit]
Description=NodeOpenRiverCam operational edge or cloud compute instance
After=network.target

[Service]
# User=${USER}
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

logo() {

    echo '
                              ++++++++++++++++   *********************                                 %%%%%%%%                          %%%%%%%@
                         +++++++************+++++++  *****************  %%%%%                     %%%%%%%%%%%%%%%%%                  %%%%%%%%%%%%%%%%@               %%%%%%%              %%%%%
                     +++++************************+++++ **************  %%%%%                   %%%%%%%%%%%%%%%%%%%%%@             %%%%%%%%%%%%%%%%%%%%%            %%%%%%%%              %%%%%
                   ++++******************************++++ ************  %%%%%                  %%%%%%%%       @%%%%%%%%          %%%%%%%%@       %%%%%%%            %%%%%%%%%             %%%%%
                 +++************+-::-+******************++++**********  %%%%%                %%%%%%%@            @%%%%%%        %%%%%%%             %%%            %%%%%@%%%%%            %%%%%
               +++***********=::::::::::=*****************++++********  %%%%%               @%%%%%%                %%%%%%      %%%%%%@                            %%%%%% %%%%%            %%%%%
             +++************::::::::::::::******************+++ ******  %%%%%               %%%%%%                 @%%%%%@    @%%%%%@                            @%%%%%  %%%%%%           %%%%%
            +++*******#%@@%***+-::::::::::-*******************+++*****  %%%%%               %%%%%@                  %%%%%%    %%%%%%                             %%%%%    %%%%%%          %%%%%
          %**%@@@@@@@@@@@@@@@@@@@@@@@@@%#*=********************+++****  %%%%%              @%%%%%                   @%%%%%    %%%%%%                            %%%%%%     %%%%%%         %%%%%
      @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@#*****************+++***  %%%%%              @%%%%%                   %%%%%%    %%%%%%                           %%%%%%      %%%%%%         %%%%%
    @@@@@@@@@@@@@@%#%%%%###%@=%@@@@*+%==#%@@@@@#################*+++**  %%%%%               %%%%%%                  %%%%%%    %%%%%%                           %%%%%%       %%%%%%        %%%%%
    @@  +++####@@@@@@@@@@@%@@%+#=-==-:-=*%%%%@@@@################*++*   %%%%%               %%%%%@                  %%%%%%    %%%%%%                          %%%%%%%%%%%%%%%%%%%%%       %%%%%
       +++#####%%%%@@##%@@@@@@#=::::::-*##########################+++   %%%%%               %%%%%%@                %%%%%%     @%%%%%%                        %%%%%%%%%%%%%%%%%%%%%%       %%%%%
       ++*#########%%@%%@@@%######################################*++   %%%%%                %%%%%%%              %%%%%%%      @%%%%%%                %     @%%%%%%%%%%%%%%%%%%%%%%%      %%%%%
       ++############%@@@@#################################%%######+++  %%%%%                 %%%%%%%@          %%%%%%%@        %%%%%%%%           %%%%%    %%%%%%             %%%%%@     %%%%%
       ++##############@@%###################%#######@%##%@@@@%####*++  %%%%%%%%%%%%%%%%%%     %%%%%%%%%%%%%%%%%%%%%%%           @%%%%%%%%%%%%%%%%%%%%%%   %%%%%%              %%%%%%@    %%%%%%%%%%%%%%%%%%
      +++%%%%%%%%%%%%%%%@%######%%%%%%%%%%%@@@@%%%%@@@@@@@@@@@@@%#*+++  %%%%%%%%%%%%%%%%%%       %%%%%%%%%%%%%%%%%%%@              @%%%%%%%%%%%%%%%%%%%@  @%%%%%                %%%%%%    %%%%%%%%%%%%%%%%%%
      +++***************@@***************#@@@@@@#*@@@@@@@@@@@@@@%**+++  %%%%%%%%%%%%%%%%%%         @%%%%%%%%%%%%%%                    %%%%%%%%%%%%%%@     %%%%%%                @%%%%%%   %%%%%%%%%%%%%%%%%%
       ++******%%#*****#@@**************#*@@@@@@#*%@@@@@@@@@@@@@@%*+++
       ++%@@%%%@@@%%%@@@@@%@@@@%%%%%%@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@+++
       ++#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@%++   %%%%%%%%%%%%@           %%%%%%%%%%%%%%% @%%%%%            %%%%%  %%%%@          @%%%%%%%%%%        %%%%%%%%%%%%%%      %%%%%%%%%%%
       +++@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@+++   %%%%%%%%%%%%%%%%        @%%%%%%%%%%%%%%  @%%%%           %%%%%   %%%%@       %%%%%%%%%%%%%%%%%     %%%%%%%%%%%%%%    %%%%%%%%%%%%%%
        ++*%@%@%@%@%@%@@%@@%%@@%@@%@%%%%@@%%%%%@@@@@%@%@%@%%@@%%@#++ *  %%%%@@@@%@%%%%%%%%      @%%%%@@@@@@@@@@   %%%%%         %%%%%    %%%%@      %%%%%%%%    @%%%%%     %%%%%@@@@@@@@@    %%%%%     @%%
         ++#%%%%%%%%%%%%%#%%%%%%%%%%###%%%%%%%%%%#%%%%%%%%%%%%%%#+++**  %%%%         @%%%%%     @%%%%              %%%%@        %%%%%    %%%%@     %%%%%            %%     %%%%              %%%%
          ++##%%#%#%#%#%##%##%%#%%#%%%%%%%%%#######%%%#%#%##%%%#+++***  %%%%           %%%%%    @%%%%              %%%%%       %%%%%     %%%%@    %%%%%                    %%%%              %%%%%
           ++*#*##########+#####*##########*####**+###*###**###+++ ***  %%%%           %%%%%@   @%%%%               %%%%%     %%%%%      %%%%@    %%%%@                    %%%%              @%%%%%%%
            ++*#=##+#+#*##*#**#*+#*#*####*#*##**+=*###+#*#++**+++*****  %%%%            %%%%%   @%%%%%%%%%%%%%       %%%%@    %%%%@      %%%%@   @%%%%@                    %%%%%%%%%%%%%%      %%%%%%%%%%
             +++*+*#****#**#**#*+#+#****#+#*##*=+#####**=*+++++ ******  %%%%            %%%%@   @%%%%%%%%%%%%%       %%%%%   %%%%%       %%%%@   @%%%%%                    %%%%%%%%%%%%%%         @%%%%%%%%
               ++++#+***#**#*+#*+#=#+++*#**+*#=+**++++++*#++++********  %%%%           @%%%%    @%%%%                 %%%%%  %%%%        %%%%@    %%%%@                    %%%%                      @%%%%%%
                ++++***+#**#*+#++#######################++++ *********  %%%%           %%%%%    @%%%%                  %%%%@%%%%%        %%%%@    %%%%%                    %%%%                        @%%%%
                   +++++#**#*+=+#=##*******##########*++++ ***********  %%%%         %%%%%%     @%%%%                   %%%%%%%%         %%%%@     %%%%%%           %%     %%%%                         %%%%
                     +++++**+*#+*+*#+==++++++++***+++++ **************  %%%%%%%%%%%%%%%%%%      @%%%%%%%%%%%%%@         %%%%%%%          %%%%@      %%%%%%%%    @%%%%%     %%%%@%%%%%%%%%    %%%%     %%%%%%
                         ++++++++#+#+++++**++++++++  *****************  %%%%%%%%%%%%%%%@        @%%%%%%%%%%%%%%          %%%%%           %%%%@        %%%%%%%%%%%%%%%%     %%%%%%%%%%%%%%   @%%%%%%%%%%%%%@
                              ++++++++++++++++   *********************  %%%%%%%%%%%             %%%%%%%%%%%%%%@          %%%%@           %%%%%           %%%%%%%%%%        %%%%%%%%%%%%%%      @%%%%%%%%


    '


}
logo "$@"

main "$@"
exit 0
