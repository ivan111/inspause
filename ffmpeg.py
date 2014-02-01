# -*- coding: utf-8 -*-

'''
Ffmpegのラッパー
python標準のwaveのように動く
'''

__all__ = ['open']

import __builtin__
from datetime import datetime as dt
import os
import re
import subprocess as sp
import sys


ffmpeg_bin = ''

DURATION_RE = re.compile(r'Duration:\s*(\d{2}:\d{2}:\d{2}\.\d{2})')
EXTENSIONS = ['mp3', 'aac', 'm4a', 'wma']

# ffmpeg存在チェック
has_ffmpeg = False

def which(name):
    path = '.' + os.pathsep + os.environ.get('PATH', None)
    if not path:
        return None

    for p in path.split(os.pathsep):
        p = os.path.join(p, name)
        if os.access(p, os.X_OK):
            return p

    return None

ffmpeg_name = 'ffmpeg'
if sys.platform == 'win32':
    ffmpeg_name += '.exe'

try:
    result = which(ffmpeg_name)
    if result:
        has_ffmpeg = True
        ffmpeg_bin = ffmpeg_name
except:
    pass


def open(f, mode='rb', prg=None):
    if mode in ('r', 'rb'):
        r_mode = True
    elif mode in ('w', 'wb'):
        r_mode = False
    else:
        raise Exception("mode must be 'r', 'rb', 'w', or 'wb'")

    ext = get_ext(f)

    if r_mode:
        return Ffmpeg_read(f, prg)
    else:
        return Ffmpeg_write(f)


class Ffmpeg_read(object):

    def __init__(self, f, prg=None):
        self._load(f, prg)

    def _load(self, f, prg):
        if not os.path.exists(f):
            raise Exception('file not found: %s' % f)

        if prg:
            # TODO: もっといい方法があるはず
            # UNIX系ならselect使って音声読み込みのときstderrに出力される
            # Durationを見ればいいけろ、Windowsじゃだめ。
            dur_s = self._getduration_s(f)

        if sys.platform == 'win32':
            f = f.encode('CP932')
            # コンソールを表示しない
            startupinfo = sp.STARTUPINFO()
            startupinfo.dwFlags |= sp.STARTF_USESHOWWINDOW
        else:
            f = f.encode('UTF-8')
            startupinfo = None

        nul_file = __builtin__.open(os.devnull, 'w')

        args = [ffmpeg_bin, '-i', f, '-f', 's16le', '-acodec', 'pcm_s16le',
               '-ar', '44100', '-ac', '2', '-']

        # ffmpegがoverreadエラーを出力した場合に止まってしまったので
        # stderr出力を捨てるようにした。
        pipe = sp.Popen(args,
                        stdin=sp.PIPE, stdout=sp.PIPE, stderr=nul_file,
                        startupinfo=startupinfo)

        self.ch = 2
        self.w = 2
        self.rate = 44100
        self.frame_size = self.ch * self.w

        if prg:
            total_nframes = int(dur_s * self.rate)
            percent = 0
            prg(percent)

            CHUNK = 4096

            buf = []
            read_nframes = 0
            data = pipe.stdout.read(CHUNK)
            while len(data) > 0:
                buf.append(data)

                read_nframes += len(data) * self.frame_size
                new_percent = read_nframes * 100 / total_nframes

                if new_percent != percent and new_percent < 100:
                    percent = new_percent
                    prg(percent)

                data = pipe.stdout.read(CHUNK)

            percent = 100
            prg(percent)

            self.buf = ''.join(buf)
        else:
            self.buf = pipe.stdout.read()

        self.nframes = len(self.buf) / self.frame_size
        self.pos_f = 0

        pipe.stdin.close()
        pipe.stdout.close()
        nul_file.close()

    def _getduration_s(self, f):
        if sys.platform == 'win32':
            f = f.encode('CP932')
            # コンソールを表示しない
            startupinfo = sp.STARTUPINFO()
            startupinfo.dwFlags |= sp.STARTF_USESHOWWINDOW
        else:
            f = f.encode('UTF-8')
            startupinfo = None

        nul_file = __builtin__.open(os.devnull, 'w')

        args = [ffmpeg_bin, '-i', f]

        pipe = sp.Popen(args,
                        stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE,
                        startupinfo=startupinfo)

        dur_s = 0.0

        for line in iter(pipe.stderr.readline, ''):
            m = DURATION_RE.search(line)

            if m:
                try:
                    dur_dt = dt.strptime(m.group(1), '%H:%M:%S.%f')
                    dur_date = dt.combine(dur_dt.date(), dt.min.time())
                    dur_delta = dur_dt - dur_date
                    dur_s = dur_delta.total_seconds()
                except:
                    pass

                break

        pipe.stdin.close()
        pipe.stdout.close()
        pipe.stderr.close()
        nul_file.close()

        return dur_s

    def getnchannels(self):
        return self.ch

    def getsampwidth(self):
        return self.w

    def getframerate(self):
        return self.rate

    def getnframes(self):
        return self.nframes

    def getcomptype(self):
        return None

    def getcompname(self):
        return 'not compressed'

    def getparams(self):
        pass

    def getmarkers(self):
        return None

    def getmark(self, id):
        raise Exception()

    def readframes(self, nframes):
        rest_f = self.nframes - self.pos_f
        nframes = max(0, min(nframes, rest_f))

        if nframes == 0:
            return ''

        pos_b = self.pos_f * self.frame_size
        n_b = nframes * self.frame_size
        frames = self.buf[pos_b: pos_b + n_b]

        self.pos_f += nframes

        return frames

    def rewind(self):
        self.pos_f = 0

    def setpos(self, pos_f):
        self.pos_f = max(0, min(pos_f, self.nframes))

    def tell(self):
        return self.pos_f

    def close(self):
        pass


class Ffmpeg_write(object):

    def __init__(self, f):
        self.pipe = None

        if sys.platform == 'win32':
            f = f.encode('CP932')
            startupinfo = sp.STARTUPINFO()
            startupinfo.dwFlags |= sp.STARTF_USESHOWWINDOW
        else:
            f = f.encode('UTF-8')
            startupinfo = None

        self.nul_file = __builtin__.open(os.devnull, 'w')

        ext = get_ext(f)

        '''
        acodec = get_encoder(ext)

        if not acodec:
            raise Exception('Not Found Encoder')

        args = [ffmpeg_bin, '-y', '-f', 's16le', '-acodec', 'pcm_s16le',
            '-ar', '44100', '-ac','2', '-i', '-',
            '-vn', '-acodec', acodec, '-b', '128k', f]
        '''

        args = [ffmpeg_bin, '-y', '-f', 's16le', '-acodec', 'pcm_s16le',
            '-ar', '44100', '-ac','2', '-i', '-',
            '-vn', '-b', '128k', f]

        self.pipe = sp.Popen(args,
            stdin=sp.PIPE, stdout=sp.PIPE, stderr=self.nul_file,
            startupinfo=startupinfo)

    def __del__(self):
        self.close()

    def setnchannels(self, ch):
        pass

    def setsampwidth(self, w):
        pass

    def setframerate(self, rate):
        pass

    def writeframes(self, frames):
        self.pipe.stdin.write(frames)

    def close(self):
        if self.pipe:
            self.pipe.stdin.close()
            self.pipe.stdout.close()
            self.nul_file.close()

            self.pipe = None
            self.nul_file = None


def get_ext(name):
    '''
    拡張子を取得する。先頭のドットは含まない。
    '''

    root, ext = os.path.splitext(name)
    ext = ext.lower()

    if ext.startswith('.'):
        ext = ext[1:]

    return ext


def get_encoder(ext):
    acodec = None

    if ext == 'mp3':
        acodec = 'libmp3lame'
    elif ext == 'aac' or ext == 'm4a':
        if sys.platform == 'win32':
            acodec = 'libvo_aacenc'
        else:
            acodec = 'libfaac'
    elif ext == 'wma':
        acodec = 'wmav2'

    return acodec
