# -*- coding: utf-8 -*-

from ctypes import *
import struct

try:
    lib = cdll.LoadLibrary('libmad.dll')
except:
    print 'could not load libmad.dll'

BUF_SIZE = 1024 * 8

def readframes(file_name):
    handle = lib.openFile(file_name.encode('shift-jis'))
    if handle == -1:
        raise IOError, 'mp3 file open error'

    c_short_a = c_short * BUF_SIZE
    buf = c_short_a()
    lib.readFrames.argtypes = [c_int, POINTER(c_short), c_int]

    try:
        size = lib.readFrames(handle, buf, BUF_SIZE)

        buffer = ''
        while size != 0:
            buffer += struct.pack('%dh' % size, *buf)
            size = lib.readFrames(handle, buf, BUF_SIZE)

        rate = lib.getSamplerate(handle)
        ch = lib.getNumChannels(handle)
    except Exception as e:
        print e.message
        buffer = ''
        rate = 0
        ch = 2

    lib.closeFile(handle)

    return (buffer, rate, ch)

def readframesmono(file_name):
    handle = lib.openFile(file_name.encode('shift-jis'))
    if handle == -1:
        raise IOError, 'mp3 file open error'

    c_short_a = c_short * BUF_SIZE
    buf = c_short_a()
    lib.readFrames.argtypes = [c_int, POINTER(c_short), c_int]

    try:
        size = lib.readFramesMono(handle, buf, BUF_SIZE)

        buffer = ''
        while size != 0:
            buffer += struct.pack('%dh' % size, *buf)
            size = lib.readFramesMono(handle, buf, BUF_SIZE)

        rate = lib.getSamplerate(handle)
    except Exception as e:
        print e.message
        buffer = ''
        rate = 0

    lib.closeFile(handle)

    return (buffer, rate)


if __name__ == '__main__':
    buf, rate = readframes('in.mp3')
    print 'rate: %d' % rate
    print 'len: %d' % len(buf)
