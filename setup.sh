#! /bin/bash

## Start by checking the necessary Python version exists
check_version() {
    version=$($1 --version | awk '{print $2}')
    minor=$(echo $version | awk -F. 'OFS="." {print $2}')
    if [ $minor -lt 7 ]
    then
        echo 0
    else
        echo 1
    fi
}

python_command="python3"

if [ $(check_version "python3") == 0 ]
then
    if [ $(check_version "python3.7") == 0 ]
    then
        echo "Need python>=3.7"
        exit -1
    else
        python_command="python3.7"
    fi
fi

## Create the virtual environment and activate
$python_command -m venv venv
source ./venv/bin/activate

## Install the requiremnts
pip install -r requirements.txt

if [ $? -eq 0 ]
then
    echo "Setup complete!"
else
    echo "There was a problem, check above for information"
    exit -1
fi
