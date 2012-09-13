from distutils.core import setup
from glob import glob
import py2exe

py2exe_options = {
  "packages": ['wxPython', 'pyaudio', 'win32api'],
  "compressed": 1,
  "optimize": 2,
  "bundle_files": 1}

setup(
  options = {"py2exe": py2exe_options},
  data_files=[("icon", glob("icon\\*")), ("", ["LICENSE.txt", "README.txt"])],
  windows = [
    {"script" : "inspause.pyw", "icon_resources": [(0, "myicon.ico")]}],
  zipfile = None)

