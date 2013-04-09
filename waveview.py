# -*- coding: utf-8 -*-
'''
音声の表示と再生
'''

import os

import wx

from labels import Labels, NO_DISTINCTION
from labelswindow import LabelsWindow, LabelChangedEvent, EVT_LBL_CHANGED_ID, EVT_PLAY_IFCUT_ID
from volumewindow import EVT_CLICK_CUR_CHANGED_ID, ClickCurChangedEvent
from waveplayer import WavePlayer, EVT_CUR_CHANGED_ID, EVT_EOF_ID, EOFEvent


class WaveView(wx.Panel):
    '''
    音声表示クラス
    '''

    def __init__(self, *args, **kwargs):
        self._listener = kwargs['listener']
        del kwargs['listener']

        wx.Panel.__init__(self, *args, **kwargs)

        self._init_instance_var()
        self._init_widged()
        self._bind_events()


    def _init_instance_var(self):
        self.win  = None  # LabelsWindow

        # ---- プロパティ用
        self._wav = None  # MyWave
        self._wp  = None  # WavePlayer
        self._factor = 0
        self._add = 0


    def _init_widged(self):
        layout = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(layout)

        self.win = LabelsWindow(self)
        layout.Add(self.win, proportion=1, flag=wx.EXPAND)


    def _bind_events(self):
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_KEY_DOWN,  self.OnKeyDown)

        self.Connect(-1, -1, EVT_CLICK_CUR_CHANGED_ID, self.OnClickCurChanged)
        self.Connect(-1, -1, EVT_CUR_CHANGED_ID,       self.OnPlayerCurChanged)
        self.Connect(-1, -1, EVT_EOF_ID,               self.OnEOF)
        self.Connect(-1, -1, EVT_LBL_CHANGED_ID,       self.OnLabelChanged)
        self.Connect(-1, -1, EVT_PLAY_IFCUT_ID,        self.OnPlayIfCut)


    #--------------------------------------------------------------------------
    # コマンド

    def cancel(self):
        if self.wp:
            self.wp.stop_thread()
            self.wp.join()


    # ---- 保存

    def save(self):
        if not self.can_save():
            return

        self.win.save()

    def can_save(self):
        if self.win and self.win.can_save():
            return True
        else:
            return False


    # ---- ラベル検索

    def find(self, sil_lv, sil_dur, before_dur, after_dur):
        self.win.find(sil_lv, sil_dur, before_dur, after_dur)


    # ---- ラベルをずらす

    def shift(self, val_s):
        if self.win is None:
            return

        self.win.shift(val_s)


    # ---- ラベルを読み込む

    def load_labels(self):
        if self.wav is None:
            return

        if os.path.exists(self.wav.labels_file):
            labels = Labels(open(self.wav.labels_file, 'r').readlines())
        else:
            labels = self.wav.find_sound()

        self.win.labels = labels


    # ---- シーク

    def head(self):
        if not self.can_head():
            return

        self.wp.cur_s = 0
        self.win.head()

    def can_head(self):
        if self.wp and self.win.cur_f != 0:
            return True
        else:
            return False

    def tail(self):
        if not self.can_tail():
            return

        if self.playing:
            self.playing = False

        self.wp.tail()
        self.win.tail()

    def can_tail(self):
        if self.wp and self.win.cur_f < self.win.max_f:
            return True
        else:
            return False


    # ---- 再生

    def play(self):
        if not self.can_play():
            return

        self.wp.play()
        self.win.playing = True

        # ツールバー更新のため
        if self._listener:
            wx.PostEvent(self._listener, ClickCurChangedEvent(self.win.cur_s))

    def can_play(self):
        if self.wp and self.wp.can_play():
            return True
        else:
            return False

    def pause_mode_play(self):
        if not self.can_pause_mode_play():
            return

        self.wp.pause_mode_play(self.win.lm(), self.factor, self.add)
        self.win.playing = True

        # ツールバー更新のため
        if self._listener:
            wx.PostEvent(self._listener, ClickCurChangedEvent(self.win.cur_s))

    def can_pause_mode_play(self):
        if self.wp and self.wp.can_play():
            return True
        else:
            return False

    def play_selected(self):
        if not self.can_play_selected():
            return

        self.wp.play_selected(self.win.lm().selected)
        self.win.playing = True

        # ツールバー更新のため
        if self._listener:
            wx.PostEvent(self._listener, ClickCurChangedEvent(self.win.cur_s))

    def can_play_selected(self):
        if self.wp and self.wp.can_play() and self.win.lm and self.win.lm().selected:
            return True
        else:
            return False

    def play_ifcut(self):
        if not self.can_play_ifcut():
            return

        self.wp.play_ifcut(self.win.cur_s, False)
        self.win.playing = True

        # ツールバー更新のため
        if self._listener:
            wx.PostEvent(self._listener, ClickCurChangedEvent(self.win.cur_s))

    def can_play_ifcut(self):
        return self.can_cut()

    def play_ifcut_anywhere(self):
        if not self.wav or self.playing:
            return

        self.wp.play_ifcut(self.win.cur_s, False)
        self.win.playing = True

        # ツールバー更新のため
        if self._listener:
            wx.PostEvent(self._listener, ClickCurChangedEvent(self.win.cur_s))

    def pause(self):
        if not self.can_pause():
            return

        self.playing = False

        # ツールバー更新のため
        if self._listener:
            wx.PostEvent(self._listener, ClickCurChangedEvent(self.win.cur_s))

    def can_pause(self):
        if self.wp and self.playing:
            return True
        else:
            return False


    # ---- 拡大・縮小

    def zoom_in(self):
        if not self.can_zoomin():
            return

        self.win.zoom_in()

    def can_zoomin(self):
        if self.wav is None:
            return False

        return self.win.can_zoomin()

    def zoom_out(self):
        if not self.can_zoomout():
            return

        self.win.zoom_out()

    def can_zoomout(self):
        if self.wav is None:
            return False

        return self.win.can_zoomout()


    # ---- ラベル編集

    def insert_label(self):
        if not self.can_insert_label():
            return

        self.win.insert_label()

    def can_insert_label(self):
        return self.win.can_insert_label()

    def remove_label(self):
        if not self.can_remove_label():
            return

        self.win.remove_label()

    def can_remove_label(self):
        if self.wav is None or self.playing:
            return False

        return self.win.can_remove_label()

    def cut(self):
        if not self.can_cut():
            return

        self.win.cut()

    def can_cut(self):
        if self.wav is None or self.playing:
            return False

        return self.win.can_cut()

    def merge_left(self):
        if not self.can_merge_left():
            return

        self.win.merge_left()

    def can_merge_left(self):
        if self.playing:
            return False

        return self.win.can_merge_left()

    def merge_right(self):
        if not self.can_merge_right():
            return

        self.win.merge_right()

    def can_merge_right(self):
        if self.playing:
            return False

        return self.win.can_merge_right()


    # ---- 履歴

    def undo(self):
        if not self.can_undo():
            return

        self.win.undo()

    def can_undo(self):
        if self.playing:
            return False

        return self.win.can_undo()

    def redo(self):
        if not self.can_redo():
            return

        self.win.redo()

    def can_redo(self):
        if self.playing:
            return False

        return self.win.can_redo()


    #--------------------------------------------------------------------------
    # イベントハンドラ


    def OnLeftDown(self, evt):
        if self._listener and self.wav is None:
            self._listener.OnOpenDir(None)


    def OnKeyDown(self, evt):
        if self.wp is None:
            return

        key = evt.GetKeyCode()

        if key == wx.WXK_SPACE:
            if self.can_pause():
                self.pause()
            else:
                if evt.ControlDown() and self.can_pause_mode_play():
                    self.pause_mode_play()
                else:
                    self.play()

        if key < 256:
            ch = chr(key).lower()
        else:
            ch = ''

        if ch == 'b':
            self.play_ifcut_anywhere()
        elif ch == 's':
            if evt.ControlDown():
                self.save()
            else:
                self.play_selected()


    # 波形画面がクリックされた
    def OnClickCurChanged(self, evt):
        if self.wp:
            if self.wp.ifcut_mode:
                self.playing = False
            else:
                self.wp.seek(evt.cur_s)
            wx.PostEvent(self._listener, ClickCurChangedEvent(evt.cur_s))

    # プレーヤーの再生位置が変わった
    def OnPlayerCurChanged(self, evt):
        self.win.cur_s = evt.cur_s


    # プレーヤーの再生が終了した
    def OnEOF(self, evt):
        self.win.playing = False
        wx.PostEvent(self._listener, EOFEvent())


    # ラベルの内容が変わった
    def OnLabelChanged(self, evt):
        if self.wp and self.win:
            self.wp.cur_s = self.win.cur_s

        wx.PostEvent(self._listener, LabelChangedEvent())


    # もしカット再生依頼
    def OnPlayIfCut(self, evt):
        if not self.wp:
            return

        self.wp.play_ifcut(evt.cut_s, False)
        self.win.playing = True

        # ツールバー更新のため
        if self._listener:
            wx.PostEvent(self._listener, ClickCurChangedEvent(evt.cut_s))


    #--------------------------------------------------------------------------
    # プロパティ

    # ---- 音声データ

    @property
    def wav(self):
        return self._wav

    @wav.setter
    def wav(self, wav):
        self._wav = wav

        if wav is None:
            self._wp = None
            self.win.lm = None
            self.win.wav = None
            return

        # wav を設定したあとに labels を設定するとチラつくのでいったん None
        self.win.wav = None
        self.wp = WavePlayer(wav)

        self.load_labels()

        self.win.wav = wav

        self.win.auto_shift()


    # ---- プレーヤー

    @property
    def wp(self):
        return self._wp

    @wp.setter
    def wp(self, wp):
        # すでに他のプレーヤーがあるなら破棄する
        if self._wp:
            self._wp.stop_thread()
            self._wp.join()

        self._wp = wp

        wp.add_listener(self)
        wp.start()


    # ---- 表示範囲

    @property
    def scale(self):
        return self.win.scale

    @scale.setter
    def scale(self, scale):
        self.win.scale = scale


    # ---- 拡大率

    @property
    def view_factor(self):
        return self.win.view_factor

    @view_factor.setter
    def view_factor(self, view_factor):
        self.win.view_factor = view_factor


    # ---- 再生中か？

    @property
    def playing(self):
        if self.wp:
            return self.wp.playing
        else:
            return False

    @playing.setter
    def playing(self, is_playing):
        if self.wp:
            self.win.playing = is_playing
            self.wp.playing = is_playing


    # ---- ポーズ時間ファクター

    @property
    def factor(self):
        return self._factor

    @factor.setter
    def factor(self, factor):
        self._factor = factor


    # ---- ポーズ時間ファクター

    @property
    def add(self):
        return self._add

    @add.setter
    def add(self, add):
        self._add = add


    # ---- 背景色

    @property
    def bg_color(self):
        return self.win.bg_color

    @bg_color.setter
    def bg_color(self, color):
        self.win.bg_color = color


    # ---- 前景色

    @property
    def fg_color(self):
        return self.win.fg_color

    @fg_color.setter
    def fg_color(self, color):
        self.win.fg_color = color


if __name__ == '__main__':
    from mywave import MyWave

    def main():
        app = TestWaveView(redirect=True, filename='log_waveview.txt')
        app.MainLoop()

    class TestWaveView(wx.App):
        def OnInit(self):
            frame = wx.Frame(None, -1, 'TestWaveView')

            window = WaveView(frame, listener=self)
            window.wav = MyWave('in.wav')

            frame.Centre()
            frame.Show()

            return True

    main()
