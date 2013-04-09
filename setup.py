from distutils.core import setup
from glob import glob
import py2exe

py2exe_options = {
  "packages": ['wxPython', 'pyaudio', 'pymedia', 'eyed3', 'win32event', 'win32api', 'winerror'],
  "excludes": ['tcl'],
  "compressed": 1,
  "optimize": 2,
  "bundle_files": 3}

setup(
  options = {"py2exe": py2exe_options},
  data_files=[("auto", glob("auto\\*")), ("icon", glob("icon\\*")), ("", ["LICENSE.txt", "README.txt", "inspause.xrc", "myicon.ico", "libmad.dll"])],
  windows = [
    {"script" : "inspause.pyw", "icon_resources": [(0, "myicon.ico")]}],
  zipfile = "lib/library.zip")

