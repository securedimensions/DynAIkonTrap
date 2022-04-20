Tuning
======

Now that everything is installed the system needs to be tuned for your use-case. This can be done by running the tuner:

.. code:: sh

   # Go into the dynaikontrap code directory
   cd dynaikontrap
   
   # Activates the virtual environment
   source ./venv/bin/activate
   
   # Start the tuner
   python tuner.py

You will be asked some questions to help determine the best parameters for the system to use. These settings are saved in a ``settings.json`` file, which is loaded when you start the actual camera trap program. Below is relevant information for each question in the tuning script:

.. admonition:: Framerate
   :class: note, dropdown

   Number of frames that are captured by the camera every second. Testing indicates this should not exceed 40 FPS on a Raspberry Pi 4B.

.. admonition:: Resolution
   :class: note, dropdown

   Dimensions of the captured image. This is specified using width and height in the tuning script. Take a look at the relevant `PiCamera documentation <https://picamera.readthedocs.io/en/release-1.13/fov.html#sensor-modes>`_ for information on valid width and height combinations for your camera model. Also check that the chosen resolution supports video mode at the desired framerate. Note that certain dimensions limit the field of view of the camera.

.. admonition:: Visible animal area to trigger
   :class: note, dropdown

   The expected visible area (on a plane parallel to the camera lens) of a subject animal, expressed in square-metres. This is used to determine what amount of motion will trigger the camera.

.. admonition:: Expected distance of animal from sensor
   :class: note, dropdown

   Roughly the distance you would expect your subject animal to be from the camera sensor. A sensible value here may be around a metre, although you are encouraged to try out different values.

.. admonition:: Animal trigger speed
   :class: note, dropdown

   The minimum speed, in metres per second, you would require your animal to travel at for motion to be triggered. Ensure this is not too low, so the animal detection stage is not overwhelmed with motion sequences. If you would like to set a low threshold make sure the background is not likely to experience movement, for example by pointing the camera at a wall rather than a bush.

.. admonition:: Camera focal length
   :class: note, dropdown

   Focal length, in **metres**, as stated by the manufacturer. You may find `this summary table <https://www.raspberrypi.org/documentation/hardware/camera/>`_ helpful.

.. admonition:: Pixel size
   :class: note, dropdown

   Pixel size, in **metres**, (single dimension) as stated by the manufacturer. You may find `this summary table <https://www.raspberrypi.org/documentation/hardware/camera/>`_ helpful.

.. admonition:: Number of pixels
   :class: note, dropdown

   Sensor resolution width as stated by the manufacturer. You may find `this summary table <https://www.raspberrypi.org/documentation/hardware/camera/>`_ helpful.

.. admonition:: SoTV small movement threshold
   :class: note, dropdown

   The initial threshold applied to all movement vectors independently. This should be a small value and is given in pixel dimensions.

.. admonition:: SoTV smoothing IIR order
   :class: note, dropdown

   Order for the IIR filter on the output of the SoTV motion filtering stage. Testing has shown that an order of 3 is appropriate to minimise delays whilst still achieving the desired smoothing effect.

.. admonition:: SoTV smoothing IIR stop-band attenuation
   :class: note, dropdown

   Amount by which the frequencies in the stop-band are to be attenuated by, in dB. These are the higher frequencies that are to be removed, leading to a smoother output. -35dB has been found to work well here.

.. admonition:: Animal confidence threshold
   :class: note, dropdown

   Confidence value to be exceeded for the animal detector to declare a frame as containing an animal.

.. admonition:: Maximum motion sequence period
   :class: note, dropdown

   Maximum length for a single motion sequence, in seconds. A new motion sequence is started if the current one exceed this limit.

.. admonition:: Sensor board port
   :class: note, dropdown

   Port to be used to communicate with the USB sensor board. This will usually be ``/dev/ttyUSB0``.

.. admonition:: Sensor board baud rate
   :class: note, dropdown

   Baud rate to be used to communicate with the USB sensor board.

.. admonition:: Sensor reading interval
   :class: note, dropdown

   Interval, in seconds, at which the sensor board is read.

.. admonition:: Output mode
   :class: note, dropdown

   Choose between saving to disk (``d``) or sending data to a server (``s``) via HTTP requests. If picking the latter you will need to configure a server to use the simple API.

.. admonition:: Output path
   :class: note, dropdown

   A location for all recordings to be saved to. Leaving this empty saves them in the DynAIkonTrap project directory.

.. admonition:: Server address
   :class: note, dropdown

   URI of the server to which captures are to be transmitted using the implemented API.

.. admonition:: Output format
   :class: note, dropdown

   Whether or not output is to be saved in video format. The alternative is to output still images.

.. admonition:: Device ID
   :class: note, dropdown

   An identifier to use for the camera trap. This is not used other than in output meta-data. This could be used to uniquely identify camera traps if multiple of these are in use.

.. admonition:: Logging level
   :class: note, dropdown

   Choose the minimum threshold for logging. Messages with a level below this will not be output. The recommended level is ``INFO`` as this provides informative, but not excessive, output.

