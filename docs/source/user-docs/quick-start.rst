Quick Start
===========

These instructions will help you get up and running quickly so you can try out DynAIkonTrap. We recommend following the full instructions in the :doc:`../user-docs`, but you can use this page to get the system running with defaults quickly.

#. Connect the camera to your Raspberry Pi and enable it in settings (``sudo raspi-config``)
    - If you are on a newly setup Raspberry Pi it's worth updating before proceeding:
        
      .. code:: sh

         sudo apt update && sudo apt upgrade -y
        
    - You may also need to install git:
      
      .. code:: sh
      
        sudo apt install git -y
        
#. Download the code e.g.
    
   .. code:: sh
      
      # Download
      git clone http://gitlab.dynaikon.com/dynaikontrap/dynaikontrap.git
      # Enter the directory
      cd dynaikontrap
    
#. Run the setup script

   .. code:: sh
      
      # Installs all required libraries into a Python virtual environment.
      ./setup.sh

#. Start the camera trap program by running:
   
   .. code:: sh
    
      dynaikontrap
