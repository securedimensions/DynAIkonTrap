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
from argparse import ArgumentParser
from pickle import load, dump
from typing import List
import numpy as np
import cv2


def generate_truth(frames, i=0):
    global truth

    image = frames[i]['image']
    image = cv2.imdecode(np.asarray(image), cv2.IMREAD_COLOR)

    cv2.putText(
        image,
        'Frame {}'.format(i),
        (5, image.shape[0] - 5),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (255, 0, 0),
    )

    cv2.putText(
        image,
        'Animal: {}'.format('Y' if truth[i] else 'N'),
        (5, 25),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (255, 0, 0),
    )

    cv2.imshow("preview", image)
    key = cv2.waitKey()
    if key == ord('q'):
        return
    elif key == 13:  # Toggle current
        truth[i] = truth[i] ^ True
        generate_truth(frames, i)
    elif key == ord(' '):  # Toggle current and proceed to next
        truth[i] = truth[i] ^ True
        generate_truth(frames, min(i + 1, len(frames) - 1))
    elif key == ord('.'):  # Proceed to next
        generate_truth(frames, min(i + 1, len(frames) - 1))
    elif key == ord(','):  # Back to previous
        generate_truth(frames, max(i - 1, 0))
    else:
        generate_truth(frames, i)


parser = ArgumentParser(
    description='Generate the ground truth for a given recording. Use the `,` and `.` keys to navigate backwards and forwards in time. Use the enter/return key toggle the label for the current frame. Use the space key to toggle the current frame and proceed to the next -- a shortcut for `<enter>+.`. You can hold down keys to move through multiple frames at speed, so you can hold the space bar during animal seqeunces to label the sequence as containing an animal and keep going. Use the `q` key to quit when you are done.NOTE: this tool overwrites any previous truth you have generated.'
)
parser.add_argument(
    'filename',
    metavar='FILENAME',
    help='Name of file with recorded test data',
)
args = parser.parse_args()


with open(args.filename, 'rb') as f:
    data = load(f)

frames = data['frames']
truth = [False for i in frames]

generate_truth(frames)

name = '.'.join(args.filename.split('.')[:-1])
with open('{}.truth.pk'.format(name), 'wb') as f:
    dump(truth, f)

print('Truth saved to `{}.truth.pk`'.format(name))
