Installation
============

.. tip::
   
   If you are not familiar with SSH to log into the RPi, take a look at the :ref:`first-run` section first.

Install on RPi
--------------

Log in to the RPi and issue the following commands on the terminal.

Expand filesystem and enable camera
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To start you need to ensure the filesystem has been fully expanded. This ensures you are able to use the full size of the SD card. You can do this by running:

.. code:: sh

   sudo raspi-config

Then use the arrow keys to highlight "6 Advanced options" and hit enter. Then go to "A1 Expand filesystem" and hit enter. Back in the main menu, make sure the camera is enabled by going to "3 Interface Options" and select and enable "P1 Camera". Once you have selected this you can hit "Finish" by using the right arrow key and enter. Then reboot the RPi as requested.

Installation
^^^^^^^^^^^^

Make sure your Raspberry Pi is up-to-date:

.. code:: sh

   sudo apt update && sudo apt upgrade -y

Make sure ``git`` is installed by running:

.. code:: sh

   sudo apt install -y git

Then download the code with:

.. code:: sh

   git clone https://gitlab.dynaikon.com/dynaikontrap/dynaikontrap.git

Make sure you are on the latest stable version of DynAIkonTrap:

.. code:: sh

   (cd dynaikontrap && git checkout -q $(git tag --sort=taggerdate --list 'v[0-9]*' | tail -1))

Finally, run the setup script with:

.. code:: sh

   ./dynaikontrap/setup.sh

This may take a little time to complete, but once it is done you should be able to start the camera trap code by running ``dynaikontrap``.

Raspberry Pi settings
^^^^^^^^^^^^^^^^^^^^^

There are a few settings that need to be configured using ``sudo raspi-config``. These include enabling the camera and enabling Wi-Fi as required. You may also wish to change your hostname to ``dynaikontrap`` for compatibility with the remaining instructions, although it isn't essential.


Installation on Other Platforms (not Raspberry Pi)
--------------------------------------------------

.. important::

   You cannot run the full DynAIkonTrap on a non-RPi system out of the box. You can, however, use our `vid2frames <https://gitlab.dynaikon.com/dynaikontrap/vid2frames>`_ library or run the `evaluation script <https://gitlab.dynaikon.com/dynaikontrap/dynaikontrap#evaluation>`_.

If you are installing on another platform like your desktop or laptop you will need to run:

.. code:: sh

   export READTHEDOCS=True

before

.. code:: sh

   ./setup.sh

This instructs the installer to not install the full version of the PiCamera library as that only runs on the Raspberry Pi.


