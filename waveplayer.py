# -*- coding: utf-8 -*-

import threading
import time
import struct

import pyaudio
import wx

from mywave import CHUNK_F


EVT_CUR_CHANGED_ID = wx.NewId()
EVT_EOF_ID = wx.NewId()

# ---- もしカット再生
IFCUT_DUR_S   = 0.8  # 再生長さ（秒）。前後それぞれに設定される。
IFCUT_PAUSE_S = 0.5  # ポーズ時間（秒）


class WavePlayer(threading.Thread):
    '''
    wave 形式の音を再生するクラス
    ラベルを設定することでポーズ入りの再生ができる
    '''

    def __init__(self, wav):
        threading.Thread.__init__(self)
        self.setDaemon(True)

        self._init_instance_var(wav)


    def _init_instance_var(self, wav):
        self.wav = wav

        self.labels = []
        self.listenser = None
        self.is_running = True  # False ならスレッドを終了

        self.start_cur_f = 0

        self.pause_mode = False
        self.cur_lbl_pos = 0
        self.is_in_label = False
        self.factor = 0.5
        self.add = 0

        self.ifcut_mode = False
        self.ifcut_f = 0

        self.is_repeat = False

        self.first_pause = True

        # ---- プロパティ用
        self._cur_f = 0
        self._playing = False
        self._min_f = 0
        self._max_f = wav.max_f

    def run(self):
        p = pyaudio.PyAudio()

        stream = p.open(format=p.get_format_from_width(self.wav.w),
                        channels=self.wav.ch,
                        rate=self.wav.rate,
                        output=True)

        self.pause_fs = 0
        chunk_s = self.f_to_s(CHUNK_F)

        while True:
            if not self.is_running:
                break

            if not self.playing:
                # Pause

                if self.first_pause:
                    # 無音。streamに残っている余計な音をなくしておく。
                    # これがないと再生を再開したときに前の音が少し残っていることがある
                    stream.write(struct.pack('8192s', ''))

                    self.first_pause = False

                time.sleep(0.1)
                continue

            self.first_pause = True

            if 0 < self.pause_fs:
                # in pause
                nframes = min(CHUNK_F, self.pause_fs)
                stream.write(struct.pack('%ds' % nframes, ''))  # 無音
                self.pause_fs -= nframes

                self.is_in_label = False
            elif self.wav.cur_f >= self.max_f:
                if self.is_repeat:
                    self.wav.cur_f = 0

                    if self.pause_mode:
                        self.cur_lbl_pos = 0
                else:
                    # EOF
                    self.playing = False

                    self.wav.cur_f = self.start_cur_f

                    wx.PostEvent(self.listener, CurChangedEvent(self.wav.cur_s))
                    wx.PostEvent(self.listener, EOFEvent())
            else:
                # Play
                frames = self.wav.read()
                wx.PostEvent(self.listener, CurChangedEvent(self.wav.cur_s))

                if len(frames) == 0:
                    self.playing = False
                    wx.PostEvent(self.listener, EOFEvent())

                stream.write(frames)

                # IfCut Mode
                if self.ifcut_mode:
                    if self.ifcut_f < self.wav.cur_f + CHUNK_F:
                        # これも Pause Mode と同じように
                        # ぴったりの位置で止める処理をする

                        num_f = self.ifcut_f - self.wav.cur_f

                        if num_f > 0:
                            frames = self.wav.read(num_f)
                            stream.write(frames)

                            wx.PostEvent(self.listener, CurChangedEvent(self.wav.cur_s))

                        # ポーズを設定
                        self.pause_fs = self.wav.s_to_f(IFCUT_PAUSE_S) * self.wav.frame_size
                        self.ifcut_f = self.wav.max_f

                # Pause Mode
                if self.pause_mode:
                    if self.cur_lbl_pos < len(self.labels):
                        label = self.labels[self.cur_lbl_pos]

                        if not self.is_in_label and label.start_s < self.wav.cur_s:
                            # ラベルの中に入った

                            if label.end_s < self.wav.cur_s:
                                # ラベルはもう終わっていた
                                self.cur_lbl_pos += 1
                            else:
                                self.is_in_label = True

                        if self.is_in_label:
                            if label.is_pause():
                                if label.end_s < self.wav.cur_s + chunk_s:
                                    # ポーズラベルのケツに来た。
                                    # 実は chunk_s を足してるから少し余裕がある。
                                    # これはポーズ位置ぴったりで止まるため。
                                    #
                                    # ずれると言っても長くても 25 ms （0.025秒）ぐらい

                                    # ---- ラベルのケツにピッタリつける。
                                    # 余裕をもたせた分だけ再生する

                                    num_f = self.s_to_f(label.end_s - self.wav.cur_s)

                                    if num_f > 0:
                                        frames = self.wav.read(num_f)
                                        stream.write(frames)

                                        wx.PostEvent(self.listener, CurChangedEvent(self.wav.cur_s))


                                    # ---- ポーズを設定

                                    dur_s = label.dur_s * self.factor + self.add
                                    dur_s = dur_s * self.wav.frame_size
                                    self.pause_fs = self.s_to_f(dur_s)
                                    self.pause_fs = max(0, min(self.pause_fs, self.wav.max_f))

                                    self.cur_lbl_pos += 1

                            elif label.is_cut():
                                self.wav.cur_s = label.end_s
                                self.is_in_label = False
                                self.cur_lbl_pos += 1

                            else:
                                self.is_in_label = False
                                self.cur_lbl_pos += 1

        stream.close()
        p.terminate()

    def add_listener(self, listener):
        self.listener = listener

    def stop_thread(self):
        self.is_running = False

    def search_label_pos(self):
        cur_s = self.wav.cur_s

        self.pause_fs = 0
        self.is_in_label = False

        i = 0
        for label in self.labels:
            if label.is_pause():
                if cur_s < label.end_s:
                    if label.start_s <= cur_s:
                        self.is_in_label = True
                    break
            elif label.is_cut():
                if label.contains(cur_s):
                    self.is_in_label = True
                    break

                if cur_s < label.start_s:
                    break

            i += 1

        self.cur_lbl_pos = i

    def f_to_s(self, f):
        return float(f) / self.wav.rate

    def s_to_f(self, s):
        return int(s * self.wav.rate)


    #--------------------------------------------------------------------------
    # コマンド

    # ---- シーク

    def tail(self):
        self.seek(self.wav.dur_s)

    def seek(self, pos_s):
        self.wav.cur_s = pos_s

        if self.labels:
            self.search_label_pos()


    # ---- 再生

    def play(self):
        self.pause_mode = False
        self.ifcut_mode = False
        self.is_repeat  = True

        self.min_f = 0
        self.max_f = self.wav.max_f
        self.start_cur_f = self.wav.cur_f

        self.playing = True

    def can_play(self):
        if (not self.playing) and (self.wav.cur_f < self.wav.max_f):
            return True
        else:
            return False

    def pause_mode_play(self, labels, factor, add):
        self.pause_mode = True
        self.ifcut_mode = False
        self.is_repeat  = True

        self.min_f = 0
        self.max_f = self.wav.max_f
        self.start_cur_f = self.wav.cur_f

        self.labels = labels
        self.factor = factor
        self.add = add

        self.search_label_pos()

        self.playing = True

    def play_selected(self, selected):
        self.pause_mode = False
        self.ifcut_mode = False
        self.is_repeat  = False

        self.min_f = int(selected.start_s * self.wav.rate)
        self.max_f = int(selected.end_s * self.wav.rate)

        self.wav.cur_f = self.min_f
        self.start_cur_f = self.min_f

        self.playing = True

    def play_ifcut(self, ifcut_s, is_change_start_cur_f=True):
        self.pause_mode = False
        self.ifcut_mode = True
        self.is_repeat  = False

        self.min_f = int((ifcut_s - IFCUT_DUR_S) * self.wav.rate)
        self.min_f = max(0, self.min_f)
        self.max_f = int((ifcut_s + IFCUT_DUR_S) * self.wav.rate)
        self.max_f = min(self.max_f, self.wav.max_f)
        self.wav.cur_f = self.min_f
        if is_change_start_cur_f:
            self.start_cur_f = self.wav.cur_f
        else:
            self.start_cur_f = int(ifcut_s * self.wav.rate)

        self.ifcut_f = int(ifcut_s * self.wav.rate)

        self.playing = True


    #--------------------------------------------------------------------------
    # プロパティ

    # ---- 現在位置（フレーム）

    @property
    def cur_f(self):
        return self.wav.cur_f

    @cur_f.setter
    def cur_f(self, cur_f):
        self.wav.cur_f = cur_f


    # ---- 現在位置（秒）

    @property
    def cur_s(self):
        return self.wav.cur_s

    @cur_s.setter
    def cur_s(self, cur_s):
        self.wav.cur_s = cur_s


    # ---- 再生中か？

    @property
    def playing(self):
        return self._playing

    @playing.setter
    def playing(self, playing):
        if playing == False:
            self.pause_mode = False
            self.pause_fs = 0
            self.ifcut_mode = False

        self._playing = playing


    # ---- 最小フレーム

    @property
    def min_f(self):
        return self._min_f

    @min_f.setter
    def min_f(self, min_f):
        self._min_f = max(0, min(min_f, self.wav.max_f))


    # ---- 最大フレーム

    @property
    def max_f(self):
        return self._max_f

    @max_f.setter
    def max_f(self, max_f):
        self._max_f = max(0, min(max_f, self.wav.max_f))


# 現在位置が変わったら通知されるイベント
class CurChangedEvent(wx.PyEvent):
    def __init__(self, cur_s):
        wx.PyEvent.__init__(self)
        self.SetEventType(EVT_CUR_CHANGED_ID)
        self.cur_s = cur_s


# 再生が最後まで来たときに通知されるイベント
class EOFEvent(wx.PyEvent):
    def __init__(self):
        wx.PyEvent.__init__(self)
        self.SetEventType(EVT_EOF_ID)
