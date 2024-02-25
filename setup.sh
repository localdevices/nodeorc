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
    export SCRIPT_FOLDER=$PWD/$(dirname $0)
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
    echo 'NodeORC is detected and installed. Continue to install service ...'
    echo 'The name of your device must be unique and well recognizable in the LiveORC front-end. '
    DEVICE_NAME="$(hostname)"
    echo "The current name of your device is ${DEVICE_NAME}."
    read -p "Do you want to change this? [Y/n]" YN
    case $YN in
        [Yy]* ) read -e -p "Enter your new device name: " DEVICE_NAME; hostnamectl set-hostname $DEVICE_NAME;;
        * ) echo "No changes in device name made";;
    esac
    echo "Your device name is $DEVICE_NAME"

#    read -p "Provide an ip-address or remote hostname (without /api/) where your LiveOpenRiverCam is available: " URL
#    # remove trailing slah if any
#    if [ "${URL: -1}" == "/" ] ; then export URL=${URL:0:-1} ; fi
#    read -p "Provide your email login to ${URL}: " LOGIN
#    read -s -p "Provide your password to ${URL}: " PASSWD
    export URL="https://openrivercam.com"
    export LOGIN="winsemius@rainbowsensing.com"
    export PASSWD='^7JF!k93oqf$2EAl'
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
    export CONFIG_TEMPLATE="${SCRIPT_FOLDER}/settings/config.json"
    export CONFIG_NEW="${SCRIPT_FOLDER}/settings/config_device.json"
    jq ".callback_url.url=\"${URL}\" | .callback_url.token_refresh=\"${REFRESH}\" | .callback_url.token_access=\"${ACCESS}\"" ${CONFIG_TEMPLATE} > ${CONFIG_NEW}

    # we now have a solid configuration file, now initialize the database, and upload this to the database

    nodeorc upload-config ${CONFIG_NEW}
    # deactivate python environment
    deactivate
#    cat > nodeorc.service <<EOF
#[Unit]
#Description=NodeOpenRiverCam operational edge or cloud compute instance
#After=network.target
#
#[Service]
## User=${USER}
#WorkingDirectory=${PWD}
#Environment="PATH=${HOME}/venv/nodeorc/bin"
#ExecStart=${HOME}/venv/nodeorc/bin/nodeorc start --storage local --listen local
#Restart=always
#
#[Install]
#WantedBy=multi-user.target
#EOF
#
#echo 'moving systemd files to /etc/systemd/system'
#    sudo mv nodeorc.service /etc/systemd/system/
#    # ensuring credentials are set correctly
#    sudo chmod 644 /etc/systemd/system/nodeorc.service
#    echo 'starting and enabling the pyorc service with systemd'
#    sudo systemctl daemon-reload
#    sudo systemctl start nodeorc.service
#    sudo systemctl enable nodeorc.service
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
