# -*- coding: utf-8 -*-

# Copyright (c) 2006-2010 Hubert Pham

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


# based on pyaudio

# ** NOTE ** : sample width 2 only

from ctypes import *
import sys

if sys.platform == "win32":
    paNoError = 0
    paUnanticipatedHostError = -9999
    paStreamIsNotStopped = -9982

    paFloat32 = 0x1
    paInt32 = 0x2
    paInt24 = 0x4
    paInt16 = 0x8
    paInt8 = 0x10
    paUInt8 = 0x20
    paCustomFormat = 0x10000


    try:
        lib = cdll.LoadLibrary("libportaudio.dll")
    except:
        f = open("log.txt", "a")
        f.write("libportaudio.dllÇ™å©Ç¬Ç©ÇËÇ‹ÇπÇÒÇ≈ÇµÇΩÅB")
        sys.exit(-1)


    lib.Pa_GetErrorText.restype = c_char_p

    class PaHostErrorInfo(Structure):
        _fields_ = [('hostApiType', c_int),
                    ('errorCode', c_long),
                    ('errorText', c_char_p)]

    def print_last_error():
        lib.Pa_GetLastHostErrorInfo.restype = POINTER(PaHostErrorInfo)
        info_p = lib.Pa_GetLastHostErrorInfo()
        info = info_p.contents
        print "hostApiType:", info.hostApiType
        print "errorCode:", info.errorCode
        print "errorText:", info.errorText

    class PaStreamParameters(Structure):
        _fields_ = [('device', c_int),
                    ('channelCount', c_int),
                    ('sampleFormat', c_ulong),
                    ('suggestedLatency', c_double),
                    ('hostApiSpecificStreamInfo', c_void_p)]

    class PaDeviceInfo(Structure):
        _fields_ = [('structVersion', c_int),
                    ('name', c_char_p),
                    ('hostApi', c_int),
                    ('maxInputChannels', c_int),
                    ('maxOutputChannels', c_int),
                    ('defaultLowInputLatency', c_double),
                    ('defaultLowOutputLatency', c_double),
                    ('defaultHighInputLatency', c_double),
                    ('defaultHighOutputLatency', c_double),
                    ('defaultSampleRate', c_double)]


    class MyPyAudio:
        def __init__(self):
            err = lib.Pa_Initialize()
            if err != paNoError:
                if err == paUnanticipatedHostError:
                    print_last_error()
                print "INIT ERROR"
                print "An error occured while using the portaudio stream"
                print "Error number: %d" % err
                print "Error message: %s" % lib.Pa_GetErrorText(err)
                lib.Pa_Terminate()
                raise Exception, "INIT ERROR"

        def open(self, *args, **kwargs):
            return MyStream(self, *args, **kwargs)

        def get_format_from_width(self, width, unsigned = True):
            if width == 1:
                if unsigned:
                    return paUInt8
                else:
                    return paInt8
            elif width == 2:
                return paInt16
            elif width == 3:
                return paInt24
            elif width == 4:
                return paFloat32
            else:
                raise ValueError, "Invalid width: %d" % width

        def terminate(self):
            lib.Pa_Terminate()


    class MyStream:
        def __init__(self,
                     mypa,
                     rate,
                     channels,
                     format,
                     input = False,
                     output = False):
            self._channels = channels

            outputParameters = PaStreamParameters()

            outputParameters.device = lib.Pa_GetDefaultOutputDevice();

            if outputParameters.device < 0:
                print "Invalid output device (no default output device)"
                raise Exception, "Invalid output device (no default output device)"

            outputParameters.channelCount = channels;
            outputParameters.sampleFormat = format;
            lib.Pa_GetDeviceInfo.restype = POINTER(PaDeviceInfo)
            device_info_p = lib.Pa_GetDeviceInfo(outputParameters.device)
            outputParameters.suggestedLatency = device_info_p.contents.defaultLowOutputLatency;
            outputParameters.hostApiSpecificStreamInfo = None

            self._stream = c_void_p(None)

            class PaStreamInfo(Structure):
                _fields_ = [('structVersion', c_int),
                            ('inputLatency', c_double),
                            ('outputLatency', c_double),
                            ('sampleRate', c_double)]

            paClipOff = 1
            lib.Pa_OpenStream.argtypes = [POINTER(c_void_p), POINTER(PaStreamParameters), POINTER(PaStreamParameters), c_double, c_ulong, c_ulong, c_void_p, c_void_p]
            err = lib.Pa_OpenStream(pointer(self._stream), None, pointer(outputParameters), rate, 1024, paClipOff, None, None)

            if err != paNoError:
                if err == paUnanticipatedHostError:
                    print_last_error()
                print
                print "An error occured while using the portaudio stream"
                print "Error number: %d" % err
                print "Error message: %s" % lib.Pa_GetErrorText(err)
                raise Exception, "ERROR: Pa_OpenStream"

            err = lib.Pa_StartStream(self._stream)

            if (err != paNoError) and (err != paStreamIsNotStopped):
                if err == paUnanticipatedHostError:
                    print_last_error()
                print "An error occured while using the portaudio stream"
                print "Error number: %d" % err
                print "Error message: %s" % lib.Pa_GetErrorText(err)
                lib.Pa_CloseStream(self._stream)
                raise Exception, "ERROR: Pa_StartStream"

        def close(self):
            lib.Pa_CloseStream(self._stream)


        def write(self, frames):
            num_frames = len(frames) / (self._channels * 2)  # sample width == 2 only
            err = lib.Pa_WriteStream(self._stream, frames, num_frames)
            if err != paNoError:
                if err == paUnanticipatedHostError:
                    print_last_error()
                print "An error occured while using the portaudio stream"
                print "Error number: %d" % err
                print "Error message: %s" % lib.Pa_GetErrorText(err)
                lib.Pa_CloseStream(self._stream)
                raise Exception, "ERROR: Pa_WriteStream"


