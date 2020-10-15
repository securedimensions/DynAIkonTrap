# DynAIkonTrap
*An AI-enabled camera trap design targeted at the Raspberry Pi platform.*

DynAIkonTrap makes use of a continuous stream from a camera attached to the Raspberry Pi, analysing only the stream to detect animals. Animal detections can be used to save or send individual frames from the video, or even whole video segments. The beauty of this is that the system does not rely on any secondary sensors like PIR sensors and acts on exactly what the camera sees.

## Useful Resources
- [Getting Started](#getting-started)
    - A quick-start guide that you can use to check everything works
- [Tuning the System](#tuning-the-system)
- [Wiki](https://gitlab.dynaikon.com/c4c/dynaikontrap/-/wikis/)
    - Full documentation

## Getting Started
Once you have a Raspberry Pi with a camera set up, just run the setup script:

```sh
# Installs all required libraries into a Python virtual environment.
./setup.sh
```

Then you can start the camera trap program by running:

```sh
# Activates the virtual environment
source ./venv/bin/activate
# and starts the program
python -m DynAIkonTrap
```

## Tuning the System
The system has many parameters that can be tuned to be optimal for any given deployment.
These settings are saved in a `settings.json` file using the JSON format. It is recommended to use the included tuning script to set these. Run this with:

```sh
source ./venv/bin/activate
python tuner.py
```

## Further Information
If you are interested in more detailed information, have a look at the project's wiki page.

## Room for Improvement
As with any project there is always room for improvement. Below a few areas of particular interest for further development of the project have been identified:
- Motion queue prioritisation approach
    - At the moment this is done based on the largest SoTV, but there are probably better approaches
