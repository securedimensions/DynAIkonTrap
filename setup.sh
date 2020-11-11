#! /bin/bash

## Start by checking the necessary Python version exists
possible_pythons=$(find /usr/bin/python* -maxdepth 1 -type f -printf "%f\n")

python_command=0
for possible_python in $possible_pythons; do
    major=$(echo $possible_python | awk -F. '/python[0-9]*\.[0-9]*$/ {print $1}')
    minor=$(echo $possible_python | awk -F. '/python[0-9]*\.[0-9]*$/ {print $2}')

    if [ "$major" == "python3" ]
    then
        if [ $minor -ge 7 ]
        then
            python_command="$major.$minor"
            break
        fi
    fi
done

if [ $python_command == 0 ]
then
    echo "Need python >= 3.7; install with:"
    echo "  apt install python3.7"
    exit -1
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
