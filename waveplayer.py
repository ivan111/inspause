# -*- coding: utf-8 -*-

import pyaudio
import threading
import time
import struct
import wx

from insertpause import FACTOR, ADD

EVT_UPDATE_ID = wx.NewId()
EVT_EOF_ID = wx.NewId()
CHUNK = 1024

PB_DUR = 0.5
PB_PAUSE_SEC = 0.5


class UpdateEvent(wx.PyEvent):
    def __init__(self, cur_f):
        wx.PyEvent.__init__(self)
        self.SetEventType(EVT_UPDATE_ID)
        self.cur_f = cur_f


class EOFEvent(wx.PyEvent):
    def __init__(self):
        wx.PyEvent.__init__(self)
        self.SetEventType(EVT_EOF_ID)


class WavePlayer(threading.Thread):
    def __init__(self, listener, buffer, nchannels, sampwidth, framerate):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.listener = listener

        self.buffer = buffer
        self.nchannels = nchannels
        self.sampwidth = sampwidth
        self.framerate = framerate
        self.nframes = len(buffer) / (nchannels * sampwidth)
        self.min_f = 0
        self.max_f = self.nframes
        self.start_cur_f = 0

        self.pause_mode = False
        self.labels = []
        self.cur_lbl_pos = 0
        self.is_in_label = False
        self.factor = FACTOR
        self.add = ADD

        self.border_mode = False
        self.border_f = 0

    def run(self):
        p = pyaudio.PyAudio()

        stream = p.open(format=p.get_format_from_width(self.sampwidth),
                        channels=self.nchannels,
                        rate=self.framerate,
                        output=True)

        self.pause_f = 0

        while True:
            if self.cancel:
                break
            if self.playing:
                if self.cur_f < self.min_f:
                    self.cur_f = self.min_f

                if 0 < self.pause_f:
                    # Play Pause
                    nframes = min(CHUNK, self.pause_f)
                    stream.write(struct.pack('%ds' % nframes, ''))
                    self.pause_f = self.pause_f - nframes

                    self.is_in_label = False
                elif self.cur_f < self.max_f:
                    # Play
                    wx.PostEvent(self.listener, UpdateEvent(self.cur_f))
                    st = self.cur_f * self.nchannels * self.sampwidth
                    ed = st + (CHUNK * self.nchannels * self.sampwidth)
                    ed = min(ed, len(self.buffer))
                    stream.write(self.buffer[st: ed])
                    self.cur_f = self.cur_f + CHUNK

                    # Border Mode
                    if self.border_mode:
                        if self.border_f < self.cur_f:
                            self.pause_f = int(PB_PAUSE_SEC * self.framerate)
                            self.border_mode = False

                    # Pause Mode
                    if self.pause_mode:
                        cur_s = float(self.cur_f) / self.framerate

                        if self.cur_lbl_pos < len(self.labels):
                            label = self.labels[self.cur_lbl_pos]

                            if not self.is_in_label and label.start < cur_s:
                                if label.end < cur_s:
                                    self.cur_lbl_pos += 1
                                else:
                                    self.is_in_label = True

                            if self.is_in_label:
                                if label.is_pause():
                                    if label.end < cur_s:
                                        if label.is_spec():
                                            dur = label.dur
                                        else:
                                            dur = label.dur * self.factor + self.add
                                        self.pause_f = int(dur * self.framerate)
                                        self.pause_f = max(0, min(self.pause_f, self.nframes))

                                        self.cur_lbl_pos += 1

                                elif label.is_cut():
                                    end_f = int(label.end * self.framerate)
                                    self.cur_f = max(0, min(end_f, self.nframes))
                                    self.cur_lbl_pos += 1

                                else:
                                    self.cur_lbl_pos += 1
                else:
                    # EOF
                    self.playing = False
                    self.pause_mode = False
                    self.cur_f = self.start_cur_f
                    wx.PostEvent(self.listener, UpdateEvent(self.start_cur_f))
                    wx.PostEvent(self.listener, EOFEvent())
            else:
                # Pause
                self.pause_mode = False
                self.pause_f = 0
                time.sleep(0.1)

        stream.close()
        p.terminate()

    _cancel = False

    def seek(self, labels, pos):
        self.labels = labels
        self.cur_f = pos

        self.search_label_pos()

    def search_label_pos(self):
        cur_s = float(self.cur_f) / self.framerate

        self.pause_f = 0
        self.is_in_label = False

        i = 0
        for label in self.labels:
            if label.is_pause():
                if cur_s < label.end:
                    if label.start <= cur_s:
                        self.is_in_label = True
                    break
            elif label.is_cut():
                if label.start < cur_s and cur_s < label.end:
                    self.is_in_label = True
                    break

                if cur_s < label.start:
                    break

            i += 1

        self.cur_lbl_pos = i

    def play(self):
        self.pause_mode = False
        self.border_mode = False

        self.min_f = 0
        self.max_f = self.nframes
        self.start_cur_f = self.cur_f

        self.playing = True

    def can_play(self):
        if (not self.playing) and (self.cur_f < self.nframes):
            return True
        else:
            return False

    def pause_mode_play(self, labels, factor, add):
        self.pause_mode = True
        self.border_mode = False

        self.min_f = 0
        self.max_f = self.nframes
        self.start_cur_f = self.cur_f

        self.labels = labels
        self.factor = factor
        self.add = add

        self.playing = True

    def play_label(self, label):
        self.pause_mode = False
        self.border_mode = False

        self.min_f = int(label.start * self.framerate)
        self.max_f = int(label.end * self.framerate)

        min_dur_f = int(0.1 * self.framerate)

        if self.cur_f < self.min_f:
            self.cur_f = self.min_f
            self.start_cur_f = self.min_f
        elif self.max_f < self.cur_f:
            self.cur_f = self.min_f
            self.start_cur_f = self.cur_f
        else:
            if (self.max_f - self.cur_f) < min_dur_f:
                self.cur_f = self.min_f
                self.start_cur_f = self.min_f
            else:
                self.start_cur_f = self.cur_f

        self.playing = True

    def play_border(self, border_s, is_change_start_cur_f=True):
        self.pause_mode = False
        self.border_mode = True

        self.min_f = int((border_s - PB_DUR) * self.framerate)
        self.min_f = max(0, self.min_f)
        self.max_f = int((border_s + PB_DUR) * self.framerate)
        self.max_f = min(self.max_f, self.nframes)
        self.cur_f = self.min_f
        if is_change_start_cur_f:
            self.start_cur_f = self.cur_f
        else:
            self.start_cur_f = int(border_s * self.framerate)

        self.border_f = int(border_s * self.framerate)

        self.playing = True

    def get_cancel(self):
        return self._cancel

    def set_cancel(self, cancel):
        self._cancel = True

    cancel = property(get_cancel, set_cancel)

    _cur_f = 0

    def get_cur_f(self):
        return self._cur_f

    def set_cur_f(self, cur_f):
        self._cur_f = max(0, min(int(cur_f), self.nframes))

    cur_f = property(get_cur_f, set_cur_f)

    _playing = False

    def is_playing(self):
        return self._playing

    def set_playing(self, playing):
        self._playing = playing

    playing = property(is_playing, set_playing)

    _min_f = 0

    def get_min_f(self):
        return self._min_f

    def set_min_f(self, min_f):
        self._min_f = max(0, min(min_f, self.nframes))

    min_f = property(get_min_f, set_min_f)

    _max_f = 0

    def get_max_f(self):
        return self._max_f

    def set_max_f(self, max_f):
        self._max_f = max(0, min(max_f, self.nframes))

    max_f = property(get_max_f, set_max_f)
