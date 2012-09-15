# -*- coding: utf-8 -*-

import audioop
import copy
import math
import os
import wave

import wx

from findsound import find_sound, rms_ratecv, WAV_SCALE, DEFAULT_SIL_LV
from labels import Labels, LBL_PAUSE, LBL_CUT
from waveplayer import WavePlayer, EVT_UPDATE_ID, EVT_EOF_ID, EOFEvent

DEBUG = False

USE_BUFFERED_DC = True
EVT_CHANGE_CUR_ID = wx.NewId()
WAV_TOP = 30
ARROW_SIZE = 5
MIN_RATE = 12
MAX_RATE = 384
DEFAULT_RATE = 96
PPU = 20 # Pixels Per Unit
INSERT_DUR = 0.5

NO_HANDLE = 0
LEFT_HANDLE = 1
RIGHT_HANDLE = 2

ID_PAUSE = wx.NewId()
ID_CUT = wx.NewId()

class ChangeCurEvent(wx.PyEvent):
    def __init__(self):
        wx.PyEvent.__init__(self)
        self.SetEventType(EVT_CHANGE_CUR_ID)


class MyPopupMenu(wx.Menu):
    def __init__(self, parent):
        super(MyPopupMenu, self).__init__()
        
        self.parent = parent
        label = parent.ml().selected

        if label.label == LBL_PAUSE:
            cmi = wx.MenuItem(self, ID_CUT, u'ポーズ音声作成時に選択範囲をカット')
            self.AppendItem(cmi)
            self.Bind(wx.EVT_MENU, self.OnCut, cmi)
        elif label.label == LBL_CUT:
            pmi = wx.MenuItem(self, ID_PAUSE, u'ポーズ音声作成時に選択範囲をポーズ挿入')
            self.AppendItem(pmi)
            self.Bind(wx.EVT_MENU, self.OnPause, pmi)

    def OnPause(self, e):
        self.parent.ml.save()
        self.parent.ml().selected.label = LBL_PAUSE
        self.parent.UpdateDrawing()

    def OnCut(self, e):
        self.parent.ml.save()
        self.parent.ml().selected.label = LBL_CUT
        self.parent.UpdateDrawing()


# http://wiki.wxpython.org/DoubleBufferedDrawing
class WaveView(wx.ScrolledWindow):
    def __init__(self, *args, **kwargs):
        self.listener = kwargs['listener']
        del kwargs['listener']

        kwargs['style'] = kwargs.setdefault('style', wx.NO_FULL_REPAINT_ON_RESIZE) | wx.NO_FULL_REPAINT_ON_RESIZE
        wx.ScrolledWindow.__init__(self, *args, **kwargs)

        self.max_val = 0
        self._has_focus = False
        self.rate_changed = False
        self.wp = None
        self.ml = None
        self.labels_file = None
        self.drag_handle = NO_HANDLE
        self.draw_handle_active = None
        self.drag_scroll = False

        al = ARROW_SIZE
        self.down_arrow = ((al, 0), (0, al*math.sqrt(3)), (-al, 0))
        self.right_arrow = ((0, al), (al*math.sqrt(3), 0), (0, -al))
        self.left_arrow = ((0, al), (-al*math.sqrt(3), 0), (0, -al))

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_SCROLLWIN, self.OnScrollWin)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_MOTION, self.OnMotion)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.Bind(wx.EVT_SET_FOCUS, self.OnSetFocus)
        self.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        self.Connect(-1, -1, EVT_UPDATE_ID, self.OnUpdate)
        self.Connect(-1, -1, EVT_EOF_ID, self.OnEOF)

        self.OnSize(None)

    def set_sound(self, wav_file):
        if not os.path.exists(wav_file):
            return False

        wf = wave.open(wav_file, 'r')
        buffer = wf.readframes(wf.getnframes())
 
        self.wav_file = wav_file
        self.nchannels = 1 # if nchannels == 2, convert it to mono
        self.sampwidth = wf.getsampwidth()
        self.src_rate = wf.getframerate()
        self.nframes = len(buffer) / (self.nchannels * self.sampwidth)

        if wf.getsampwidth() != 2:
            wx.MessageBox(u'サンプルサイズは16ビットでないといけません。（このファイル：%dビット）' % (wf.getsampwidth() * 8))
            return False

        if wf.getnchannels() == 2:
            buffer = audioop.tomono(buffer, self.sampwidth, 0.5, 0.5)
        self.buffer = buffer

        self.rate = DEFAULT_RATE

        if self.wp:
            self.wp.cancel = True
            self.wp.join()

        self.wp = WavePlayer(self, buffer, self.nchannels, self.sampwidth, self.src_rate)
        self.wp.start()

        self.labels_file = None
        self.ml = None
        self.cur_f = 0

        return True

    def set_labels(self, labels_file):
        self.labels_file = labels_file
        labels = Labels(open(labels_file, 'r').readlines())
        self.ml = MyLabels(labels)
        self.UpdateDrawing()

    def UpdateDrawing(self):
        dc = wx.MemoryDC()
        dc.SelectObject(self._Buffer)
        self.Draw(dc)
        del dc # need to get rid of the MemoryDC before Update() is called.
        self.Refresh(eraseBackground=False)
        self.Update()

    #--------------------------------------------------------------------------
    # Draw
    #--------------------------------------------------------------------------

    def Draw(self, dc):
        dc.SetBackground(wx.WHITE_BRUSH)
        dc.Clear()

        if self.data:
            self._draw_wave(dc)
            self._draw_thres(dc)
            self._draw_labels(dc)
            self._draw_handle_active(dc)
            self._draw_top_line(dc)
            self._draw_out_of_area(dc)
            self._draw_playing_position(dc)
            self._draw_focus(dc)

        if DEBUG:
            # Left Frame
            # Scroll Pos
            dc.SetPen(wx.BLACK_PEN)
            dc.DrawText('%d' % self.left_f, 0, 0)
            dc.DrawText('%d' % self.GetScrollPos(wx.HORIZONTAL), 0, 15)

    def _draw_focus(self, dc):
        if self._has_focus:
            w, h = dc.Size
            dc.SetPen(wx.Pen('#4C4C4C', 1, wx.DOT))
            dc.SetBrush(wx.TRANSPARENT_BRUSH)
            dc.DrawRectangle(0, 0, w, h)

    def _draw_wave(self, dc):
        w, h = dc.Size

        dc.SetPen(wx.Pen('#4876FF')) 

        for x in range(w):
            f = self.left_f + x
            if self.max_f < f:
                break
            vol = (h-WAV_TOP) * float(self.data[f]) / self.max_val
            vol = min(vol, h - WAV_TOP)
            dc.DrawLine(x, h, x, h - vol) 

    def _draw_thres(self, dc):
        w, h = dc.Size
        w = min(w, self.max_f)

        y = (h-WAV_TOP) * self.thres / self.max_val
        y = min(y, h - WAV_TOP)

        dc.SetPen(wx.RED_PEN)
        dc.DrawLine(0, h - y, w, h - y)

    def _draw_top_line(self, dc):
        w, h = dc.Size
        w = min(w, self.max_f)

        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.SetBrush(wx.Brush('#EEFFFF'))
        dc.DrawRectangle(0, 0, w, WAV_TOP)

        dc.SetPen(wx.BLACK_PEN)
        dc.DrawLine(0, WAV_TOP, w, WAV_TOP)

    def _draw_labels(self, dc):
        if self.ml is None:
            return

        w, h = dc.Size

        rects_p = []
        rects_x = []

        for label in self.ml():
            st_f = label.start * self.rate
            ed_f = label.end * self.rate

            if (self.left_f <= st_f) and (st_f <= self.left_f + w):
                st_in_range = True
            else:
                st_in_range = False

            if (self.left_f <= ed_f) and (ed_f <= self.left_f + w):
                ed_in_range = True
            else:
                ed_in_range = False

            st = st_f - self.left_f
            ed = ed_f - self.left_f

            if self.ml().selected is label:
                selected = True
            else:
                selected = False

            rect = None
            sel_rect = None
            arrows = []

            rect = None
            if st_in_range and ed_in_range:
                rect = [st, WAV_TOP, ed - st, h - WAV_TOP]
                if selected:
                    arrows.append([[x + st, y + self.st_arrow_y] for x, y in self.right_arrow])
                    arrows.append([[x + ed-1, y + self.ed_arrow_y] for x, y in self.left_arrow])
            elif st_in_range and ed_in_range == False:
                rect = [st, WAV_TOP, w - st, h - WAV_TOP]
                if selected:
                    arrows.append([[x + st, y + self.st_arrow_y] for x, y in self.right_arrow])
            elif st_in_range == False and ed_in_range:
                rect = [0, WAV_TOP, ed, h - WAV_TOP]
                if selected:
                    arrows.append([[x + ed-1, y + self.ed_arrow_y] for x, y in self.left_arrow])
            elif (st_f < self.left_f) and (self.left_f + w < ed_f):
                rect = [0, WAV_TOP, w, h - WAV_TOP]
            
            if rect:
                if selected and (not self.playing):
                    if label.label == LBL_CUT:
                        lf = dc.GetLogicalFunction()
                        dc.SetLogicalFunction(wx.XOR)
                        dc.DrawRectangleList([rect], wx.WHITE_PEN, wx.Brush('#BBBBBB'))
                        dc.SetLogicalFunction(lf)
                    else:
                        lf = dc.GetLogicalFunction()
                        dc.SetLogicalFunction(wx.XOR)
                        dc.DrawRectangleList([rect], wx.WHITE_PEN, wx.Brush('#555555'))
                        dc.SetLogicalFunction(lf)

                    if arrows:
                        dc.DrawPolygonList(arrows, wx.BLACK_PEN, wx.Brush('#20B2AA'))
                else:
                    if label.label == LBL_CUT:
                        rects_x.append(rect)
                    else:
                        rects_p.append(rect)

        if rects_p:
            self._draw_rects(dc, rects_p, '#333333')

        if rects_x:
            self._draw_rects(dc, rects_x, '#999999')

    def _draw_handle_active(self, dc):
        if self.playing or (self.draw_handle_active is None):
            return

        left, right = self.draw_handle_active

        dc.SetPen(wx.Pen('#000000', 1, wx.DOT))
        dc.SetBrush(wx.TRANSPARENT_BRUSH)

        if left:
            dc.DrawEllipticArc(left['x'] - self.handle_dist, left['y'] - self.handle_dist, self.handle_dist * 2, self.handle_dist * 2, -90, 90)
        elif right:
            dc.DrawEllipticArc(right['x'] - self.handle_dist, right['y'] - self.handle_dist, self.handle_dist * 2, self.handle_dist * 2, 90, 270)

    def _draw_rects(self, dc, rects, brush_color):
        prev_region = None
        for rect in rects:
            region = wx.Region(*rect)
            if prev_region:
                region.UnionRegion(prev_region)
            prev_region = region

        dc.SetClippingRegionAsRegion(region)
        rect = region.GetBox()

        lf = dc.GetLogicalFunction()
        dc.SetLogicalFunction(wx.XOR)
        dc.SetPen(wx.WHITE_PEN)
        dc.SetBrush(wx.Brush(brush_color))
        dc.DrawRectangleRect(rect)
        dc.SetLogicalFunction(lf)
        dc.DestroyClippingRegion()

        dc.SetPen(wx.BLACK_PEN)
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        for rect in rects:
            dc.DrawRectangleRect(rect)

    def _draw_out_of_area(self, dc):
        w, h = dc.Size

        max_x = self.max_f - self.left_f
        if max_x < w:
            dc.SetPen(wx.TRANSPARENT_PEN)
            dc.SetBrush(wx.Brush('#D3D3D3'))

            dc.DrawRectangle(max_x, 0, w, h)

    def _draw_playing_position(self, dc):
        w, h = dc.Size

        dc.SetPen(wx.Pen('#FF0000'))
        dc.SetBrush(wx.Brush('#FF0000'))
        cur_f = self.cur_f - self.left_f
        dc.DrawLine(cur_f, 0, cur_f, h)
        dc.DrawPolygon(self.down_arrow, cur_f, 0)

    #--------------------------------------------------------------------------
    # Command
    #--------------------------------------------------------------------------

    def cancel(self):
        if self.wp:
            self.wp.cancel = True
            self.wp.join()

    def save(self):
        if not self.can_save():
            return

        self.ml().write(self.labels_file)
        self.ml.clear_history()

    def can_save(self):
        if self.labels_file and self.can_undo():
            return True
        else:
            return False

    def find(self, sil_lv, sil_dur, before_label_dur, after_label_dur):
        if not self.wp:
            return

        labels = find_sound(self.wav_file, sil_lv, sil_dur, before_label_dur, after_label_dur)

        if self.ml is None:
            self.ml = MyLabels(labels)
        else:
            self.ml.save()
            self.ml.set_labels(labels)

        self.UpdateDrawing()

    def head(self):
        if not self.can_head():
            return

        self.cur_f = 0
        self.wp.cur_f = 0
        self.left_f = 0
        self.UpdateDrawing()

    def can_head(self):
        if self.wp and self.cur_f != 0:
            return True
        else:
            return False

    def play(self):
        if not self.can_play():
            return

        self.wp.play()

    def can_play(self):
        if self.wp and self.wp.can_play():
            return True
        else:
            return False

    def pause_mode_play(self, factor, add):
        if not self.can_pause_mode_play():
            return

        self.wp.pause_mode_play(self.ml(), factor, add)

    def can_pause_mode_play(self):
        if self.wp and self.wp.can_play():
            return True
        else:
            return False

    def playsel(self):
        if not self.can_playsel():
            return

        self.wp.play_label(self.ml().selected)

    def can_playsel(self):
        if self.wp and self.wp.can_play() and self.ml and self.ml().selected:
            return True
        else:
            return False

    def play_border(self):
        if not self.can_play_border():
            return

        self.wp.play_border(self.ml().selected.end)

    def can_play_border(self):
        if self.wp and self.wp.can_play() and self.ml and self.ml().selected:
            return True
        else:
            return False

    def pause(self):
        if not self.can_pause():
            return

        self.wp.playing = False
        self.UpdateDrawing()

    def can_pause(self):
        if self.wp and self.playing:
            return True
        else:
            return False

    def tail(self):
        if not self.can_tail():
            return

        self.cur_f = self.max_f
        self.wp.cur_f = self.nframes
        self.left_f = self.max_f
        self.UpdateDrawing()

    def can_tail(self):
        if self.wp and self.cur_f != self.max_f:
            return True
        else:
            return False

    def zoom_in(self, x=None):
        if not self.can_zoomin():
            return

        self.set_rate(self.rate * 2, x)

    def can_zoomin(self):
        if self.wp is None:
            return False

        return (self.rate * 2) <= MAX_RATE

    def zoom_out(self, x=None):
        if not self.can_zoomout():
            return

        self.set_rate(self.rate / 2, x)

    def can_zoomout(self):
        if self.wp is None:
            return False

        return MIN_RATE <= (self.rate / 2)

    def insert_label(self):
        if not self.can_insert_label():
            return

        self.ml.save()
        self.ml().insert_label(self.cur_s, INSERT_DUR, self.max_s)
        self.UpdateDrawing()

    def can_insert_label(self):
        if (self.ml is None) or self.playing:
            return False

        return self.ml().can_insert_label(self.cur_s, INSERT_DUR, self.max_s)

    def remove_label(self):
        if not self.can_remove_label():
            return

        self.ml.save()
        self.ml().remove_sel()
        self.UpdateDrawing()

    def can_remove_label(self):
        if (self.ml is None) or self.playing or self.ml().selected is None:
            return False

        return True

    def cut(self):
        if not self.can_cut():
            return

        self.ml.save()
        self.ml().cut(self.cur_s)
        self.UpdateDrawing()

    def can_cut(self):
        if (self.ml is None) or self.playing:
            return False

        return self.ml().can_cut(self.cur_s)

    def merge_left(self):
        if not self.can_merge_left():
            return

        self.ml.save()
        self.ml().merge_left()
        self.UpdateDrawing()

    def can_merge_left(self):
        if (self.ml is None) or self.playing:
            return False

        return self.ml().can_merge_left()

    def merge_right(self):
        if not self.can_merge_right():
            return

        self.ml.save()
        self.ml().merge_right()
        self.UpdateDrawing()

    def can_merge_right(self):
        if (self.ml is None) or self.playing:
            return False

        return self.ml().can_merge_right()

    def undo(self):
        if not self.can_undo():
            return

        self.ml.undo()
        self.UpdateDrawing()

    def can_undo(self):
        if (self.ml is None) or self.playing:
            return False

        return self.ml.can_undo()

    def redo(self):
        if not self.can_redo():
            return

        self.ml.redo()
        self.UpdateDrawing()

    def can_redo(self):
        if (self.ml is None) or self.playing:
            return False

        return self.ml.can_redo()

    #--------------------------------------------------------------------------
    # Event Handler
    #--------------------------------------------------------------------------

    def OnSize(self, evt):
        self.size_changed = True

        Size = self.ClientSize
        self.Width = Size[0]
        self.Height = Size[1]

        self._Buffer = wx.EmptyBitmap(*Size)

        self.st_arrow_y = WAV_TOP + ((self.Height - WAV_TOP)/3)
        self.ed_arrow_y = WAV_TOP + ((self.Height - WAV_TOP)*2/3)

        self.handle_dist = ((self.Height - WAV_TOP) / 3) / 2

        self.UpdateDrawing()

    def OnPaint(self, evt):
        if USE_BUFFERED_DC:
            dc = wx.BufferedPaintDC(self, self._Buffer)
        else:
            dc = wx.PaintDC(self)
            dc.DrawBitmap(self._Buffer, 0, 0)

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
            if self.size_changed:
                self.size_changed = False
                evt.Skip()

            if self.rate_changed:
                self.rate_changed = False
                evt.Skip()

        pos = max(0, min(pos, self.GetScrollRange(wx.HORIZONTAL)))

        if old_pos != pos:
            self.SetScrollPos(wx.HORIZONTAL, pos)
            self.UpdateDrawing()

    def OnMouseWheel(self, evt):
        if evt.WheelRotation < 0:
            self.zoom_out(evt.X)
        else:
            self.zoom_in(evt.X)

    def OnUpdate(self, evt):
        self.cur_f = evt.cur_f * self.rate / self.src_rate

    def OnEOF(self, evt):
        wx.PostEvent(self.listener, EOFEvent())

    def OnLeftDown(self, evt):
        self.SetFocus()

        if self.wp is None:
            return

        drag_scroll = True

        cur_f = self.left_f + evt.X

        if evt.Y < WAV_TOP:
            # If top area is clicked, move that point.
            src_f = cur_f * self.src_rate / self.rate
            self.cur_f = cur_f
            self.wp.cur_f = src_f
            self.wp.pause_f = 0
            wx.PostEvent(self.listener, ChangeCurEvent())
            drag_scroll = False
        else:
            if not self.playing:
                # drag handle
                if self.is_in_left_handle(evt.X, evt.Y):
                    self.drag_handle = LEFT_HANDLE
                    self.ml.save()
                    self.CaptureMouse()
                    drag_scroll = False
                elif self.is_in_right_handle(evt.X, evt.Y):
                    self.drag_handle = RIGHT_HANDLE
                    self.ml.save()
                    self.CaptureMouse()
                    drag_scroll = False

                if self.drag_handle == NO_HANDLE:
                    # select label
                    if self.rate != 0:
                        cur_s = float(cur_f) / self.rate
                        self.ml().select(cur_s)
                        wx.PostEvent(self.listener, ChangeCurEvent())

        if drag_scroll and (not self.playing):
            self.drag_scroll = evt.X
            self.drag_scroll_left_f = self.left_f

        self.UpdateDrawing()

    def is_in_left_handle(self, x, y):
        sel = self.ml().selected
        if not sel:
            return False

        st = {'x': int(sel.start * self.rate) - self.left_f, 'y': self.st_arrow_y}
        if self.collision_detection(st['x'], st['y'], x, y, self.handle_dist):
            if st['x'] <= x:
                return st

        return False

    def is_in_right_handle(self, x, y):
        sel = self.ml().selected
        if not sel:
            return False

        ed = {'x': int(sel.end * self.rate) - self.left_f, 'y': self.ed_arrow_y}
        if self.collision_detection(ed['x'], ed['y'], x, y, self.handle_dist):
            if x <= ed['x']:
                return ed

        return False

    def OnLeftUp(self, evt):
        if self.drag_handle != NO_HANDLE:
            self.ReleaseMouse()
            wx.PostEvent(self.listener, ChangeCurEvent())
        self.drag_handle = NO_HANDLE
        self.drag_scroll = False

    def OnRightDown(self, evt):
        if self.drag_handle != NO_HANDLE:
            self.ml.restore()
            self.drag_handle = NO_HANDLE
            self.UpdateDrawing()
        else:
            sel = self.ml().selected
            if sel:
                overlapped = self.ml().get_overlapped(sel)
                if len(overlapped) == 0:
                    self.PopupMenu(MyPopupMenu(self), evt.GetPosition())

    def OnMotion(self, evt):
        if self.wp is None:
            return

        change_handle_active = False

        if (self.drag_handle == NO_HANDLE) and self.ml().selected:
            st = self.is_in_left_handle(evt.X, evt.Y)
            ed = self.is_in_right_handle(evt.X, evt.Y)
            if st:
                self.draw_handle_active = (st, False)
                change_handle_active = True
                self.UpdateDrawing()
            elif ed:
                self.draw_handle_active = (False, ed)
                change_handle_active = True
                self.UpdateDrawing()
        elif (self.drag_handle != NO_HANDLE) and self.ml().selected:
            cur_f = self.left_f + evt.X
            cur_s = float(cur_f) / self.rate

            if self.drag_handle == LEFT_HANDLE:
                self.ml().change_sel(cur_s, None, evt.ShiftDown(), evt.ControlDown())
            elif self.drag_handle == RIGHT_HANDLE:
                self.ml().change_sel(None, cur_s, evt.ShiftDown(), evt.ControlDown())

            self.UpdateDrawing()

        if self.drag_scroll and (not self.playing):
            self.left_f = self.drag_scroll_left_f + (self.drag_scroll - evt.X)
            self.UpdateDrawing()

        if self.draw_handle_active and (not change_handle_active):
            self.draw_handle_active = None
            self.UpdateDrawing()

    def OnSetFocus(self, evt):
        self._has_focus = True
        self.UpdateDrawing()

    def OnKillFocus(self, evt):
        self._has_focus = False
        self.UpdateDrawing()

    def OnKeyDown(self, evt):
        if self.wp is None:
            return

        key = evt.GetKeyCode()

        if key == wx.WXK_NUMPAD_ADD:
            self.zoom_in()
        elif key == wx.WXK_NUMPAD_SUBTRACT:
            self.zoom_out()
        elif key == wx.WXK_DELETE:
            self.remove_label()
        elif key == wx.WXK_SPACE:
            if self.can_pause():
                self.pause()
            elif self.can_play():
                self.play()
        elif key == wx.WXK_HOME:
            self.head()
        elif key == wx.WXK_END:
            self.tail()
        elif key == wx.WXK_LEFT:
            if self.wp and (not self.playing):
                self.cur_f = self.cur_f - 1
        elif key == wx.WXK_RIGHT:
            if self.wp and (not self.playing):
                self.cur_f = self.cur_f + 1

        if (32 <= key) and (key <= 127):
            ch = chr(key)
            if ch == 'b' or ch == 'B':
                self.play_border()
            elif ch == 'c' or ch == 'C':
                self.cut()
            elif ch == 's' or ch == 'S':
                if evt.ControlDown():
                    self.save()
                else:
                    self.playsel()
            elif (ch == 'z' or ch == 'Z') and evt.ControlDown():
                self.undo()

        self.UpdateDrawing()
        wx.PostEvent(self.listener, ChangeCurEvent())

    def collision_detection(self, ax, ay, bx, by, dist):
        ad = math.sqrt((bx-ax)*(bx-ax) + (by-ay)*(by-ay))
        if ad < dist:
            result = True
        else:
            result = False
        return result
 
    #--------------------------------------------------------------------------
    # Property
    #--------------------------------------------------------------------------

    # playing property
    def is_playing(self):
        if self.wp:
            return self.wp.playing
        else:
            return False

    playing = property(is_playing)

    # rate property
    _rate = 0

    def get_rate(self):
        return self._rate

    def set_rate(self, rate, x=None):
        if (MIN_RATE <= rate) and (rate <= MAX_RATE) and (rate <= self.src_rate):
            if x is None:
                x = self.Width / 2

            old_cur_s = self.cur_s
            old_rate = self.rate
            old_left_f = self.left_f

            self._rate = rate
            self.data = rms_ratecv(self.buffer, self.nchannels, self.sampwidth, self.src_rate, rate)

            self.rate_changed = True
            old_pos = self.GetScrollPos(wx.HORIZONTAL)
            old_range = self.GetScrollRange(wx.HORIZONTAL)

            self.SetScrollbars(PPU , 0, math.ceil(float(self.max_f) / PPU), 0)

            if old_rate != 0:
                self.cur_f = old_cur_s * self.rate
                wx.PostEvent(self.listener, ChangeCurEvent())

                cen_s = float(old_left_f + x) / old_rate
                cen_f = int(cen_s * self.rate)
                left_f = cen_f - x
                new_pos = left_f / PPU

                self.SetScrollPos(wx.HORIZONTAL, new_pos)

            self.UpdateDrawing()

    rate = property(get_rate, set_rate)

    # data property
    _data = []

    def get_data(self):
        return self._data

    def set_data(self, data):
        self._data = data
        self.max_f = len(data) - 1
        self.max_s = float(self.max_f) / self.rate
        self.max_val = max(data) / WAV_SCALE
        self.sil_lv = self.sil_lv # recalc thres

    data = property(get_data, set_data)

    # sil_lv property
    _sil_lv = DEFAULT_SIL_LV

    def get_sil_lv(self):
        return self._sil_lv

    def set_sil_lv(self, sil_lv):
        self._sil_lv = max(0, min(sil_lv, 100))
        self.thres = self._sil_lv * self.max_val / 100
        self.UpdateDrawing()

    sil_lv = property(get_sil_lv, set_sil_lv)

    # left_f property
    def get_left_f(self):
        return self.GetScrollPos(wx.HORIZONTAL) * PPU

    def set_left_f(self, left_f):
        if self.rate == 0:
            pos = 0
        else:
            max_left_f = max(0, self.max_f - self.Width)
            left_f = max(0, min(left_f, max_left_f))
            pos = max(0, math.ceil(float(left_f) / PPU))

        self.SetScrollPos(wx.HORIZONTAL, pos)

    left_f = property(get_left_f, set_left_f)

    # cur_f property
    _cur_f = 0

    def get_cur_f(self):
        return self._cur_f

    def set_cur_f(self, cur_f):
        self._cur_f = max(0, min(cur_f, self.max_f))

        if (self.cur_f < self.left_f) or (self.left_f + self.Width < self.cur_f):
            self.left_f = self.cur_f

        self.UpdateDrawing()

    cur_f = property(get_cur_f, set_cur_f)

    # cur_s property
    def get_cur_s(self):
        if self.rate == 0:
            return 0
        else:
            return float(self.cur_f) / self.rate

    def set_cur_s(self, cur_s):
        self.cur_f = int(cur_s * self.rate)

    cur_s = property(get_cur_s, set_cur_s)


class MyLabels():
    def __init__(self, labels):
        self.i = 0
        self.labels_list = [labels]

    def __str__(self):
        result = 'Current Index : %d\n\n' % self.i

        for i, labels in enumerate(self.labels_list):
            result = result + 'Item : %d\n' % i
            result = result + labels.__str__()
            result = result + '\n'

        return result

    def get_labels(self):
        return self.labels_list[self.i]

    def set_labels(self, labels):
        self.labels_list[self.i] = labels

    labels = property(get_labels, set_labels)

    def __call__(self):
        return self.labels

    def save(self):
        if self.i + 1 < len(self.labels_list):
            del self.labels_list[self.i + 1:]
        labels = copy.deepcopy(self.labels)
        self.labels_list.append(labels)
        self.i = self.i + 1

    def clear_history(self):
        labels = self.labels
        self.i = 0
        self.labels_list = [labels]

    def restore(self):
        if 0 < self.i:
            self.labels_list.pop(self.i)
            self.i = self.i - 1

    def undo(self):
        self.i = max(0, self.i - 1)

    def can_undo(self):
        return self.i != 0

    def redo(self):
        self.i = min(self.i + 1, len(self.labels_list))

    def can_redo(self):
        return self.i != len(self.labels_list) - 1

