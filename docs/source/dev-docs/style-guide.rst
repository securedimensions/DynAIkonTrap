Style Guide
===========

This page is concerned with the coding style to be adopted in writing code for the DynAIkonTrap.

Documentation
-------------

The package documentation is automatically built using Sphinx and so following this guidance will ensure documentation is properly displayed.

#. Docstrings should be used wherever possible to explain what a module/class/function/etc. does and how to use it. We use the Google docstring format as much as possible.

#. Use Restructured Text formatting where needed over Markdown for better compatibility with Sphinx

#. In addition to docstrings, the use of type hints is strongly encouraged.

#. Docstrings should follow the format:
    .. code:: py

        def square(x: float) -> float:
            """Multiply a number by itself

            Args:
                x (float): Number to be squared

            Returns:
                float: Squared input
            
            """

#. Document changes in :file:`CHANGELOG.md` under a heading for the release version. Commits that do not yet relate to a release should be added to the persistant ``[Unreleased]`` heading until they become part of a release.

Code/Structure/Linting
----------------------

#. To ensure consistent structure of code throughout the project we use the `black <https://pypi.org/project/black/>`_ code formatter with the ``-S`` flag.
   
#. Generally single-quoted strings (``'string'`` vs. ``"string"``) are used.

#. Each code file should start with a license statment:

   .. code:: py

      # DynAIkonTrap is an AI-infused camera trapping software package.
      # Copyright (C) <year> <author name>
      
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

#. Where practical, unit tests should be written and run before merging new code.


