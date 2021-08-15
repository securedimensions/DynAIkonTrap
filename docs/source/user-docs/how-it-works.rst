How it Works
============

The basic premise of this project is that a continuous stream of camera :abbr:`frame (a single snapshot in time from the camera video stream, consisting of motion vectors and an image)`\s is passed through a pipeline to :abbr:`filter (a system to remove unwanted parts of data (can be in time or frequency domain))` out empty images and only allow animal images through. This filtering pipeline is the centrepiece of the project. This document is a short overview of the architecture so you can gain a fairly good understanding of the concepts used. 

The Pipeline
------------

This pipeline represents a software architecture. The core of the pipeline is a series of filter stages placed after the camera stage that acts as the input to the system. The output of the filters goes to the output node of the system, which combines frames with corresponding sensor readings if they exist. The output is configured to either produce still images or video sequences of animal motion events. This can be stored on the local disk or sent to a server via an HTTP request.

You may ask why such a multi-stage filtering approach is needed (why not just use the animal detector) and that is a completely valid question. The main reason is one of performance. Remember that this software is intended for deployment on a Raspberry Pi, a device with limited computational resources. Whilst desktop PCs might be able to process images at 30FPS with Tiny YOLO, the Raspberry Pi can only handle around one frame every two seconds. By using a different faster filter before this, the animal detector does not need to run permanently and has time to work through a queue of potential animal frames.

Movement Filter
---------------

The first filter is a movement filter. This only allows frames with motion that exceeds a threshold to be passed on to the next filtering stage. To get the frame's motion the motion vectors from the H.264-encoded camera stream are used. Taking advantage of this means the calculations for determining motion are performed externally to the processor, leaving more resources available for the rest of the system.

A method we are calling the Sum of Vectors (SoV) is applied to the motion vectors to obtain a single value that characterises the frame's motion. The SoV is calculated by summing all vectors -- as vectors not just their magnitudes -- to give a value that implicitly takes the following into account:

* Visible area of motion
* Speed of motion
* Coherence of motion (random motion sums to zero)

A further feature of the frames exists, which is that they are temporally related; a frame and its successor will only differ [#f1]_ if motion occurred. To take advantage of this, the SoTV is passed through an `IIR <https://en.wikipedia.org/wiki/Infinite_impulse_response>`_ frequency filter to smooth the output. It is reasonable to assume that motion will vary smoothly in time. This smoothing is applied to the SoTV as a vector, so in fact there are two filters: one for the horizontal and one for the vertical component.

Another threshold is applied to this smoothed SoTV to determine if sufficient motion occurred in the frame. If not, the frame is discarded and the next one analysed. If there is sufficient motion, the frame is passed to the next filtering stage. As many frames will not contain any movement, on average the rate at which this stage outputs frames is much lower than the framerate at which the camera records.

.. [#f1] Assuming the camera is stationary and lighting is constant from one frame to the next

Animal Filter
-------------

At the core of the animal filtering stage lies an animal detector. In this case it is a `Tiny YOLOv4 <https://github.com/AlexeyAB/darknet>`_ model trained on the `WCS <http://lila.science/datasets/wcscameratraps>`_ dataset. To determine if a frame contains an animal, this detector can be run on that frame and a number of predictions are made. The confidence in the highest prediction of "animal" for that image is compared to a predefined threshold and if exceeded means the frame is deemed to contain an animal.

That is quite a simple process, but it is made more complicated by the fact that YOLO does not consistently provide high-confidence predictions. This problem can be addressed by once again taking advantage of a few facts:

* The animal filtering does not need to happen in real-time -- there is no hard deadline for completion of processing
* Frames are temporally related
* Animals take time to move so they will usually be present in multiple frames

Naïvely one might consider applying the IIR smoothing approach use for the motion filter, but that is not appropriate here for two reasons: first, the animal detector predictions are very sporadic and form anything but continuous data. Second, the IIR approach is causal, meaning it cannot look forward in time. As the animal filtering stage does not have real-time requirements we can buffer data, meaning knowledge of the future and past will exist from a given frame's perspective. This buffering is done via the :class:`DynAIkonTrap.filtering.motion_queue.MotionQueue`.

Motion Queue
^^^^^^^^^^^^

The motion queue is a buffer where frames in which motion occurred, as determined by the motion filter, are queued. To be more exact the queue actually contains sequences of motion. Each sequence consists of all the frames from the start of motion to when that period of motion stops. Once the complete motion sequence is buffered the animal detector is passed over it. To ensure that motion sequences cannot go on for ever, a maximum time period for a sequence can be defined by the user. This also ensures other parts of the filtering pipeline are not idle for too long waiting for a sequence to process.

Smoothing
^^^^^^^^^

It is possible to calculate the expected number of frames an animal will be in, based on various criteria including the expected speed and size of the animal, and camera specifications like focal length and sensor dimensions. For a given animal prediction it is therefore expected that the animal could be present in up to this many frames either side of a predicted animal occurrence. As such all of these frames are also declared to contain an animal, effectively smoothing predictions in time. This has the benefit of improving the `recall <https://en.wikipedia.org/wiki/Precision_and_recall>`_ for the system. Once a frame has been labelled as animal or empty it does not need to be looked at again and so it is possible that the animal detector only needs to be run for a few frames in a motion sequence. The side effect here is that the average framerate is thereby improved as well. By applying this smoothing methodology performance in terms of frame filtering quality and speed are improved.

Sensor
------

The software caters for the usage of a USB sensor board, a prototype for which has already been designed by DynAikon. This part of the architecture can be easily modified to read data from any sensor, including one attached via the Raspberry Pi's GPIO pins. Sensor values are recorded at a regular interval and stored. The sensor readings are deleted once it is known that no corresponding frame has been recorded for a sensor reading.

Output
------

The output of the system combines a frame with its sensor readings, if they exist. The final output can then be either written to the local disk or sent via an HTTP request to a server. A simple REST API has been devised for this purpose. The animal data can be stored/sent as either still images or videos consisting of motion sequences.

Closing Remarks
---------------

This page gives a very brief insight into the architecture design, but you may have more questions. If that is the case please do get in touch and we'd love to discuss and explain things further.
