# coding: utf-8

from distutils.core import Command
import os
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
    template = os.path.join('..', 'inspause_template.wxs')
    wxs0 = '%s.wxs' % f
    obj0 = '%s.wixobj' % f
    wxs1 = 'files_%s.wxs' % f
    obj1 = 'files_%s.wixobj' % f
    dst = '%s.msi' % f

    args = ['heat', 'dir', f, '-dr', 'INSPAUSE', '-cg', 'InspauseGroup',
            '-gg', '-g1', '-sfrag', '-srd', '-sreg', '-var', 'var.inspauseDir',
            '-out', wxs1]
    subprocess.call(args, shell=True)

    create_wxs0(template, wxs0, inspause.__version__)

    args = ['candle', '-nologo', wxs0, '-out', obj0]
    subprocess.call(args, shell=True)

    args = ['candle', '-nologo', '-dinspauseDir=' + f, wxs1, '-out', obj1]
    subprocess.call(args, shell=True)

    args = ['light', '-nologo', '-cultures:ja-jp', obj0, obj1, '-out', dst]
    subprocess.call(args, shell=True)

    os.chdir('..')


def create_wxs0(template, f, ver):
    with open(f, 'w') as fout:
        with open(template, 'r') as fin:
            for line in fin:
                fout.write(line.replace('{{VERSION}}', ver))
