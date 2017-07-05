__author__ = 'Paul Mason'

# Copyright 2017 Actian Corporation
#
#
# what's this trivial file for?
# it's all Windows fault!
#
# On windows, when we create a compiled version we can either make it a
# console app or a windows app.
# A windows app has no console to write to - print messages will fail
# A console app can still launch the tk GUI but if you set a shortcut
# to launch the app then it will open a console window behind the GUI
# which looks bad

# so I decided we'd have two exe's on Windows - one windows and one cli
# but distutils doesn't seem to be able to create two exes based on one
# source file - hence this

# so this will become SC930_LRQ_gui - a windows app, with a shortcut in the installer
# SC930_LRQ will be a console app
import SC930_LRQ

SC930_LRQ.gui_main()

