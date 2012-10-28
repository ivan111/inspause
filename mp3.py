# -*- coding: utf-8 -*-

from ctypes import *
import struct

try:
    lib = cdll.LoadLibrary('libmad.dll')
except:
    print 'could not load libmad.dll'

BUF_SIZE = 5 * 8192


class MP3:
    _handle = -1

    def open(self, file_name):
        self._handle = lib.open(file_name.encode('shift-jis'))
        if self._handle == -1:
            raise IOError, 'mp3 file open error'

    def close(self):
        if self._handle != -1:
            lib.close(self._handle)

    def getnchannels(self):
        ch = 2

        if self._handle != -1:
            ch = lib.getnchannels(self._handle)

        return ch

    def getsampwidth(self):
        return 2

    def getframerate(self):
        rate = 0

        if self._handle != -1:
            rate = lib.getframerate(self._handle)

        return rate

    def readframes(self, n):
        buffer = ''

        if self._handle == -1:
            return buffer

        c_short_a = c_short * n
        buf = c_short_a()
        lib.readframes.argtypes = [c_int, POINTER(c_short), c_int]

        try:
            size = lib.readframes(self._handle, buf, n)
            if size != 0:
                buffer = struct.pack('%dh' % size, *buf)
        except Exception as e:
            print e.message

        return buffer


def readallframes(file_name):
    handle = lib.open(file_name.encode('shift-jis'))
    if handle == -1:
        raise IOError, 'mp3 file open error'

    c_short_a = c_short * BUF_SIZE
    buf = c_short_a()
    lib.readframes.argtypes = [c_int, POINTER(c_short), c_int]

    try:
        size = lib.readframes(handle, buf, BUF_SIZE)

        buffer = ''
        while size != 0:
            buffer += struct.pack('%dh' % size, *buf)
            size = lib.readframes(handle, buf, BUF_SIZE)

        ch = lib.getnchannels(handle)
        rate = lib.getframerate(handle)
    except Exception as e:
        print e.message

        buffer = ''
        ch = 2
        rate = 0

    lib.close(handle)

    return (buffer, ch, rate)


if __name__ == '__main__':
    mp3 = MP3()
    mp3.open('in.mp3')
    ch = mp3.getnchannels()
    rate = mp3.getframerate()
    buf = mp3.readframes(1024)
    mp3.close()
    print 'len: %d, ch: %d, rate: %d' % (len(buf), ch, rate)

    buf, ch, rate = readallframes('in.mp3')
    print 'len: %d, ch: %d, rate: %d' % (len(buf), ch, rate)
