# -*- coding: utf-8 -*-

'''
ラベル付きボリューム表示
'''

import math

import wx

from findsnd import find_sound
from labels import Labels, NO_DISTINCTION
from labelsmanager import LabelsManager
from volumewindow import *


ARROW_SIZE = 5  # 範囲変更ハンドルの矢印サイズ
INSERT_DUR_S = 0.5  # 新規に範囲を挿入するときの範囲の長さ

# ---- 範囲変更ハンドル
NO_HANDLE    = 0
LEFT_HANDLE  = 1
RIGHT_HANDLE = 2

# ---- ハンドルタイプ
HT_NONE     = 0
HT_LEFT     = 1
HT_RIGHT    = 2
HT_IFCUT    = 3
HT_CUT      = 4
HT_SELECTED = 5
HT_INSERT   = 6
HT_LMERGE   = 7
HT_RMERGE   = 8
HT_REMOVE   = 9
HT_CHGLBL   = 10

BORDER_COLOUR = '#404040'
HANDLE_COLOUR = 'light grey'


class LabelsWindow(VolumeWindow):
    '''
    ラベル付きボリューム表示ウィンドウ
    '''

    binder = VolumeWindow.binder

    def __init__(self, *args, **kwargs):
        self.lm = None  # LabelsManager
        self._is_enter = False
        self._drag_handle = NO_HANDLE
        self._handle_type = None
        self.border_pen = wx.Pen(BORDER_COLOUR)
        self.handle_brush = wx.Brush(HANDLE_COLOUR)

        self._init_arrow()
        self._load_btn_img()

        VolumeWindow.__init__(self, *args, **kwargs)

        self.AddLayer()

    def GetLabels(self):
        return self.labels

    def SetLabels(self, labels, labels_file):
        self.labels_file = labels_file
        self.lm = LabelsManager(labels)
        self.UpdateDrawing(2)

    def ReloadLabels(self):
        f = self.labels_file
        if f and os.path.exists(f):
            labels = Labels(f)
            self.SetLabels(labels, f)

    def SetHandleColour(self, colour):
        self.handle_brush = wx.Brush(colour)
        self.UpdateDrawing(2)

    #--------------------------------------------------------------------------
    # 描画

    def Draw(self, dc, nlayer):
        if nlayer == 1:
            VolumeWindow.Draw(self, dc, nlayer)
            return

        if nlayer != 2:
            return

        self.DrawBase(dc, nlayer-1)

        old_dc = dc
        dc = wx.GCDC(dc)

        if self.labels and self._vol:

            self.DrawLabels(dc, old_dc)

            if not self.playing:
                selected = self.selected
                if selected:
                    self.DrawHandle(dc, selected)
                    self.DrawFocus(dc, selected)
                else:
                    self.DrawInsert(dc)

    def DrawLabels(self, dc, old_dc):
        left_s = self.left_s

        lf = old_dc.GetLogicalFunction()
        old_dc.SetLogicalFunction(wx.XOR)

        for label in self._get_labels_in_view():
            x1 = self.s_to_i(label.start_s - left_s)
            x2 = self.s_to_i(label.end_s - left_s)
            w = x2 - x1

            if w != 0:
                # ---- ラベルの領域を描画

                dc.SetPen(wx.TRANSPARENT_PEN)

                if label.is_cut():
                    colour = [32, 32, 32, 192]
                else:
                    colour = list(label.colour)
                    colour.append(32)  # alpha

                label_brush = wx.Brush(wx.Colour(*colour))
                dc.SetBrush(label_brush)
                dc.DrawRectangle(x1, 0, w, self.h)

                # ---- 境界
                old_dc.SetPen(self.border_pen)
                old_dc.DrawLine(x1, 0, x1, self.h)
                old_dc.DrawLine(x2, 0, x2, self.h)

        old_dc.SetLogicalFunction(lf)

    # フォーカス矩形を描画
    def DrawFocus(self, dc, selected):
        left_s = self.left_s

        x1 = self.s_to_i(selected.start_s - left_s)
        x2 = self.s_to_i(selected.end_s - left_s)

        lf = dc.GetLogicalFunction()
        dc.SetLogicalFunction(wx.XOR)

        # ---- 境界
        dc.SetPen(wx.WHITE_PEN)
        dc.DrawLine(x1, 0, x1, self.h)
        dc.DrawLine(x2, 0, x2, self.h)

        dc.SetLogicalFunction(lf)

    def DrawHandle(self, dc, selected):
        dc.SetPen(wx.Pen('black', 1, wx.DOT))
        dc.SetBrush(wx.TRANSPARENT_BRUSH)

        self.DrawIfcutAndCut(dc, selected)
        self.DrawSelectedPlay(dc, selected)
        self.DrawMerge(dc, selected)
        self.DrawChangeLblAndRemove(dc, selected)
        self.DrawChangeRange(dc, selected)

    def DrawIfcutAndCut(self, dc, selected):
        '''
        選択範囲の中にある現在位置の上方にある「もしカット再生」ボタン
        と「分割」ボタンを描画
        '''

        if (self._drag_handle == NO_HANDLE and self.can_cut() and
                selected.contains(self.pos_s)):
            pass
        else:
            return

        x = self.pos_i - self.left_i
        d = self.dist

        self.SetHandleTypeBrush(dc, HT_IFCUT, self.selected)
        dc.DrawEllipticArc(x-d, -d, d*2, d*2, 180, 270)
        self.SetHandleTypeBrush(dc, HT_CUT, self.selected)
        dc.DrawEllipticArc(x-d, -d, d*2, d*2, 270, 360)
        dc.DrawBitmap(self.bmp_ifcut, x-36, 20)
        dc.DrawBitmap(self.bmp_cut, x+20, 20)

    def DrawSelectedPlay(self, dc, selected):
        '''
        選択範囲の右上にある選択再生ボタンを描画
        '''

        x = self.s_to_i(selected.end_s) - self.left_i
        d = self.dist

        self.SetHandleTypeBrush(dc, HT_SELECTED, self.selected)
        dc.DrawEllipticArc(x-d, -d, d*2, d*2, 180, 270)
        dc.DrawBitmap(self.bmp_ifcut, x-36, 20)

    def DrawChangeLblAndRemove(self, dc, selected):
        '''
        選択範囲の中にある現在位置の下方にあるラベル変更ボタンと削除ボタンを描画
        '''

        w = self.w
        h = self.h
        st_i = self.s_to_i(selected.start_s)
        ed_i = self.s_to_i(selected.end_s)
        x = (st_i + ed_i) / 2 - self.left_i
        y = h
        d = self.dist / 2

        self.SetHandleTypeBrush(dc, HT_CHGLBL, self.selected)
        dc.DrawEllipticArc(x-d, y-d, d*2, d*2, 90, 180)
        dc.DrawLine(x, h-d, x, h)
        self.SetHandleTypeBrush(dc, HT_REMOVE, self.selected)
        dc.DrawEllipticArc(x-d, y-d, d*2, d*2, 0, 90)

        if selected.is_pause():
            dc.DrawBitmap(self.bmp_dellbl, x-20, y-20)
        else:
            dc.DrawBitmap(self.bmp_sndlbl, x-20, y-20)
        dc.DrawBitmap(self.bmp_remove, x+4, y-20)

    def DrawMerge(self, dc, selected):
        '''
        選択範囲の両端の下にある選択再生ボタンを描画
        '''

        w = self.w
        h = self.h

        lx = self.s_to_i(selected.start_s) - self.left_i
        rx = self.s_to_i(selected.end_s) - self.left_i
        y = h
        d = self.dist / 2

        if self.can_merge_left():
            self.SetHandleTypeBrush(dc, HT_LMERGE, self.selected)
            dc.DrawEllipticArc(lx-d, y-d, d*2, d*2, 0, 90)
            dc.DrawBitmap(self.bmp_lmerge, lx+4, y-20)

        if self.can_merge_right():
            self.SetHandleTypeBrush(dc, HT_RMERGE, self.selected)
            dc.DrawEllipticArc(rx-d, y-d, d*2, d*2, 90, 180)
            dc.DrawBitmap(self.bmp_rmerge, rx-20, y-20)

    def DrawChangeRange(self, dc, selected):
        '''
        選択範囲の両端の中程にある範囲変更ハンドルを描画
        '''

        lx = self.s_to_i(selected.start_s) - self.left_i
        rx = self.s_to_i(selected.end_s) - self.left_i
        ly = self._st_arrow_y
        ry = self._ed_arrow_y
        d = self.dist

        self.SetHandleTypeBrush(dc, HT_LEFT, self.selected)
        dc.DrawEllipticArc(lx-d, ly-d, d*2, d*2, -90, 90)
        self.SetHandleTypeBrush(dc, HT_RIGHT, self.selected)
        dc.DrawEllipticArc(rx-d, ry-d, d*2, d*2, 90, 270)

        dc.SetPen(wx.GREY_PEN)
        dc.SetBrush(self.arrow_brush)
        dc.DrawPolygon(self._right_arrow, lx, ly)
        dc.DrawPolygon(self._left_arrow, rx, ry)

    def DrawInsert(self, dc):
        '''
        選択範囲の外にある現在位置の上方にある「挿入」ボタンを描画
        '''

        if (self._is_enter and self._drag_handle == NO_HANDLE and
                self.can_insert_label()):
            pass
        else:
            return

        dc.SetPen(wx.Pen('black', 1, wx.DOT))
        dc.SetBrush(wx.TRANSPARENT_BRUSH)

        x = self.pos_i - self.left_i
        d = self.dist

        self.SetHandleTypeBrush(dc, HT_INSERT, self.selected)
        dc.DrawEllipticArc(x-d, -d, d*2, d*2, 270, 360)
        dc.DrawBitmap(self.bmp_insert, x+20, 20)

    def SetHandleTypeBrush(self, dc, typ, selected):
        if self._handle_type == typ:
            if selected:
                colour = list(selected.colour)
                colour.append(32)  # alpha

                handle_brush = wx.Brush(wx.Colour(*colour))
                dc.SetBrush(handle_brush)
            else:
                dc.SetBrush(self.handle_brush)
        else:
            dc.SetBrush(wx.TRANSPARENT_BRUSH)

    #--------------------------------------------------------------------------
    # コマンド

    def can_save(self):
        if self._vol and self.can_undo():
            return True
        else:
            return False

    def save(self):
        if not self.can_save():
            return

        self.labels.write(self.labels_file)
        self.lm.clear_history()
        self.post_label_change_evt()

    def find(self, sil_lv, sil_dur, before_dur, after_dur):
        if self._vol is None:
            return

        self.lm.save()
        self.lm.labels = find_sound(self._vol, sil_lv, sil_dur, before_dur, after_dur)
        self.UpdateDrawing(2)
        self.post_label_change_evt()

    def shift(self, val_s):
        if self.labels is None:
            return

        self.lm.save()
        self.labels.shift(val_s)
        self.UpdateDrawing(2)
        self.post_label_change_evt()

    # ---- ラベル編集
    def can_insert_label(self):
        if not self.playing and self.labels:
            return self.labels.can_insert_label(self.pos_s, INSERT_DUR_S, self._vol.dur_s)
        else:
            return False

    def insert_label(self, evt=None):
        if not self.can_insert_label():
            return

        self.lm.save()
        max_s = self.i_to_s(len(self._vol) - 1)
        self.labels.insert_label(self.pos_s, INSERT_DUR_S, max_s)
        self.UpdateDrawing(2)
        self.post_label_change_evt()

    def can_remove_label(self):
        if not self.playing and self.selected:
            return True
        else:
            return False

    def remove_label(self):
        if not self.can_remove_label():
            return

        self.lm.save()
        self.labels.remove_selected()
        self.UpdateDrawing(2)
        self.post_label_change_evt()

    def can_cut(self):
        if not self.playing and self.labels:
            return self.labels.can_cut(self.pos_s)
        else:
            return False

    def cut(self, evt=None):
        if not self.can_cut():
            return

        self.lm.save()
        self.labels.cut(self.pos_s)
        self.UpdateDrawing(2)
        self.post_label_change_evt()

    def can_change_lbl(self):
        if not self.playing and self.selected:
            return self.labels.can_change_lbl()
        else:
            return False

    def change_lbl(self, evt=None):
        if not self.can_change_lbl():
            return

        self.lm.save()
        self.labels.change_lbl()
        self.UpdateDrawing(2)
        self.post_label_change_evt()

    def can_merge_left(self):
        if not self.playing and self.labels:
            return self.labels.can_merge_left()
        else:
            return False

    def merge_left(self):
        if not self.can_merge_left():
            return

        self.lm.save()
        self.labels.merge_left()
        self.UpdateDrawing(2)
        self.post_label_change_evt()

    def can_merge_right(self):
        if not self.playing and self.labels:
            return self.labels.can_merge_right()
        else:
            return False

    def merge_right(self):
        if not self.can_merge_right():
            return

        self.lm.save()
        self.labels.merge_right()
        self.UpdateDrawing(2)
        self.post_label_change_evt()

    # ---- 履歴

    def can_undo(self):
        if not self.playing and self.lm:
            return self.lm.can_undo()
        else:
            return False

    def undo(self):
        if not self.can_undo():
            return

        self.lm.undo()
        self.UpdateDrawing(2)
        self.post_label_change_evt()

    def can_redo(self):
        if not self.playing and self.lm:
            return self.lm.can_redo()
        else:
            return False

    def redo(self):
        if not self.can_redo():
            return

        self.lm.redo()
        self.UpdateDrawing(2)
        self.post_label_change_evt()

    #--------------------------------------------------------------------------
    # イベントハンドラ

    @binder(wx.EVT_SIZE)
    def OnSize(self, evt):
        h = self.ClientSize[1]

        d = h / 7
        self.dist = d

        self._st_arrow_y = d * 2
        self._ed_arrow_y = d * 4

        VolumeWindow.OnSize(self, evt)

    @binder(wx.EVT_ENTER_WINDOW)
    def OnEnterWindow(self, evt):
        self.SetFocus()

        self._is_enter = True

        self.UpdateDrawing(2)

    @binder(wx.EVT_LEAVE_WINDOW)
    def OnLeaveWindow(self, evt):
        self._is_enter = False
        self._handle_type = HT_NONE

        self.post_status_msg_evt()

        if self.selected and self._drag_handle == NO_HANDLE:
            self.labels.selected = None

        self.UpdateDrawing(2)

    @binder(wx.EVT_LEFT_DOWN)
    def OnLeftDown(self, evt):
        self.SetFocus()

        if self._vol is None:
            VolumeWindow.OnLeftDown(self, evt)
            return

        if not self.playing:
            typ = self._set_handle_type(evt.X, evt.Y)

            if typ == HT_LEFT or typ == HT_RIGHT:  # 範囲変更
                if typ == HT_LEFT:
                    self._drag_handle = LEFT_HANDLE
                else:
                    self._drag_handle = RIGHT_HANDLE

                self.lm.save()
                self.CaptureMouse()
                self.UpdateDrawing(2)
                return
            elif typ == HT_IFCUT:  # もしカット再生
                self.post_ifcut_play_evt(self.pos_s)
                return
            elif typ == HT_CUT:  # カット
                self.cut()
                return
            elif typ == HT_SELECTED:  # 選択ラベル再生
                self.post_ifcut_play_evt(self.selected.end_s)
                return
            elif typ == HT_INSERT:  # 範囲挿入
                self.insert_label()
                return
            elif typ == HT_LMERGE:  # 左結合
                self.merge_left()
                return
            elif typ == HT_RMERGE:  # 右結合
                self.merge_right()
                return
            elif typ == HT_CHGLBL:  # ラベル種類変更
                self.change_lbl()
                return
            elif typ == HT_REMOVE:  # ラベル削除
                self.remove_label()
                return

        # ドラッグでスクロールする
        VolumeWindow.OnLeftDown(self, evt)

    @binder(wx.EVT_LEFT_UP)
    def OnLeftUp(self, evt):
        if self._drag_handle != NO_HANDLE and self.HasCapture():
            self.ReleaseMouse()
            self.post_label_change_evt()
        else:
            evt.Skip()
            VolumeWindow.OnLeftUp(self, evt)

        self._drag_handle = NO_HANDLE

    @binder(wx.EVT_RIGHT_DOWN)
    def OnRightDown(self, evt):
        if self._drag_handle != NO_HANDLE and self.HasCapture():
            self.ReleaseMouse()
            self.lm.restore()
            self._drag_handle = NO_HANDLE
            self.UpdateDrawing(2)

    @binder(wx.EVT_MOTION)
    def OnMotion(self, evt):
        if self._vol is None or self.playing:
            VolumeWindow.OnMotion(self, evt)
            return

        update = False

        if self._drag_handle == NO_HANDLE:
            VolumeWindow.OnMotion(self, evt)

            # ---- マウスがラベル範囲内なら選択する
            if not self.playing and self.labels:
                prev_selected = self.selected
                pos_s = self.left_s + self.i_to_s(evt.X)
                selected = self.labels.select(pos_s)

                if prev_selected != selected:
                    update = True

            # ---- ハンドルの操作ができるならハンドルの背景色を変えるために更新
            old = self._handle_type
            new = self._set_handle_type(evt.X, evt.Y)

            if old != new:
                update = True

                self.post_status_msg_evt()
        else:  # ラベル範囲を変更中
            pos_s = self.i_to_s(self.left_i + evt.X)

            if self._drag_handle == LEFT_HANDLE:
                if self.selected:
                    update = self.labels.change_range(start_s=pos_s, is_fit=evt.ShiftDown(), is_near=evt.ControlDown())
                    self.pos_s = self.selected.start_s
            elif self._drag_handle == RIGHT_HANDLE:
                if self.selected:
                    update = self.labels.change_range(end_s=pos_s, is_fit=evt.ShiftDown(), is_near=evt.ControlDown())
                    self.pos_s = self.selected.end_s

        if update:
            self.UpdateDrawing(2)

    @binder(wx.EVT_KEY_DOWN)
    def OnKeyDown(self, evt):
        if self._vol is None:
            return

        key = evt.GetKeyCode()

        if key == wx.WXK_DELETE:
            self.remove_label()
        elif key == wx.WXK_SPACE and evt.ShiftDown():
            if not self.playing:
                self.post_pause_play_evt()
                return

        if self._drag_handle == LEFT_HANDLE:
            if key == wx.WXK_LEFT:
                pos_s = self.selected.start_s - 0.002
                self.labels.change_range(start_s=pos_s)
                self._handle_type = None
                self.pos_s = self.selected.start_s
                self.UpdateDrawing(1)
                return
            elif key == wx.WXK_RIGHT:
                pos_s = self.selected.start_s + 0.002
                self.labels.change_range(start_s=pos_s)
                self._handle_type = None
                self.pos_s = self.selected.start_s
                self.UpdateDrawing(1)
                return
        elif self._drag_handle == RIGHT_HANDLE:
            if key == wx.WXK_LEFT:
                pos_s = self.selected.end_s - 0.002
                self.labels.change_range(end_s=pos_s)
                self._handle_type = None
                self.pos_s = self.selected.end_s
                self.UpdateDrawing(1)
                return
            elif key == wx.WXK_RIGHT:
                pos_s = self.selected.end_s + 0.002
                self.labels.change_range(end_s=pos_s)
                self._handle_type = None
                self.pos_s = self.selected.end_s
                self.UpdateDrawing(1)
                return

        if self.playing == False:
            if 32 <= key <= 127:
                ch = chr(key).lower()

                if ch == 'b' and self.can_cut():
                    self.post_ifcut_play_evt(self.pos_s)
                elif ch == 'c':
                    self.cut()
                elif ch == 'i':
                    self.insert_label()
                elif ch == 'l':
                    self.merge_left()
                elif ch == 'r':
                    self.merge_right()
                elif ch == 's':
                    if evt.ControlDown():
                        self.save()
                    else:
                        if self.selected:
                            end_s = self.selected.end_s
                            self.post_ifcut_play_evt(end_s)
                elif (ch == 'z') and evt.ControlDown():
                    self.undo()
                elif (ch == 'y') and evt.ControlDown():
                    self.redo()

        VolumeWindow.OnKeyDown(self, evt)

    #--------------------------------------------------------------------------
    # プロパティ

    @property
    def labels(self):
        if self.lm:
            return self.lm()
        else:
            return None

    @property
    def selected(self):
        if self.lm:
            return self.lm().selected
        else:
            return None

    #--------------------------------------------------------------------------
    # 内部メソッド

    def _init_arrow(self):
        self._st_arrow_y = 0
        self._ed_arrow_y = 0

        self._right_arrow = None
        self._left_arrow = None

        al = ARROW_SIZE
        self._right_arrow = ((0, al), (al * math.sqrt(3), 0),  (0, -al))
        self._left_arrow  = ((0, al), (-al * math.sqrt(3), 0), (0, -al))

        self.arrow_brush = wx.Brush('#20B2AA')

    def _load_btn_img(self):
        self.bmp_cut = self._load_img('cut.png')
        self.bmp_ifcut = self._load_img('playifcut.png')
        self.bmp_lmerge = self._load_img('mergeleft.png')
        self.bmp_rmerge = self._load_img('mergeright.png')
        self.bmp_insert = self._load_img('insert.png')
        self.bmp_dellbl = self._load_img('dellbl.png')
        self.bmp_sndlbl = self._load_img('sndlbl.png')
        self.bmp_remove = self._load_img('remove.png')

    def _load_img(self, fname):
        img = wx.Image('icon/%s' % fname, wx.BITMAP_TYPE_PNG)
        img = img.Scale(16, 16, wx.IMAGE_QUALITY_HIGH)
        return wx.BitmapFromImage(img)

    def _get_labels_in_view(self):
        '''
        画面内にあるラベルを取得する
        '''

        labels = self.labels
        if labels is None:
            return

        left_s = self.i_to_s(self.left_i)
        right_s = self.i_to_s(self.left_i + self.w - 1)

        labels_in_view = []

        for label in labels:
            if label.end_s < left_s:
                continue

            if label.start_s > right_s:
                return labels_in_view

            # 開始位置が視界の範囲内か？
            if left_s <= label.start_s and label.start_s <= right_s:
                labels_in_view.append(label)
                continue

            # 終了位置が視界の範囲内か？
            if left_s <= label.end_s and label.end_s <= right_s:
                labels_in_view.append(label)
                continue

            # ラベルが視界の全部を含んでいるか？
            if label.contains(left_s) and label.contains(right_s):
                labels_in_view.append(label)
                continue

        return labels_in_view

    def _set_handle_type(self, x, y):
        '''
        引数の座標に対応するハンドルの種類を返す
        '''

        self._handle_type = HT_NONE

        if self.labels is None:
            return self._handle_type

        selected = self.selected
        pos_x = self.pos_i - self.left_i

        # ---- 非選択範囲のハンドル

        if selected is None:
            if (self._hit_test(pos_x, 0, x, y, self.dist) and
                    x > pos_x):  # 範囲挿入ハンドル
                self._handle_type = HT_INSERT
                return self._handle_type

            return self._handle_type

        # ---- 選択範囲のハンドル

        if self._hit_test(pos_x, 0, x, y, self.dist):
            if x <= pos_x:  # もしカット再生ハンドル
                if self.can_cut():
                    self._handle_type = HT_IFCUT
                    return self._handle_type
            else:  # カットハンドル
                if self.can_cut():
                    self._handle_type = HT_CUT

                    # ラベル右上の「もしカット再生」とかぶったらそっち優先

        pos_s = self.left_s + self.i_to_s(x)
        if pos_s < selected.start_s or selected.end_s < pos_s:
            return self._handle_type

        st_x = self.s_to_i(selected.start_s) - self.left_i

        # ---- 左移動ハンドル
        if self._hit_test(st_x, self._st_arrow_y, x, y, self.dist):
            if x >= st_x:
                self._handle_type = HT_LEFT
                return self._handle_type

        # ---- 左結合ハンドル
        if self._hit_test(st_x, self.h, x, y, self.dist / 2):
            if x >= st_x and self.can_merge_left():
                self._handle_type = HT_LMERGE
                return self._handle_type

        ed_x = self.s_to_i(selected.end_s) - self.left_i

        # ---- 右移動ハンドル
        if self._hit_test(ed_x, self._ed_arrow_y, x, y, self.dist):
            if x <= ed_x:
                self._handle_type = HT_RIGHT
                return self._handle_type

        # ---- 右結合ハンドル
        if self._hit_test(ed_x, self.h, x, y, self.dist / 2):
            if x <= ed_x and self.can_merge_right():
                self._handle_type = HT_RMERGE
                return self._handle_type

        # ---- 選択再生ハンドル
        if self._hit_test(ed_x, 0, x, y, self.dist):
            if x <= ed_x:
                self._handle_type = HT_SELECTED
                return self._handle_type

        mid_x = (st_x + ed_x) / 2

        if self._hit_test(mid_x, self.h, x, y, self.dist/2):
            if x <= mid_x:  # ラベル種類変更
                self._handle_type = HT_CHGLBL
            else:  # ラベル削除
                self._handle_type = HT_REMOVE

            return self._handle_type

        return self._handle_type

    def _hit_test(self, ax, ay, bx, by, dist):
        '''
        (ax, ay)と(bx, by)の間の距離がdist以下か？
        '''

        ad = math.sqrt((bx - ax) * (bx - ax) + (by - ay) * (by - ay))
        if ad < dist:
            result = True
        else:
            result = False
        return result

    # ---- イベント発行

    def post_label_change_evt(self):
        evt = LabelsWindowEvent(myEVT_LABEL_CHANGE, self.GetId())
        self.GetEventHandler().ProcessEvent(evt)

    def post_ifcut_play_evt(self, pos_s):
        evt = LabelsWindowEvent(myEVT_REQ_IFCUT_PLAY, self.GetId(), pos_s)
        self.GetEventHandler().ProcessEvent(evt)

    def post_pause_play_evt(self):
        evt = LabelsWindowEvent(myEVT_REQ_PAUSE_PLAY, self.GetId())
        self.GetEventHandler().ProcessEvent(evt)

    def post_status_msg_evt(self):
        typ = self._handle_type
        if typ == HT_NONE:
            msg = u''
        elif typ == HT_LEFT:
            msg = u'範囲を変更'
        elif typ == HT_RIGHT:
            msg = u'範囲を変更'
        elif typ == HT_IFCUT:
            msg = u'もしカット再生'
        elif typ == HT_CUT:
            msg = u'範囲の分割'
        elif typ == HT_SELECTED:
            msg = u'選択再生'
        elif typ == HT_INSERT:
            msg = u'新しい範囲の挿入'
        elif typ == HT_LMERGE:
            msg = u'左の範囲と結合'
        elif typ == HT_RMERGE:
            msg = u'右の範囲と結合'
        elif typ == HT_REMOVE:
            msg = u'範囲の削除'
        elif typ == HT_CHGLBL:
            selected = self.selected
            if selected:
                if selected.is_pause():
                    msg = u'音声の削除'
                else:
                    msg = u'音声削除の取り消し'

        evt = LabelsWindowEvent(myEVT_STATUS_MSG, self.GetId())
        evt.SetMsg(msg)
        self.GetEventHandler().ProcessEvent(evt)


#------------------------------------------------------------------------------
# イベント
#------------------------------------------------------------------------------

# ---- イベントタイプ
myEVT_LABEL_CHANGE = wx.NewEventType()
myEVT_REQ_IFCUT_PLAY = wx.NewEventType()
myEVT_REQ_PAUSE_PLAY = wx.NewEventType()
myEVT_STATUS_MSG = wx.NewEventType()

# ---- イベントバインダ
EVT_LABEL_CHANGE = wx.PyEventBinder(myEVT_LABEL_CHANGE, 1)
EVT_REQ_IFCUT_PLAY = wx.PyEventBinder(myEVT_REQ_IFCUT_PLAY, 1)
EVT_REQ_PAUSE_PLAY = wx.PyEventBinder(myEVT_REQ_PAUSE_PLAY, 1)
EVT_STATUS_MSG = wx.PyEventBinder(myEVT_STATUS_MSG, 1)


class LabelsWindowEvent(wx.PyCommandEvent):
    def __init__(self, event_type, id, pos_s=0, msg=None):
        wx.PyCommandEvent.__init__(self, event_type, id)
        self.SetSec(pos_s)
        self.SetMsg(msg)

    def GetSec(self):
        return self.pos_s

    def SetSec(self, pos_s):
        self.pos_s = pos_s

    def GetMsg(self):
        return self.msg

    def SetMsg(self, msg):
        self.msg = msg


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
            wx.Frame.__init__(self, None, size=(500, 400))

            wav = pausewave.open('in.mp3')
            vol = Volume(wav)
            labels = find_sound(vol)

            win = LabelsWindow(parent=self, id=-1)
            self.statusbar = self.CreateStatusBar()
            win.Bind(EVT_VW_POS_CHANGE, self.OnVwPosChange)
            win.Bind(EVT_REQ_PLAY, self.OnPlay)
            win.Bind(EVT_REQ_PAUSE, self.OnPause)
            win.Bind(EVT_REQ_IFCUT_PLAY, self.OnIfCutPlay)
            win.Bind(EVT_REQ_PAUSE_PLAY, self.OnPausePlay)
            win.SetVolume(vol)
            win.SetLabels(labels, None)

            self.win = win

        def OnPlay(self, evt):
            print 'play'

        def OnPause(self, evt):
            print 'pause'

        def OnVwPosChange(self, evt):
            pos_s = self.win.f_to_s(evt.GetPos())
            time_str = sec_to_str(pos_s)
            self.statusbar.SetStatusText(time_str)

        def OnIfCutPlay(self, evt):
            print 'ifcut play: %.6fs' % evt.GetSec()

        def OnPausePlay(self, evt):
            print 'pause play'

    app = wx.PySimpleApp()
    frame = MyFrame()
    frame.Show(True)
    app.MainLoop()
