#!/usr/bin/env python
# -*- coding: utf-8 -*-

from distutils.core import setup
from glob import glob
import sys

import inspause
from distall import DistAllCommand


def main():
    options = get_options()
    setup(**options)


def get_options():
    options = {
        'name': 'inspause',
        'version': inspause.__version__,
        'packages': '.',
        'description': 'insert pause into sound file',
        'long_description': 'insert pause into sound file',
        'author': inspause.__author__,
        'author_email': 'i@vanya.jp.net',
        'license': 'GPL',
        'url': 'http://vanya.jp.net/eng/inspause/',
        'requires': ['wxPython', 'pyaudio'],
        'cmdclass': { 'all': DistAllCommand }
    }

    if sys.platform == 'win32':
        if len(sys.argv) >= 2 and sys.argv[1] == 'py2exe':
            add_py2exe_options(options)

    return options


def add_py2exe_options(options):
    try:
        import py2exe
    except ImportError:
        print 'Could not import py2exe.   Windows exe could not be built.'
        sys.exit(0)

    py2exe_options = {
        'packages': ['wxPython', 'pyaudio', 'win32event', 'win32api',
                     'win32com', 'winerror'],
        'excludes': ['tcl', 'numpy', 'scipy'],
        'compressed': 1,
        'optimize': 2,
        'bundle_files': 3,
        'dist_dir': 'dist/inspausew-%s' % inspause.__version__,
    }

    manifest = get_manifest()

    files = ['gui.xrc', 'icon.ico', 'README.md', 'CHANGES.md', 'LICENSE.txt']
    options['data_files'] = [('backup', glob('backup\\*.zip')),
                             ('icon', glob('icon\\*.png')),
                             ('', files)]
    options['options'] = { 'py2exe': py2exe_options }
    options['zipfile'] = 'lib/library.zip'
    options['windows'] = [{
        'script': 'inspause.py',
        'icon_resources': [(0, 'icon.ico')],
        #'other_resources': [(24, 1, manifest)],
    }]


def get_manifest():
    # this manifest enables the standard Windows XP/Vista-looking theme
    return '''\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1"
manifestVersion="1.0">
<assemblyIdentity
    version="0.64.1.0"
    processorArchitecture="x86"
    name="Controls"
    type="win32"
/>
<description>Picalo</description>
<dependency>
    <dependentAssembly>
        <assemblyIdentity
            type="win32"
            name="Microsoft.Windows.Common-Controls"
            version="6.0.0.0"
            processorArchitecture="X86"
            publicKeyToken="6595b64144ccf1df"
            language="*"
        />
    </dependentAssembly>
</dependency>
</assembly>
'''


if __name__ == '__main__':
    main()
