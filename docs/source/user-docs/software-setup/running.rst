Running
=======

.. seealso::

   Once you have tested that the code works we recommend you have a look at the :doc:`Tuning Guide <tuning>` to make sure the system is tuned to your needs.


.. _first-run:

First Run
---------

Before starting your RPi make sure you have plugged in your camera and inserted the flashed SD card (see our :doc:`Flashing Guide <flashing>` if you haven't done this yet.)

Now plug in your RPi. You should see some LEDs come on and flash, indicating the RPi is booting up. The booting should take no more than a minute.

Now you will need to connect to your RPi by using ``ssh`` from the terminal. This command is generally available on Linux and Mac computers. Windows machines running Windows 10 with at least the October 2018 update also have ``ssh`` pre-installed. If you have an older version of Windows you will need to follow the official RPi guide available `here <https://www.raspberrypi.org/documentation/remote-access/ssh/windows.md>`_.

#. Open a terminal (Powershell on Windows)
#. Start an SSH connection

   .. code:: sh
   
      ssh pi@dynaikontrap.local

   Or if that doesn't work you will need to find out the RPi IP address (see `here <https://www.raspberrypi.org/documentation/remote-access/ip-address.md>`_ for more information). Enter the IP address like this:

   .. code:: sh

      ssh pi@192.168.1.123

#. You will be asked for a password. Enter "raspberry" as the password. You should change this at some point to improve security using ``passwd`` on the RPi.
#. If everything worked you'll see some text followed by:

   .. code:: sh

      pi@dynaikontrap:~ $ 

   This is the terminal on the RPi. You can interact with the RPi by issuing commands here.

#. Once the :doc:`software is set up <manual-installation>` you can start the camera trap code to make sure everything is working by typing the following on the terminal:

   .. code:: sh

      dynaikontrap

   After a few moments you should see the output from the camera trap software appearing. If you wave your hand in front of the camera you should begin to see messages about detected movement appearing.

#. To quit the program hit :kbd:`Ctrl+C`.

If you have reached this point, then well done! You have successfully set up the camera trap.

The remaining sections on this page have some useful recommendations on how to best use this camera trap, but if you are not very comfortable using a RPi yet you may want to stop here. Either way we do recommend that you have a look at the :doc:`tuning` guide before deploying the camera trap properly to make sure your system is fully optimised for your use-case.


Long-term Running
-----------------

If you start the code using the ``dynaikontrap`` command, the program will stop as soon as you log out of the RPi. This is not very useful as you will likely not want to keep the terminal connection open for days or weeks on end. A simple solution is to use the ``screen`` command.

Starting
^^^^^^^^

Issue the following commands:

.. code:: sh

   # Start a new screen session called "dynaikontrap"
   screen -S dynaikontrap

   # Start the camera trap within the screen session
   dynaikontrap

You can now leave :program:`screen` without stopping the camera trap code by hitting :kbd:`Ctrl+A`, and then the :kbd:`D` key to "detach" from the session. Now if you close the terminal/log out from the RPi (:kbd:`Ctrl+D` or ``logout``), the camera trap will continue to run.

Checking progress
^^^^^^^^^^^^^^^^^

You may want to check up on your camera trap's progress. This is easily done by starting an ``ssh`` session to the RPi. You can then reattach to the ``screen`` session using:

.. code:: sh

   screen -r dynaikontrap

You will be able to see any logs produced by the DynAIkonTrap.

Stopping
^^^^^^^^

Reattach to the ``screen`` session as mentioned above for `Checking progress`_. Once in the ``dynaikontrap`` session use :kbd:`Ctrl+C` to quit the DynAIkonTrap code.

It is also safe to simply shutdown the RPi by running:

.. code:: sh

   sudo shutdown -h 0

This means using superuser privileges (``sudo``) shutdown (``shutdown``) now (``-h 0``). The camera trap code will **not** automatically start again when the RPi is powered on. Remember to unplug the RPi once it is shut down as it will continue to use a very slight amount of energy if left plugged in.

Remote File Saving
------------------

The most important question you might have is "how do I see my animal pictures?" and that is a fair question. The absolute simplest option for a novice RPi user may be to plug the SD card into their computer and access the video files in ``/home/pi/dynaikontrap`` or similar. This is not the recommended approach, though.

A still very simple approach might be to use SCP to copy files via SSH:

.. code:: sh

   scp pi@dynaikontrap.local:~/dynaikontrap/*.mp4 ./

copies all mp4 files from the default video output directory onto the current directory on your computer.

Automatic
^^^^^^^^^

A slightly more complicated solution that allows automatic saving of files to a separate device is as follows. If you have a second RPi you could use this as a server. Let's state some assumptions:

* The camera trap is called ``dynaikontrap``
* The output directory has been set to ``~/videos``
* The second computer (could be a second RPi) is called ``server``

On ``dynaikontrap`` you could then run:

.. code:: sh

   sshfs ~/videos pi@server.local:~

to automatically save all files from ``dynaikontrap``'s output to the ``server``'s home directory. Note that ``sshfs`` may not be installed, but you can install this with ``sudo apt install sshfs`` on Ubuntu/Debian systems. In this configuration the files are actually saved physically to ``server``, so you could have a more reliable hard disk drive on this device and serve the files to other devices connected on the local network.

Server
^^^^^^

The camera trap does have a RESTful server API, but code for the server is not released. This is left as an exercise for the reader. Using frameworks like Django can make this a fairly simple process. We do not have the resources to write and maintain the necessary code for this, but we would be happy to answer questions you may have and hopefully help you set something up.

