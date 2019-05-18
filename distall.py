# coding: utf-8

from distutils.core import Command
import os
import shutil
import subprocess
import zipfile

import inspause


class DistAllCommand(Command):
    description = 'create all inspause distributions'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        create_sdist()
        create_win_dist()
        create_win_installer()


def create_sdist():
    args = ['python', 'setup.py', 'sdist']
    subprocess.call(args, shell=True)


def create_win_dist():
    args = ['python', 'setup.py', 'py2exe']
    subprocess.call(args, shell=True)

    os.chdir('dist')

    in_f = 'inspausew-%s' % inspause.__version__
    out_f = in_f + '.zip'

    with zipfile.ZipFile(out_f, 'w', zipfile.ZIP_DEFLATED) as z:
        zipdir(in_f, z)

    os.chdir('..')


def zipdir(path, z):
    for root, dirs, files in os.walk(path):
        for f in files:
            z.write(os.path.join(root, f))


def create_win_installer():
    os.chdir('dist')

    f = 'inspausew-%s' % inspause.__version__
    template = os.path.join('..', 'inspausew.wxs')
    wxs = '%s.wxs' % f
    obj = '%s.wixobj' % f
    dst = '%s.msi' % f

    shutil.copyfile(template, wxs)

    args = ['candle', '-nologo', '-dversion=%s' % inspause.__version__,
            '-dinspauseDir=%s' % f, wxs, '-out', obj]
    subprocess.call(args, shell=True)

    args = ['light', '-nologo', '-cultures:ja-jp', obj, '-out', dst]
    subprocess.call(args, shell=True)

    os.chdir('..')
