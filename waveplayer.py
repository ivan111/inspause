# -*- coding: utf-8 -*-

from threading import Thread

import pyaudio
import wx


CHUNK_F = 1024


class WavePlayer(object):
    '''
    音を再生するプレイヤ
    '''

    def __init__(self):
        self.wxid = wx.NewId()
        self.is_playing = False
        self.player = None
        self.listeners = set()
        self.pyaudio = pyaudio.PyAudio()

    def run(self):
        ch = self.wav.getnchannels()
        w = self.wav.getsampwidth()
        rate = self.wav.getframerate()
        format = self.pyaudio.get_format_from_width(w)

        stream = self.pyaudio.open(format=format,
                                   channels=ch, rate=rate, output=True)

        while True:
            if not self.is_playing:
                break

            frames = self.wav.readframes(CHUNK_F)

            if len(frames) == 0:
                if not self.is_repeat:  # EOW
                    self.post_eow_evt()
                    break

                self.wav.rewind()

            stream.write(frames)

            self.post_cur_pos_evt(self.wav.tell())

        self.is_playing = False

        stream.close()

    def add_listener(self, listener):
        self.listeners.add(listener)

    def remove_listener(self, listener):
        self.listeners.remove(listener)

    #--------------------------------------------------------------------------
    # コマンド

    # ---- 再生

    def play(self, wav, is_repeat):
        if self.is_playing:
            self.pause()

        self.wav = wav
        self.is_playing = True
        self.is_repeat = is_repeat

        self.player = Thread(target=self.run)
        self.player.setDaemon(True)
        self.player.start()

    def can_play(self):
        return not self.is_playing

    def pause(self):
        if self.is_playing and self.player:
            self.is_playing = False
            self.player.join()
            self.player = None
        else:
            self.is_playing = False

    def can_pause(self):
        return self.is_playing

    #--------------------------------------------------------------------------
    # 内部メソッド

    def post_cur_pos_evt(self, pos_f):
        event = WavePlayerEvent(myEVT_CUR_POS_CHANGE, self.wxid)
        event.SetPos(pos_f)

        for listener in self.listeners:
            # 別スレッドから実行されるのが普通なので
            # AddPendingEvent でイベントをキューに入れる。
            # ProcessEvent だとエラーになる。
            listener.GetEventHandler().AddPendingEvent(event)

    def post_eow_evt(self):
        event = WavePlayerEvent(myEVT_EOW, self.wxid)

        for listener in self.listeners:
            listener.GetEventHandler().AddPendingEvent(event)


#------------------------------------------------------------------------------
# イベント
#------------------------------------------------------------------------------

# ---- イベントタイプ
myEVT_CUR_POS_CHANGE = wx.NewEventType()
myEVT_EOW = wx.NewEventType()

# ---- イベントバインダ
EVT_CUR_POS_CHANGE = wx.PyEventBinder(myEVT_CUR_POS_CHANGE, 1)
EVT_EOW = wx.PyEventBinder(myEVT_EOW, 1)


class WavePlayerEvent(wx.PyCommandEvent):
    def __init__(self, event_type, id, pos_f=0):
        wx.PyCommandEvent.__init__(self, event_type, id)
        self.pos_f = pos_f

    def GetPos(self):
        return self.pos_f

    def SetPos(self, pos_f):
        self.pos_f = pos_f
