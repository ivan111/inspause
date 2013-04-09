# -*- coding: utf-8 -*-
'''
ボリューム表示
'''

import math
import os

import wx
import wx_utils

from mywave import FIND_RATE


EVT_CLICK_CUR_CHANGED_ID = wx.NewId()

USE_BUFFERED_DC = True

SCALE = 100  # 波形の下から何％を表示するか
MIN_SCALE = 3
MAX_VIEW_FACTOR = 4
VIEW_FACTOR = MAX_VIEW_FACTOR / 2  # これで拡大率が決まる。表示レート = FIND_RATE / (1 << VIEW_FACTOR)
PPU = 20  # Pixels Per Unit

# 矢印キーの移動量
SEEK_S       = 0.002
SEEK_CTRL_S  = 0.02
SEEK_SHIFT_F = 1

NO_WAV_MESSAGE1 = u'音声がありません'
NO_WAV_MESSAGE2 = u'ここをクリックしてください'


# http://wiki.wxpython.org/DoubleBufferedDrawing
class VolumeWindow(wx.ScrolledWindow):
    '''
    ボリューム表示ウィンドウ
    '''

    binder = wx_utils.bind_manager()

    def __init__(self, *args, **kwargs):
        kwargs['style'] = kwargs.setdefault('style', 0) | wx.NO_FULL_REPAINT_ON_RESIZE
        wx.ScrolledWindow.__init__(self, *args, **kwargs)

        self._init_instance_var_vw()

        self.binder.bindall(self)

        self.OnSize(None)


    # オーバーライドされて変な動作しないように
    # 後ろに _vm をつけたよ
    def _init_instance_var_vw(self):
        self._max_val = 0  # 表示することができるボリュームの最大値
                      # これを超えるボリュームは頭の部分が途中で切れる

        self.max_f = 0
        self.max_s = 0

        self.rate = FIND_RATE

        self.num_update_draw_base = 0

        self._playing = False

        self.brush_text_bg = wx.Brush(wx.Colour(255, 255, 255, 128))

        # draw_base で更新された場合 True
        self.draw_base_changed = False

        # _buffer_base を更新するか決めるための変数
        self.prev_left_f = -1
        self.prev_vol = None
        self.prev_w = 0
        self.prev_h = 0
        self.prev_scale = 0

        # ドラッグスクロール関連
        self._drag_scroll = False
        self._drag_scroll_left_f = 0

        # 以下が True のときは、スクロールイベントを無視
        self._size_changed = False
        self._view_factor_changed = False

        # 画面サイズ
        self.w = 0  # 幅
        self.h = 0  # 高さ

        # ---- プロパティ用
        self._wav = None
        self._vol = None
        self._scale = SCALE
        self._view_factor = VIEW_FACTOR
        self._cur_s = 0
        self._brush_bg = wx.BLACK_BRUSH
        self._pen_fg = wx.BLACK_PEN


    def sec_to_str(self, sec):
        m  = sec / 60
        s  = int(sec) % 60
        ms = int(sec * 1000) % 1000

        time_str = '%01d:%02d.%03d' % (m, s, ms)

        return time_str


    #--------------------------------------------------------------------------
    # 描画

    def update_drawing(self, update_base=False):
        '''
        画面の更新。
        ソフトウェア内で画面の更新が必要がになった場合は、このメソッドを呼ぶ。
        '''

        dc = wx.MemoryDC()
        dc.SelectObject(self._buffer_base)
        self.draw_base(dc, update_base)

        del dc

        dc = wx.MemoryDC()
        dc.SelectObject(self._buffer)
        self.draw(dc)

        del dc  # Update() が呼ばれる前に MemoryDC を解放する必要がある

        self.Refresh(eraseBackground=False)
        self.Update()

    def draw_base(self, dc, update_base):
        '''
        波形やラベルなど頻繁に変わらない部分を描く。
        draw はこれをもとに描く。
        '''

        # なるべく更新しない努力をしてます
        if not update_base and self.left_f == self.prev_left_f and \
                self.vol is self.prev_vol and self.w == self.prev_w and \
                self.h == self.prev_h and self.scale == self.prev_scale:
            self.draw_base_changed = False
            return

        self.prev_left_f = self.left_f
        self.prev_vol    = self.vol
        self.prev_w      = self.w
        self.prev_h      = self.h
        self.prev_scale  = self.scale

        self.draw_base_changed = True

        self.num_update_draw_base += 1

        dc.SetBackground(self._brush_bg)
        dc.Clear()

        if self.vol:
            self._draw_volume(dc)
            self._draw_out_of_area(dc)
        else:
            self._draw_message(dc)


    def draw(self, dc):
        dc.DrawBitmap(self._buffer_base, 0, 0)

        dc = wx.GCDC(dc)

        if self.vol:
            self._draw_cur_position(dc)

            # 現在位置の時間を表示
            time_str = self.sec_to_str(self.cur_s)
            cw, ch = dc.GetTextExtent(time_str)

            dc.SetPen(wx.TRANSPARENT_PEN)
            dc.SetBrush(self.brush_text_bg)
            dc.DrawRectangle(8, 3, cw + 4, ch + 4)

            dc.DrawText(time_str, 10, 5)


    def _draw_volume(self, dc):
        '''
        ボリュームを描画
        '''

        if self.max_val == 0:
            return

        w, h = dc.Size

        dc.SetPen(self._pen_fg)

        for x in range(w):
            i = self.left_f + x
            if self.max_f < i:
                break
            v = h * float(self.vol[i]) / self.max_val
            v = min(v, h)
            dc.DrawLine(x, h, x, h - v)


    def _draw_out_of_area(self, dc):
        '''
        波形が画面より小さいときに、波形以外の部分を表示する
        '''

        w, h = dc.Size

        max_x = self.max_f - self.left_f
        if max_x < w:
            dc.SetPen(wx.TRANSPARENT_PEN)
            dc.SetBrush(wx.Brush('#D3D3D3'))

            dc.DrawRectangle(max_x, 0, w, h)


    def _draw_message(self, dc):
        '''
        波形がないときのメッセージを描画
        '''

        w, h = dc.Size

        old_color = dc.GetTextForeground()
        bg = self._brush_bg.Colour
        new_color = wx.Colour(~bg.Red() & 0xFF, ~bg.Green() & 0xFF, ~bg.Blue() & 0xFF)  # ビット反転した色
        dc.SetTextForeground(new_color)

        cw, ch = dc.GetTextExtent(NO_WAV_MESSAGE1)
        x = (w - cw) / 2
        y = h / 2 - ch
        dc.DrawText(NO_WAV_MESSAGE1, x, y)

        cw, ch = dc.GetTextExtent(NO_WAV_MESSAGE2)
        x = (w - cw) / 2
        y = h / 2
        dc.DrawText(NO_WAV_MESSAGE2, x, y)

        dc.SetTextForeground(old_color)


    def _draw_cur_position(self, dc):
        w, h = dc.Size

        dc.SetPen(wx.Pen('#FF0000'))
        cur_f = self.cur_f - self.left_f
        dc.DrawLine(cur_f, 0, cur_f, h)


    #--------------------------------------------------------------------------
    # コマンド

    # ---- シーク

    def head(self):
        if not self.can_head():
            return

        self.cur_f  = 0
        self.left_f = 0

    def can_head(self):
        if self.vol and self.cur_f != 0:
            return True
        else:
            return False

    def tail(self):
        if not self.can_tail():
            return

        self.cur_f = self.max_f
        self.left_f = self.max_f

    def can_tail(self):
        if self.vol and self.cur_f != self.max_f:
            return True
        else:
            return False


    # ---- 拡大・縮小

    def zoom_in(self, x=0):
        if not self.can_zoomin():
            return

        self.set_view_factor(self.view_factor - 1, x)

    def can_zoomin(self):
        if self.vol is None:
            return False

        return self.view_factor - 1 >= 0

    def zoom_out(self, x=0):
        if not self.can_zoomout():
            return

        self.set_view_factor(self.view_factor + 1, x)

    def can_zoomout(self):
        if self.vol is None:
            return False

        return self.view_factor + 1 <= MAX_VIEW_FACTOR


    # ---- スクロール

    def pageup(self):
        pos = self.GetScrollPos(wx.HORIZONTAL)
        old_pos = pos

        pos -= self.GetScrollPageSize(wx.HORIZONTAL)
        pos = max(0, min(pos, self.GetScrollRange(wx.HORIZONTAL)))

        if old_pos != pos:
            self.SetScrollPos(wx.HORIZONTAL, pos)
            self.update_drawing()

    def pagedown(self):
        pos = self.GetScrollPos(wx.HORIZONTAL)
        old_pos = pos

        pos += self.GetScrollPageSize(wx.HORIZONTAL)
        pos = max(0, min(pos, self.GetScrollRange(wx.HORIZONTAL)))

        if old_pos != pos:
            self.SetScrollPos(wx.HORIZONTAL, pos)
            self.update_drawing()


    #--------------------------------------------------------------------------
    # イベントハンドラ

    @binder(wx.EVT_SIZE)
    def OnSize(self, evt):
        self._size_changed = True

        size = self.ClientSize
        self.w = size[0]
        self.h = size[1]

        if self.prev_w != self.w or self.prev_h != self.h:
            self._buffer = wx.EmptyBitmap(*size)
            # 波形やラベルなど頻繁に変わらない部分
            self._buffer_base = wx.EmptyBitmap(*size)

        self.update_drawing()


    @binder(wx.EVT_PAINT)
    def OnPaint(self, evt):
        if USE_BUFFERED_DC:
            dc = wx.BufferedPaintDC(self, self._buffer)
        else:
            dc = wx.PaintDC(self)
            dc.DrawBitmap(self._buffer, 0, 0)


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
            self.track = True
            pos = evt.Position
        elif evt.EventType == wx.EVT_SCROLLWIN_THUMBRELEASE.typeId:
            if self._size_changed:
                self._size_changed = False
                evt.Skip()

            if self._view_factor_changed:
                self._view_factor_changed = False
                evt.Skip()

        pos = max(0, min(pos, self.GetScrollRange(wx.HORIZONTAL)))

        if (old_pos != pos) or (os.name == 'posix'):
            self.SetScrollPos(wx.HORIZONTAL, pos)
            self.update_drawing()


    @binder(wx.EVT_MOUSEWHEEL)
    def OnMouseWheel(self, evt):
        if evt.WheelRotation < 0:
            self.zoom_out(evt.X)
        else:
            self.zoom_in(evt.X)


    @binder(wx.EVT_LEFT_DOWN)
    def OnLeftDown(self, evt):
        self.SetFocus()

        if not self.vol:
            return

        # 現在位置を変更
        self.cur_f = self.left_f + evt.X
        wx.PostEvent(self.Parent, ClickCurChangedEvent(self.cur_s))

        # ドラッグでスクロール
        self._drag_scroll = evt.X
        self._drag_scroll_left_f = self.left_f
        self.CaptureMouse()

        self.update_drawing()


    @binder(wx.EVT_LEFT_UP)
    def OnLeftUp(self, evt):
        if self._drag_scroll:
            self.ReleaseMouse()

        self._drag_scroll = False


    @binder(wx.EVT_MOTION)
    def OnMotion(self, evt):
        if self.vol is None:
            return

        # ドラッグでスクロール
        if self._drag_scroll:
            self.left_f = self._drag_scroll_left_f + (self._drag_scroll - evt.X)
            self.update_drawing()


    @binder(wx.EVT_MOUSE_CAPTURE_LOST)
    def OnCaptureLost(self, evt):
        if self._drag_scroll:
            self.ReleaseMouse()
            self._drag_scroll = False


    @binder(wx.EVT_KEY_DOWN)
    def OnKeyDown(self, evt):
        if self.vol is None:
            return

        key = evt.GetKeyCode()

        if key == wx.WXK_NUMPAD_ADD:
            self.zoom_in()
        elif key == wx.WXK_NUMPAD_SUBTRACT:
            self.zoom_out()
        elif key == wx.WXK_PAGEUP:
            self.pageup()
        elif key == wx.WXK_PAGEDOWN:
            self.pagedown()
        elif key == wx.WXK_HOME:
            self.head()
        elif key == wx.WXK_END:
            self.tail()
        elif key == wx.WXK_LEFT or key == wx.WXK_RIGHT:
            if self.vol:
                seek_s = 0

                if evt.ControlDown():
                    seek_s = SEEK_CTRL_S
                elif evt.ShiftDown():
                    seek_s = self.f_to_s(SEEK_SHIFT_F)
                else:
                    seek_s = SEEK_S

                if seek_s != 0:
                    if key == wx.WXK_LEFT:
                        self.cur_s -= seek_s
                    else:
                        self.cur_s += seek_s

                    wx.PostEvent(self.Parent, ClickCurChangedEvent(self.cur_s))


    #--------------------------------------------------------------------------
    # プロパティ

    # ---- 音声

    @property
    def wav(self):
        return self._wav

    @wav.setter
    def wav(self, wav):
        self._wav = wav
        self._cur_s = 0
        self.view_factor = self._view_factor
        self.left_f = 0

        if wav is None:
            self.SetScrollbars(PPU, 0, 0, 0)
            self.update_drawing()


    # ---- 現在の拡大率に合ったボリュームデータ

    @property
    def vol(self):
        return self._vol

    @vol.setter
    def vol(self, vol):
        self._vol = vol
        self.max_f = len(vol) - 1
        self.max_s = self.f_to_s(self.max_f)
        self.scale = self._scale  # ここで画面が更新される
        self.SetScrollbars(PPU, 0, math.ceil(float(self.max_f) / PPU), 0)


    # ---- 表示範囲

    @property
    def scale(self):
        return self._scale

    @scale.setter
    def scale(self, scale):
        self._scale = max(MIN_SCALE, min(scale, 100))

        if not self.vol:
            return

        percent = self._scale / 100.0
        self.max_val = max(self.vol) * percent
        self.update_drawing()


    # ---- 拡大率

    def get_view_factor(self):
        return self._view_factor

    def set_view_factor(self, view_factor, x=0):
        '''
        @param x この X 座標を中心として拡大・縮小する
        '''

        if x == 0:
            prev_left_s = self.left_s
        else:
            x = max(0, min(x, self.w))
            x_s = self.f_to_s(self.left_f + x)

        view_factor = max(0, min(view_factor, MAX_VIEW_FACTOR))

        self._view_factor = view_factor

        self._view_factor_changed = True

        self.rate = FIND_RATE / (1 << view_factor)

        if not self.wav:
            self._vol = None
            return

        self.vol = self.wav.calc_volume(view_factor)

        if x == 0:
            self.left_s = prev_left_s
        else:
            self.left_f = self.s_to_f(x_s) - x

    view_factor = property(get_view_factor, set_view_factor)


    # ---- 左位置（フレーム）

    @property
    def left_f(self):
        return self.GetScrollPos(wx.HORIZONTAL) * PPU

    @left_f.setter
    def left_f(self, left_f):
        if self.wav is None:
            return

        max_left_f = max(0, self.max_f - self.w)
        left_f = max(0, min(left_f, max_left_f))
        pos = max(0, math.ceil(float(left_f) / PPU))

        self.SetScrollPos(wx.HORIZONTAL, pos)

        self.update_drawing()


    # ---- 左位置（秒）

    @property
    def left_s(self):
        return self.f_to_s(self.left_f)

    @left_s.setter
    def left_s(self, left_s):
        self.left_f = self.s_to_f(left_s)


    # ---- 現在位置（フレーム）

    @property
    def cur_f(self):
        return self.s_to_f(self.cur_s)

    @cur_f.setter
    def cur_f(self, cur_f):
        self.cur_s = self.f_to_s(cur_f)


    # ---- 現在位置（秒）

    @property
    def cur_s(self):
        return self._cur_s

    @cur_s.setter
    def cur_s(self, cur_s):
        self._cur_s = max(0, min(cur_s, self.max_s))

        cur_f = self.cur_f
        if (cur_f < self.left_f) or (self.left_f + self.w < cur_f):
            self.left_f = cur_f

        self.update_drawing()


    # ---- 再生中か？

    @property
    def playing(self):
        return self._playing

    @playing.setter
    def playing(self, is_playing):
        self._playing = is_playing


    # ---- 背景色

    @property
    def bg_color(self):
        bg = self._brush_bg.Colour
        return '#%02X%02X%02X' % (bg.Red(), bg.Green(), bg.Blue())

    @bg_color.setter
    def bg_color(self, color):
        self._brush_bg = wx.Brush(color)
        self.update_drawing(True)


    # ---- 前景色

    @property
    def fg_color(self):
        fg = self._pen_fg.Colour
        return '#%02X%02X%02X' % (fg.Red(), fg.Green(), fg.Blue())

    @fg_color.setter
    def fg_color(self, color):
        self._pen_fg = wx.Pen(color)
        self.update_drawing(True)


    def f_to_s(self, f):
        return float(f) / self.rate

    def s_to_f(self, s):
        return int(s * self.rate)


class ClickCurChangedEvent(wx.PyEvent):
    def __init__(self, cur_s):
        wx.PyEvent.__init__(self)
        self.SetEventType(EVT_CLICK_CUR_CHANGED_ID)
        self.cur_s = cur_s



if __name__ == '__main__':
    from mywave import MyWave

    def main():
        app = TestVolumeWindow(redirect=True, filename='log_volumewindow.txt')
        app.MainLoop()

    class TestVolumeWindow(wx.App):
        def OnInit(self):
            frame = wx.Frame(None, -1, 'TestVolumeWindow')
            panel = wx.Panel(frame)

            layout = wx.BoxSizer(wx.HORIZONTAL)
            panel.SetSizer(layout)

            window = VolumeWindow(panel)
            wav = MyWave('in.wav', '001.txt')
            window.wav = wav
            layout.Add(window, proportion=1, flag=wx.EXPAND)

            frame.Centre()
            frame.Show()

            return True

    main()
