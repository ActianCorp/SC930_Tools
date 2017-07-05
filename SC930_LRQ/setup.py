__author__ = 'Paul Mason'

# Copyright 2017 Actian Corporation
import sys
from cx_Freeze import setup, Executable

base = None
if sys.platform == 'win32':
   base = 'Win32GUI'

options = {
    'build_exe': {
        "include_msvcr": True
    },
    # the upgrade-code ensures newer versions update over older ones rather than creating new copies in Control Panel
    'bdist_msi' : {
        'upgrade_code' : '{AA28BF7F-EA75-4324-A5E8-CC5B72F3E5E6}'
    }
}

# the two executables are the console version of the app (which can still launch the GUI if no args are given)
# and the GUI.
# see comments in SC930_LRQ_gui.py for more
executables = [
    # Console app
    Executable('SC930_LRQ.py', base=None),
    # windows app
    Executable('SC930_LRQ_gui.py', base=base, shortcutName='SC930_LRQ',shortcutDir='DesktopFolder')
]

# get version and URL strings from SC930_LRQ.py
# scanning the source file means not having to have a module just for constants
prog_vers = '0.0'
prog_url = 'http://code.ingres.com/samples/python/SC930_LRQ/'
try:
    fh = open('SC930_LRQ.py')
    for line in fh.readlines():
        check = line[:13]
        if check == 'SC930_LRQ_VER':
            prog_vers = line.split("'")[1]
        if check == 'SC930_LRQ_LNK':
            prog_url = line.split("'")[1]
    fh.close()
except:
    pass

setup(name='SC930_LRQ',
      version=prog_vers,
      description="SC930 Long-Running Query Finder",
      author='Actian Corporation',
      url=prog_url,
      options=options,
      executables=executables
      )
