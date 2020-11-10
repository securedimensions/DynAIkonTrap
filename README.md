# DynAIkonTrap
*An AI-enabled camera trap design targeted at the Raspberry Pi platform.*

DynAIkonTrap makes use of a continuous stream from a camera attached to the Raspberry Pi, analysing only the stream to detect animals. Animal detections can be used to save or send individual frames from the video, or even whole video segments. The beauty of this is that the system does not rely on any secondary sensors like PIR sensors and acts on exactly what the camera sees.

## Useful Resources
- [Getting Started](#getting-started)
    - A quick-start guide that you can use to check everything works
- [Tuning the System](#tuning-the-system)
- [Evaluation](#evaluation)
- [Wiki](https://gitlab.dynaikon.com/c4c/dynaikontrap/-/wikis/)
- [Source code documentation](docs/html)
    - You will need to view these files via your browser after downloading
    - GitLab does not actually render the HTML pages

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

Be sure to check out the wiki for more information on deploying the system, including advice on power supplies and case designs.

## Tuning the System
The system has many parameters that can be tuned to be optimal for any given deployment.
These settings are saved in a `settings.json` file using the JSON format. It is recommended to use the included tuning script to set these. Run this with:

```sh
source ./venv/bin/activate
python tuner.py
```

## Evaluation
The software is accompanied by some evaluation tools to make it easier for you to see how tweaking the settings can affect system performance. You can follow the recommended approach for generating test data sequences with your Raspberry Pi, or convert existing videos to test data if you are feeling adventurous.

By following these steps you will generate sequences of frames (consisting of images and motion vectors), generate your own truth by deciding if each of the frames contains an animal, and then run this through the filtering pipeline at the heart of the camera trap.

### 1. Record test data
On your Raspberry Pi, run the data generation program using (remember to activate the virtual environment):
```sh
python evaluate/generate_data.py
```

This records video data and generates an output file, `data.pk`. You can then copy this to another machine (via `scp`, USB, email, etc.), or continue the evaluation on the Raspberry Pi. You can rename the file if you would like it to be called something more descriptive. This is a good idea (and necessary) if you have multiple of these test sequences.

<details>
<summary>How to use an existing video, instead of recording my own? (click to expand)</summary>


If you wish to use existing videos, rather than recording your own, you can do this using tools like [MV-Tractus](https://github.com/jishnujayakumar/MV-Tractus). This whole process can be a little awkward, so this has not been described here in detail. If you do create your own you need to provide the data and truth as follows:

- Recorded data
```python
{
    'framerate': <framerate>,
    'resolution': (<width>, <height>),
    'frames': [
        {
            'image': <JPEG_image_as_bytes>,
            'motion': <array_of_motion_vectors>
        },
        {
            'image': <JPEG_image_as_bytes>,
            'motion': <array_of_motion_vectors>
        },
        ...
    ]
}
```
- Your generated truth
    - A list of Booleans indicating whether each frame in the frames returned by `data()` contains an animal (`True`), or not (`False`).

</details>

### 2. Generate the truth
Next, you will need to provide information on what the truth is in the video. For this run the truth generator:
```sh
python evaluate/generate_truth.py data.pk
```

This doesn't need to be done on the Raspberry Pi and in fact requires a display, which you may not have set up for your Raspberry Pi. You will be asked to label each frame in the video to indicate if the frame contains an animal or not. You can go forwards (using the `.` key), backwards (`,`), and toggle the current frame's label (using the enter key). A shortcut exists to toggle the current frame's label and proceed to the next (space bar). Once you are done hit the `q` key to complete the process. The truth you have just generated will then be saved in a new file e.g. `data.truth.pk`.

### 3. Running the evaluation
To start the evaluation simply run (remember to activate any virtual environment):
```sh
python evaluate/evaluate.py <path/to/data> <path/to/truth>
```

It is recommended that you run this on a desktop rather than the Raspberry Pi, as you will have your results a lot faster. It should, however, still work on the Raspberry Pi.

You will eventually see a table of results, e.g.:

| Metric            | Score / % |
|-------------------|-----------|
| alpha = 0 (TPR)   |     93.02 |
| alpha = 0,1       |     93.29 |
| alpha = 0,5       |     94.40 |
| alpha = 0,9       |     95.52 |
| alpha = 1 (TNR)   |     95.81 |
| Precision         |     85.11 |

The scoring is the weighted harmonic mean of the true-positive and true-negative rates. The weighting is done via an alpha parameter, which is represented in the table. If you value a system that allows as many animal frames as possible through, look at alpha=0,1. If, on the other hand, you are more interested in filtering out all the empty frames focus on alpha=0,9. An ideal system performs well in both tasks and so you may also be interested in alpha=0,5 where both aspects are equally weighted.

A precision score is also given to indicate what percentage of the frames declared as containing an animal actually did, according to the ground truth.

For all of these results higher is better, with 100% being the maximum. A perfect system would have a result of 100% for alpha set in the exclusive interval (0...1).

## Further Information
If you are interested in more detailed information, have a look at the project's wiki page.

## Room for Improvement
As with any project there is always room for improvement. Below a few areas of particular interest for further development of the project have been identified:
- Motion queue prioritisation approach
    - At the moment this is done based on the largest SoTV, but there are probably better approaches
