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
        'packages': ['wx', 'pyaudio', 'win32event', 'win32api',
                     'win32com', 'winerror'],
        'excludes': ['tcl', 'numpy', 'scipy'],
        'dll_excludes': ['MSVCP90.dll', 'w9xpopen.exe',
            # エラーで出てきたDLLを追加。おまえ、間違ってはいませんか。冗談じゃないかしら。
            'api-ms-win-core-string-l1-1-0.dll', 'api-ms-win-core-psapi-l1-1-0.dll', 'api-ms-win-core-registry-l1-1-0.dll', 'api-ms-win-core-localization-l1-2-0.dll', 'api-ms-win-security-base-l1-1-0.dll', 'api-ms-win-core-string-obsolete-l1-1-0.dll', 'api-ms-win-core-delayload-l1-1-0.dll', 'api-ms-win-core-handle-l1-1-0.dll', 'api-ms-win-crt-private-l1-1-0.dll', 'api-ms-win-core-libraryloader-l1-2-1.dll', 'api-ms-win-core-memory-l1-1-0.dll', 'api-ms-win-core-heap-obsolete-l1-1-0.dll', 'api-ms-win-core-atoms-l1-1-0.dll', 'api-ms-win-core-processthreads-l1-1-1.dll', 'api-ms-win-core-heap-l2-1-0.dll', 'api-ms-win-core-delayload-l1-1-1.dll', 'api-ms-win-core-processthreads-l1-1-0.dll', 'api-ms-win-core-com-midlproxystub-l1-1-0.dll', 'api-ms-win-crt-string-l1-1-0.dll', 'api-ms-win-crt-runtime-l1-1-0.dll', 'api-ms-win-core-libraryloader-l1-2-0.dll', 'api-ms-win-core-errorhandling-l1-1-0.dll', 'api-ms-win-core-string-l2-1-0.dll', 'api-ms-win-core-synch-l1-2-0.dll', 'api-ms-win-core-profile-l1-1-0.dll', 'api-ms-win-core-synch-l1-1-0.dll', 'api-ms-win-core-threadpool-legacy-l1-1-0.dll', 'api-ms-win-core-interlocked-l1-1-0.dll', 'api-ms-win-core-debug-l1-1-0.dll', 'api-ms-win-core-sysinfo-l1-1-0.dll',
            'RPCRT4.dll', 'OLEAUT32.dll', 'USER32.dll', 'SHELL32.dll', 'ole32.dll', 'COMDLG32.dll', 'WSOCK32.dll', 'COMCTL32.dll', 'ADVAPI32.dll', 'mfc90.dll', 'msvcrt.dll', 'WS2_32.dll', 'WINSPOOL.DRV', 'GDI32.dll', 'WINMM.dll', 'VERSION.dll', 'KERNEL32.dll', 'ntdll.dll', 'OPENGL32.dll', 'UxTheme.dll'],
        'compressed': 1,
        'optimize': 2,
        'bundle_files': 3,
        'dist_dir': 'dist/inspausew-%s' % inspause.__version__,
    }

    files = ['gui.xrc', 'icon.ico', 'README.md', 'CHANGES.md', 'LICENSE.txt', 'ffmpeg.exe']
    options['data_files'] = [('backup', glob('backup\\*.zip')),
                             ('icon', glob('icon\\*.png')),
                             ('', files)]
    options['options'] = { 'py2exe': py2exe_options }
    options['zipfile'] = 'lib/library.zip'
    options['windows'] = [{
        'script': 'inspause.py',
        'icon_resources': [(0, 'icon.ico')],
    }]


if __name__ == '__main__':
    main()
