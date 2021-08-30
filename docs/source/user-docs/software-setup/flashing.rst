Flashing the SD Card
====================

We will now "flash" the SD card. This is the process of installing the operating system.

We recommend using the official RPi imaging tool for this, which can be downloaded `here <https://www.raspberrypi.org/software/>`_. If you usually use a different tool to flash SD cards, feel free to use that instead. We recommend a "headless" setup for the camera trap.

.. admonition:: What is a headless setup?
   :class: hint

   Using a headless setup means you will not attach a keyboard or monitor directly to your RPi. That may sound scary, but don't worry! It's no more complicated than the full installation you would do to use a mouse and keyboard on the RPi. In fact many people would argue that using your RPi this way is easier. The idea is that you don't need to have your RPi in front of you to use it.

   We will use a tool called SSH to connect to your RPi from your main computer e.g. a desktop or laptop PC.


#. Insert the SD card into your computer
#. Start the RPi imaging tool
#. We recommend selecting "Raspberry Pi OS Lite" as the operating system
#. Click "Choose SD card" and select the card
#. Click "Write" and wait until a completion message appears

If you would like to connect to your RPi remotely via Wi-Fi, there is one more step to do. We recommend doing this.

.. admonition:: Wi-Fi and SSH Setup
   :class: hint, dropdown

   You need to enter your router's name and password so the RPi can connect to the network. First remove and reinsert the SD card into your computer. You should then look for a "boot" device that appeared in your file browser. Open this up. Next, create a new file with the name ``wpa_supplicant.conf`` and paste the following contents inside:

   .. code::

      ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
      update_config=1
      country=GB
      
      network={
         ssid="<name>"
         psk="<password>"
      }

   Make sure you replace ``<name>`` and ``<password>`` with your router's name and password. Also make sure you keep the double quotes around these. The country should be changed from ``GB`` to your country's `ISO 3166-1 alpha-2 code <https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2#Officially_assigned_code_elements>`_.

   To enable :program:`ssh`, which we will use to remotely log in to the RPi, create an empty file called "ssh" on the "boot" device. This is the same place you saved the Wi-Fi configuration above.

   Finally close and save the file and eject the SD card. Before ejecting make sure you've clicked "eject" in your file browser.

Congratulations! You now have everything set up and ready to go. Head over to the :doc:`manual-installation` page for the next steps.
