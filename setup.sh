#!/bin/bash
man_help(){
    echo "========================================================================"
    echo "Setup of nodeorc operational service Linux"
    echo "========================================================================"
    echo ''
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
    echo '################################'
    echo 'INSTALLING DEPENDENCIES'
    echo '################################'
    if [[ `hostnamectl` =~ .*"CentOS".* ]];
    then
        echo "CentOS system detected, running yum"
	sudo yum -y update
	sudo yum install ffmpeg libsm6 libxext6 libgl1 python3-venv libgdal-dev -y
    elif [[ `hostnamectl` =~ .*"Ubuntu".* ]] || [[ `hostnamectl` =~ .*"pop-os".* ]] || [[ `hostnamectl` =~ .*"Mint".* ]] || [[ `hostnamectl` =~ .*"Debian".* ]];
    then
        echo "Ubuntu-like system detected, trying apt"
        sudo apt -y update
        sudo apt -y upgrade
        sudo apt install ffmpeg libsm6 libxext6 libgl1 python3-venv -y
    else
        echo "System unknown I can't help you with updating"
    fi
}


install_nodeorc () {
    echo '################################'
    echo 'INSTALLING NODEOPENRIVERCAM'
    echo '################################'
        pip3 install virtualenv
        python3 -m venv $HOME/venv/nodeorc
        # activate the new environment
        source $HOME/venv/nodeorc/bin/activate
        # install the current source code
        pip install .
}

install_service () {
    echo '################################'
    echo 'INSTALLING SYSTEMD SERVICE '
    echo '################################'
    echo ' '
    echo 'The name of your device must be unique and well recognizable in the LiveORC front-end. '
    DEVICE_NAME="$(hostname)"
    echo "The current name of your device is $DEVICE_NAME."
    read -p "Do you want to change this? [Y/n]" YN
    case $YN in
        [Yy]* ) read -e -p "Enter your new device name: " DEVICE_NAME; hostnamectl set-hostname $DEVICE_NAME;;
        * ) echo "No changes in device name made";;
    esac
    echo "Your device name is $DEVICE_NAME"
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

main "$@"
exit 0
