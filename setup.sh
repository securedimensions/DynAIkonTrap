#! /bin/bash
# DynAIkonTrap is an AI-infused camera trapping software package.
# Copyright (C) 2020 Miklas Riechmann

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

echo "Installation starting. This may take a while, so please be patient."

DIR="$(cd "$(dirname "$0")" && pwd)"

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
    echo "  sudo apt install python3.7"
    exit
fi

## Install dependencies
sudo -p "[sudo] password to install dependencies> " apt install -y libaom0 libavcodec58 libavformat58 libavutil56 libcodec2-0.8.1 libilmbase23 libopenexr23 libswresample3 libswscale5 libx264-155 libx265-165

if [ $? -ne 0 ]
then
    echo "There was an error installing dependencies (see above)"
    echo "Are you sure your device is up-to-date, update with:"
    echo "  sudo apt update && sudo apt upgrade"
    echo ""
    read -r -p "This is fine on non-Raspberry Pi systems; continue? [Y/n] " input
 
    case $input in
        [yY][eE][sS]|[yY])
    ;;
        [nN][oO]|[nN])
    exit 1
        ;;
        *)
    echo "Invalid input"
    exit 1
    ;;
    esac
fi

sudo -p "[sudo] password to install dependencies> " apt install -y libatlas3-base libbluray2 libcairo2 libchromaprint1 libcroco3 libdatrie1 libdrm2 libfontconfig1 libgdk-pixbuf2.0-0 libgfortran5 libgme0 libgraphite2-3 libgsm1 libharfbuzz0b libjbig0 libmp3lame0 libmpg123-0 libogg0 libopenjp2-7 libopenmpt0 libopus0 libpango-1.0-0 libpangocairo-1.0-0 libpangoft2-1.0-0 libpixman-1-0 librsvg2-2 libshine3 libsnappy1v5 libsoxr0 libspeex1 libssh-gcrypt-4 libthai0 libtheora0 libtiff5 libtwolame0 libva-drm2 libva-x11-2 libva2 libvdpau1 libvorbis0a libvorbisenc2 libvorbisfile3 libvpx5 libwavpack1 libwebp6 libwebpmux3 libxcb-render0 libxcb-shm0 libxfixes3 libxrender1 libxvidcore4 libzvbi0

if [ $? -ne 0 ]
then
    echo "There was an error installing dependencies (see above)"
    echo "Are you sure your device is up-to-date, update with:"
    echo "  sudo apt update && sudo apt upgrade"
    exit
fi

## Ensure virtual environment package is installed
dpkg -s $python_command-venv > /dev/null 2>&1
if [ $? -ne 0 ]
then
    sudo -p "[sudo] password to install virtual environment> " apt install -y python3-venv $python_command-venv
fi

## Create the virtual environment and activate
(cd $DIR && $python_command -m venv venv && \
source ./venv/bin/activate && \
\
## Ensure pip is up-to-date
python -m pip install --upgrade pip && \
\
## Install the requiremnts
pip install -r requirements.txt)

## Create a "launcher" script that can also be called via `nohup`
echo "#! /bin/bash" > "$DIR/dynaikontrap.sh"
echo "(cd \"$DIR\" && source \"./venv/bin/activate\" && python -m DynAIkonTrap)" >> "$DIR/dynaikontrap.sh"
chmod +x "$DIR/dynaikontrap.sh"

## Place the script in /usr/local/bin/ so it be called from everywhere
sudo mv "$DIR/dynaikontrap.sh" /usr/local/bin/dynaikontrap

if [ $? -eq 0 ]
then
    echo ""
    echo "Setup complete!"
    echo "Start the camera trap with:"
    echo "  dynaikontrap"
else
    echo "There was a problem, check above for information"
    exit
fi
