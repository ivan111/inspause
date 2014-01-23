# -*- coding: utf-8 -*-

'''
ボリューム表示ウィンドウ
'''

import math
import os

import wx

from bufferedwindow import BufferedWindow, BG_COLOUR


MIN_SCALE = 3
MAX_VIEW_FACTOR = 16
PPU = 20  # Pixels Per Unit

# 色
FG_COLOUR = '#4B87EB'  # 前景色
OA_COLOUR = '#D3D3D3'  # 領域外の色
POS_COLOUR = 'Red'  # 現在位置線の色

# 矢印キーの移動量
SEEK_S = 0.002
SEEK_CTRL_S = 0.02
SEEK_SHIFT_S = 1

NO_WAV_MESSAGE1 = u'音声がありません。'
NO_WAV_MESSAGE2 = u'ここをクリックしてください。'


class VolumeWindow(BufferedWindow):
    '''
    ボリューム表示ウィンドウ
    '''

    binder = BufferedWindow.binder

    def __init__(self, *args, **kwargs):
        self._vol = None
        self._old_pos_i = -1
        self._pos_f = 0
        self._playing = False
        self._cur_pos_pen = wx.Pen(POS_COLOUR)

        # ---- 表示関連
        self._view_factor = 1
        self._scale = 100

        # ---- ドラッグスクロール関連
        self._ds_x = None
        self._ds_left_i = None

        BufferedWindow.__init__(self, *args, **kwargs)

        self.SetForegroundColour(FG_COLOUR)

        self.SetVolume(self._vol)

        self.SetCallAfter(self.DrawCurPos)

    def SetVolume(self, vol):
        self._vol = vol

        if vol:
            rate = vol.base_rate / self._view_factor
            vol.change_rate(rate)

        self.update_scroll()

        self._old_pos_i = -1
        self.pos_f = 0

    # ---- 変換

    def f_to_s(self, f):
        if self._vol:
            return float(f) / self._vol.wav_rate
        else:
            return 0.0

    def s_to_f(self, s):
        if self._vol:
            return int(s * self._vol.wav_rate)
        else:
            return 0

    def f_to_i(self, f):
        if self._vol:
            return f * self._vol.rate / self._vol.wav_rate
        else:
            return 0

    def i_to_f(self, s):
        if self._vol:
            return int(s * self._vol.wav_rate / self._vol.rate)
        else:
            return 0

    def i_to_s(self, i):
        if self._vol:
            return float(i) / self._vol.rate
        else:
            return 0.0

    def s_to_i(self, s):
        if self._vol:
            return int(s * self._vol.rate)
        else:
            return 0

    #--------------------------------------------------------------------------
    # 描画

    def Draw(self, dc, nlayer):
        if nlayer != 1:
            return

        BufferedWindow.Draw(self, dc, 0)

        if self._vol:
            self.DrawVolume(dc)
            self.DrawOutOfArea(dc)
        else:
            self.DrawMessage(dc)

    def DrawVolume(self, dc):
        '''
        ボリュームを描画
        '''

        w, h = dc.Size

        dc.SetPen(wx.Pen(self.GetForegroundColour()))

        max_val = int(float(self._vol.max_val) * self.scale / 100)
        if max_val == 0:
            max_val = 1  # 0で割ることを防ぐため

        for x in range(w):
            i = self.left_i + x
            if i >= len(self._vol):
                break
            v = int(h * float(self._vol[i]) / max_val)
            v = min(v, h)
            dc.DrawLine(x, h, x, h - v)

    def DrawOutOfArea(self, dc):
        '''
        波形領域外を描画
        '''

        w, h = dc.Size

        max_x = len(self._vol) - self.left_i
        if max_x < w:
            dc.SetPen(wx.TRANSPARENT_PEN)
            dc.SetBrush(wx.Brush(OA_COLOUR))

            dc.DrawRectangle(max_x, 0, w, h)

    def DrawCurPos(self, from_pos_f_method=False):
        '''
        現在位置を描画
        '''

        if self._vol is None:
            return

        dc = wx.ClientDC(self)
        dc.SetPen(self._cur_pos_pen)

        pos_i = self.pos_i
        left_i = self.left_i
        old_x = self._old_pos_i - left_i
        new_x = pos_i - left_i

        if self._old_pos_i != pos_i:
            base_dc = self.GetTopLayerDC()

            if self.playing:
                # 再生中は新しい位置を描いてから古い位置を消す方がちらつかない

                # 新しい位置を描く
                dc.DrawLine(new_x, 0, new_x, self.h)

                # 古い位置を消す
                if 0 <= old_x < self.w:
                    dc.Blit(old_x, 0, 1, self.h, base_dc, old_x, 0)
            else:
                # 古い位置を消す
                old_x = self._old_pos_i - self.left_i
                if 0 <= old_x < self.w:
                    dc.Blit(old_x, 0, 1, self.h, base_dc, old_x, 0)

                # 新しい位置を描く
                dc.DrawLine(new_x, 0, new_x, self.h)

            self._old_pos_i = pos_i
        elif not from_pos_f_method:
            # 新しい位置を描く
            dc.DrawLine(new_x, 0, new_x, self.h)

    def DrawMessage(self, dc):
        '''
        波形がないときのメッセージを描画
        '''

        w, h = dc.Size

        cw, ch = dc.GetTextExtent(NO_WAV_MESSAGE1)
        x = (w - cw) / 2
        y = h / 2 - ch
        dc.DrawText(NO_WAV_MESSAGE1, x, y)

        cw, ch = dc.GetTextExtent(NO_WAV_MESSAGE2)
        x = (w - cw) / 2
        y = h / 2
        dc.DrawText(NO_WAV_MESSAGE2, x, y)

    #--------------------------------------------------------------------------
    # コマンド

    # ---- シーク
    def head(self):
        if not self.can_head():
            return

        self.pos_f = 0
        self.post_vw_pos_evt()

    def can_head(self):
        if self._vol and self._pos_f != 0:
            return True
        else:
            return False

    def tail(self):
        if not self.can_tail():
            return

        self.pos_f = self._vol.max_f
        self.post_vw_pos_evt()

    def can_tail(self):
        if self._vol and self.pos_i < self._vol.max_f:
            return True
        else:
            return False

    # ---- 拡大・縮小
    def zoom_in(self, x=0):
        if not self.can_zoom_in():
            return

        self.set_view_factor(self.view_factor / 2, x)

    def can_zoom_in(self):
        if self._vol and self.view_factor >= 2:
            return True
        else:
            return False

    def zoom_out(self, x=0):
        if not self.can_zoom_out():
            return

        self.set_view_factor(self.view_factor * 2, x)

    def can_zoom_out(self):
        if self._vol and self.view_factor * 2 <= MAX_VIEW_FACTOR:
            return True
        else:
            return False

    # ---- スクロール
    def pageup(self):
        evt = wx.ScrollWinEvent(wx.wxEVT_SCROLLWIN_PAGEUP, self.GetId())
        self.GetEventHandler().ProcessEvent(evt)

    def pagedown(self):
        evt = wx.ScrollWinEvent(wx.wxEVT_SCROLLWIN_PAGEDOWN, self.GetId())
        self.GetEventHandler().ProcessEvent(evt)

    #--------------------------------------------------------------------------
    # イベントハンドラ

    @binder(wx.EVT_SCROLLWIN)
    def OnScrollWin(self, evt):
        pos = self.GetScrollPos(wx.HORIZONTAL)
        old_pos = pos

        if evt.EventType == wx.EVT_SCROLLWIN_LINEUP.typeId:
            pos = pos - 1
        elif evt.EventType == wx.EVT_SCROLLWIN_LINEDOWN.typeId:
            pos = pos + 1
        elif evt.EventType == wx.EVT_SCROLLWIN_PAGEUP.typeId:
            pos = pos - self.GetScrollPageSize(wx.HORIZONTAL)
        elif evt.EventType == wx.EVT_SCROLLWIN_PAGEDOWN.typeId:
            pos = pos + self.GetScrollPageSize(wx.HORIZONTAL)
        elif evt.EventType == wx.EVT_SCROLLWIN_THUMBTRACK.typeId:
            pos = evt.Position

        pos = max(0, min(pos, self.GetScrollRange(wx.HORIZONTAL)))

        if (old_pos != pos) or (os.name == 'posix'):
            self.SetScrollPos(wx.HORIZONTAL, pos)
            self.UpdateDrawing()

    @binder(wx.EVT_MOUSEWHEEL)
    def OnMouseWheel(self, evt):
        if evt.WheelRotation < 0:
            self.zoom_out(evt.X)
        else:
            self.zoom_in(evt.X)

    @binder(wx.EVT_LEFT_DOWN)
    def OnLeftDown(self, evt):
        self.SetFocus()

        if not self._vol:
            self.post_open_snd_evt()
            return

        # 現在位置を変更
        self.pos_i = self.left_i + evt.X
        self.UpdateDrawing(2)
        self.post_vw_pos_evt()

        # ドラッグでスクロール
        self._ds_x = evt.X
        self._ds_left_i = self.left_i
        self.CaptureMouse()

    @binder(wx.EVT_LEFT_UP)
    def OnLeftUp(self, evt):
        if self.HasCapture():
            self.ReleaseMouse()
            self._ds_x = None
            self._ds_left_i = None

    @binder(wx.EVT_MOTION)
    def OnMotion(self, evt):
        # ドラッグでスクロール
        if self._ds_x is not None and self.HasCapture():
            self.left_i = self._ds_left_i + (self._ds_x - evt.X)

    @binder(wx.EVT_KEY_DOWN)
    def OnKeyDown(self, evt):
        if self._vol is None:
            return

        key = evt.GetKeyCode()

        if key == wx.WXK_SPACE:
            if self.playing:
                self.post_pause_evt()
            else:
                self.post_play_evt()
        elif key == wx.WXK_NUMPAD_ADD:
            self.zoom_in()
        elif key == wx.WXK_NUMPAD_SUBTRACT:
            self.zoom_out()
        elif key == wx.WXK_PAGEUP:
            if self.playing:
                return

            self.pageup()
        elif key == wx.WXK_PAGEDOWN:
            if self.playing:
                return

            self.pagedown()
        elif key == wx.WXK_HOME:
            self.pos_f = 0
            self.post_vw_pos_evt()
        elif key == wx.WXK_END:
            if self.playing:
                return

            pos = self.GetScrollRange(wx.HORIZONTAL)
            self.SetScrollPos(wx.HORIZONTAL, pos)
            self.UpdateDrawing()
        elif key == wx.WXK_UP:
            self.scale -= 1
        elif key == wx.WXK_DOWN:
            self.scale += 1
        elif key == wx.WXK_LEFT or key == wx.WXK_RIGHT:
            if self.playing:
                return

            seek_s = 0

            if evt.ControlDown():
                seek_s = SEEK_CTRL_S
            elif evt.ShiftDown():
                seek_s = SEEK_SHIFT_S
            else:
                seek_s = SEEK_S

            if seek_s != 0:
                if key == wx.WXK_LEFT:
                    self.pos_s -= seek_s
                else:
                    self.pos_s += seek_s

                self.post_vw_pos_evt()

    #--------------------------------------------------------------------------
    # プロパティ

    # ---- 再生中か？

    @property
    def playing(self):
        return self._playing

    @playing.setter
    def playing(self, is_playing):
        self._playing = is_playing

    # ---- 表示範囲

    @property
    def scale(self):
        return self._scale

    @scale.setter
    def scale(self, scale):
        scale = max(MIN_SCALE, min(scale, 100))

        if self._scale == scale:
            return scale

        self._scale = scale

        self.UpdateDrawing()

        self.post_scale_change_evt()

    # ---- 拡大率

    def get_view_factor(self):
        return self._view_factor

    def set_view_factor(self, view_factor, x=0):
        '''
        @param x この X 座標を中心として拡大・縮小する
        '''

        view_factor = max(1, min(view_factor, MAX_VIEW_FACTOR))

        if self._view_factor == view_factor:
            return

        if self._vol is None:
            self._view_factor = view_factor
            return

        left_i = self.get_new_left_i(self._view_factor, view_factor, x)

        self._view_factor = view_factor

        rate = self._vol.base_rate / self._view_factor
        self._vol.change_rate(rate)

        self.update_scroll(left_i)

    # set_view_factor は関数としても使うので
    # この方法でプロパティをつくる
    view_factor = property(get_view_factor, set_view_factor)

    # ---- 左位置（インデックス）

    @property
    def left_i(self):
        return self.GetScrollPos(wx.HORIZONTAL) * PPU

    @left_i.setter
    def left_i(self, left_i):
        if self._vol is None:
            return

        old_pos = self.GetScrollPos(wx.HORIZONTAL)

        max_left_i = max(0, len(self._vol) - self.w)
        left_i = max(0, min(left_i, max_left_i))
        new_pos = max(0, left_i / PPU)

        if old_pos != new_pos:
            self.SetScrollPos(wx.HORIZONTAL, new_pos)
            self.UpdateDrawing()

    # ---- 左位置（秒）

    @property
    def left_s(self):
        return self.i_to_s(self.left_i)

    @left_s.setter
    def left_s(self, left_s):
        self.left_i = self.s_to_i(left_s)

    # ---- 現在位置（フレーム）

    @property
    def pos_f(self):
        return self._pos_f

    @pos_f.setter
    def pos_f(self, pos_f):
        if self._vol is None:
            return 0

        left_i = self.left_i
        old_x = self._pos_f - left_i

        self._pos_f = max(0, min(int(pos_f), self._vol.max_f))

        # 現在位置が画面外だったら画面内になるようにする
        pos_i = self.pos_i
        if (pos_i < left_i) or (left_i + self.w < pos_i):
            self.left_i = pos_i
            return

        self.DrawCurPos(True)

    # ---- 現在位置（インデックス）

    @property
    def pos_i(self):
        return self.f_to_i(self._pos_f)

    @pos_i.setter
    def pos_i(self, pos_i):
        self.pos_f = self.i_to_f(pos_i)

    # ---- 現在位置（秒）

    @property
    def pos_s(self):
        return self.f_to_s(self._pos_f)

    @pos_s.setter
    def pos_s(self, pos_s):
        self.pos_f = self.s_to_f(pos_s)

    #--------------------------------------------------------------------------
    # 内部メソッド

    def update_scroll(self, new_left_i=0):
        vol = self._vol or []

        no_units = math.ceil(float(len(vol)) / PPU)
        self.SetScrollbars(PPU, 0, no_units, 0)

        pos = math.ceil(float(new_left_i) / PPU)
        self.SetScrollPos(wx.HORIZONTAL, pos)

        self.UpdateDrawing()

    def get_new_left_i(self, old_view_factor, new_view_factor, x):
        old_rate = self._vol.base_rate / old_view_factor
        new_rate = self._vol.base_rate / new_view_factor

        old_i = self.left_i + x
        s = float(old_i) / old_rate
        new_i = int(s * new_rate)

        return new_i - x

    # ---- イベント

    def post_open_snd_evt(self):
        evt = VolumeWindowEvent(myEVT_OPEN_SND, self.GetId())
        self.GetEventHandler().ProcessEvent(evt)

    def post_vw_pos_evt(self):
        evt = VolumeWindowEvent(myEVT_VW_POS_CHANGE, self.GetId())
        evt.SetPos(self.pos_f)
        self.GetEventHandler().ProcessEvent(evt)

    def post_pause_evt(self):
        evt = VolumeWindowEvent(myEVT_REQ_PAUSE, self.GetId())
        self.GetEventHandler().ProcessEvent(evt)

    def post_play_evt(self):
        evt = VolumeWindowEvent(myEVT_REQ_PLAY, self.GetId())
        self.GetEventHandler().ProcessEvent(evt)

    def post_scale_change_evt(self):
        evt = VolumeWindowEvent(myEVT_SCALE_CHANGE, self.GetId(), self.scale)
        self.GetEventHandler().ProcessEvent(evt)


#------------------------------------------------------------------------------
# イベント
#------------------------------------------------------------------------------

# ---- イベントタイプ
myEVT_OPEN_SND = wx.NewEventType()
myEVT_VW_POS_CHANGE = wx.NewEventType()
myEVT_REQ_PAUSE = wx.NewEventType()
myEVT_REQ_PLAY = wx.NewEventType()
myEVT_SCALE_CHANGE = wx.NewEventType()

# ---- イベントバインダ
EVT_OPEN_SND = wx.PyEventBinder(myEVT_OPEN_SND, 1)
EVT_VW_POS_CHANGE = wx.PyEventBinder(myEVT_VW_POS_CHANGE, 1)
EVT_REQ_PAUSE = wx.PyEventBinder(myEVT_REQ_PAUSE, 1)
EVT_REQ_PLAY = wx.PyEventBinder(myEVT_REQ_PLAY, 1)
EVT_SCALE_CHANGE = wx.PyEventBinder(myEVT_SCALE_CHANGE, 1)


class VolumeWindowEvent(wx.PyCommandEvent):
    def __init__(self, event_type, id, pos_f=0):
        wx.PyCommandEvent.__init__(self, event_type, id)
        self.SetPos(pos_f)

    def GetPos(self):
        return self.pos_f

    def SetPos(self, pos_f):
        self.pos_f = pos_f


if __name__ == '__main__':
    import pausewave
    from volume import Volume

    def sec_to_str(sec):
        m = sec / 60
        s = int(sec) % 60
        ms = int(sec * 1000) % 1000

        time_str = '%01d:%02d.%03d' % (m, s, ms)

        return time_str

    class MyFrame(wx.Frame):
        def __init__(self):
            wx.Frame.__init__(self, None)

            wav = pausewave.open('in.mp3')
            vol = Volume(wav)

            win = VolumeWindow(parent=self, id=-1)
            self.statusbar = self.CreateStatusBar()
            self.Bind(EVT_VW_POS_CHANGE, self.OnVwPosChange)
            self.Bind(EVT_REQ_PLAY, self.OnReqPlay)
            self.Bind(EVT_REQ_PAUSE, self.OnReqPause)
            win.SetVolume(vol)
            self.win = win

        def OnVwPosChange(self, event):
            pos_s = self.win.f_to_s(event.GetPos())
            time_str = sec_to_str(pos_s)
            self.statusbar.SetStatusText(time_str)

        def OnReqPlay(self, event):
            print 'play'

        def OnReqPause(self, event):
            print 'pause'

    app = wx.PySimpleApp()
    frame = MyFrame()
    frame.Show(True)
    app.MainLoop()
