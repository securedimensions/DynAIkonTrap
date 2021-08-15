Building Documentation
======================

This page documents how to build the documentation. You can use these steps to check everything displays correctly locally before pushing changes.

#. Ensure you are in your virtual environment
#. Install dependencies (for docs **and** DynAIkonTrap project):

   .. code-block:: sh
    
       cd docs
       pip install -r requirements.txt && pip install -r ../requirements.txt

#. Build documentation:

   .. code-block:: sh

       make clean && make html

#. Navigate a browser to ``.../docs/build/html/index.html``

