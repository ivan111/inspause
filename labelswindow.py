# -*- coding: utf-8 -*-
'''
ラベル付きボリューム表示
'''

import math

import wx
import wx_utils

from labels import NO_DISTINCTION
from labelsmanager import LabelsManager
from mywave import auto_shift_diff_s
from volumewindow import VolumeWindow, ClickCurChangedEvent


EVT_LBL_CHANGED_ID = wx.NewId()
EVT_PLAY_IFCUT_ID = wx.NewId()

ARROW_SIZE = 5
INSERT_DUR = 0.5

NO_HANDLE    = 0
LEFT_HANDLE  = 1
RIGHT_HANDLE = 2

INFO_LEFT   = 1
INFO_RIGHT  = 2
INFO_IFCUT  = 3
INFO_CUT    = 4
INFO_BORDER = 5


class LabelsWindow(VolumeWindow):
    '''
    ラベル付きボリューム表示ウィンドウ
    '''

    mybinder = wx_utils.bind_manager()

    def __init__(self, *args, **kwargs):
        self._init_instance_var_lw()

        VolumeWindow.__init__(self, *args, **kwargs)

        self.mybinder.bindall(self)


    def _init_instance_var_lw(self):
        self.lm = None  # LabelsManager

        self._drag_handle = NO_HANDLE
        self._handle_active = None

        self._st_arrow_y = 0
        self._ed_arrow_y = 0

        self._down_arrow = None
        self._right_arrow = None
        self._left_arrow = None

        al = ARROW_SIZE
        self._down_arrow  = ((al, 0), (0, al * math.sqrt(3)),  (-al, 0))
        self._right_arrow = ((0, al), (al * math.sqrt(3), 0),  (0, -al))
        self._left_arrow  = ((0, al), (-al * math.sqrt(3), 0), (0, -al))

        img = wx.Image('icon/cut.png', wx.BITMAP_TYPE_PNG)
        img = img.Scale(16, 16, wx.IMAGE_QUALITY_HIGH)
        self.bmp_cut = wx.BitmapFromImage(img)

        img = wx.Image('icon/playifcut.png', wx.BITMAP_TYPE_PNG)
        img = img.Scale(16, 16, wx.IMAGE_QUALITY_HIGH)
        self.bmp_ifcut = wx.BitmapFromImage(img)

        self.arrow_brush = wx.Brush('#20B2AA')
        self.border_pen = wx.Pen('#404040')


    def get_labels_in_view(self):
        '''
        画面内にあるラベルを取得する
        '''

        left_s  = self.f_to_s(self.left_f)
        right_s = self.f_to_s(self.left_f + self.w - 1)

        labels_in_view = []

        for label in self.lm():
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


    #--------------------------------------------------------------------------
    # 描画

    def draw_base(self, dc, update_base):
        VolumeWindow.draw_base(self, dc, update_base)

        if self.draw_base_changed and self.lm and self.vol:
            self._draw_labels(dc)


    def draw(self, dc):
        VolumeWindow.draw(self, dc)

        if self.lm and self.vol:
            if not self.playing:
                self._draw_active_handle(dc)
                self._draw_focus(dc)

        if self.vol:
            VolumeWindow._draw_cur_position(self, dc)


    def _draw_labels(self, dc):
        w, h = dc.Size

        left_s  = self.f_to_s(self.left_f)

        old_dc = dc
        dc = wx.GCDC(dc)

        lf = old_dc.GetLogicalFunction()
        old_dc.SetLogicalFunction(wx.XOR)

        for label in self.get_labels_in_view():
            x1 = self.s_to_f(label.start_s - left_s)
            x2 = self.s_to_f(label.end_s - left_s)
            w  = x2 - x1

            if w != 0:
                # ---- ラベルの領域を描画

                dc.SetPen(wx.TRANSPARENT_PEN)

                if label.is_cut():
                    color = [32, 32, 32, 192]
                else:
                    color = list(label.color)
                    color.append(32)  # alpha

                label_brush = wx.Brush(wx.Colour(*color))
                dc.SetBrush(label_brush)
                dc.DrawRectangle(x1, 0, w, self.h)

                # ---- 境界
                old_dc.SetPen(self.border_pen)
                old_dc.DrawLine(x1, 0, x1, self.h)
                old_dc.DrawLine(x2, 0, x2, self.h)

        old_dc.SetLogicalFunction(lf)


    # フォーカス矩形を描画
    def _draw_focus(self, dc):
        if not self.lm().selected:
            return

        label = self.lm().selected
        left_s  = self.f_to_s(self.left_f)

        x1 = self.s_to_f(label.start_s - left_s)
        x2 = self.s_to_f(label.end_s - left_s)

        # ---- 矢印ハンドル
        dc.SetPen(wx.GREY_PEN)
        dc.SetBrush(self.arrow_brush)
        dc.DrawPolygon(self._right_arrow, x1, self._st_arrow_y)
        dc.DrawPolygon(self._left_arrow,  x2, self._ed_arrow_y)

        lf = dc.GetLogicalFunction()
        dc.SetLogicalFunction(wx.XOR)

        # ---- 境界
        dc.SetPen(wx.WHITE_PEN)
        dc.DrawLine(x1, 0, x1, self.h)
        dc.DrawLine(x2, 0, x2, self.h)

        dc.SetLogicalFunction(lf)


    def _draw_active_handle(self, dc):
        info = self._handle_active

        if not info:
            return

        lf = dc.GetLogicalFunction()
        dc.SetLogicalFunction(wx.XOR)

        dc.SetPen(wx.Pen('#FFFFFF', 1, wx.DOT))
        dc.SetBrush(wx.TRANSPARENT_BRUSH)

        if info['type'] == INFO_LEFT:
            dc.DrawEllipticArc(info['x'] - self.dist, info['y'] - self.dist, self.dist * 2, self.dist * 2, -90, 90)

            dc.SetLogicalFunction(lf)

            dc.SetPen(wx.GREY_PEN)
            dc.SetBrush(self.arrow_brush)
            dc.DrawPolygon(self._right_arrow, info['x'], info['y'])
        elif info['type'] == INFO_RIGHT:
            dc.DrawEllipticArc(info['x'] - self.dist, info['y'] - self.dist, self.dist * 2, self.dist * 2, 90, 270)

            dc.SetLogicalFunction(lf)

            dc.SetPen(wx.GREY_PEN)
            dc.SetBrush(self.arrow_brush)
            dc.DrawPolygon(self._left_arrow, info['x'], info['y'])
        elif info['type'] == INFO_IFCUT or info['type'] == INFO_BORDER:
            dc.DrawEllipticArc(info['x'] - self.dist, info['y'] - self.dist, self.dist * 2, self.dist * 2, 180, 270)

            dc.SetPen(wx.BLACK_PEN)
            dc.SetBrush(wx.Brush('#FF69B4'))

            half_dist = self.dist / 2
            x = info['x'] - half_dist - 4
            y = info['y'] + half_dist - 12
            dc.DrawBitmap(self.bmp_ifcut, x, y)
        elif info['type'] == INFO_CUT:
            dc.DrawEllipticArc(info['x'] - self.dist, info['y'] - self.dist, self.dist * 2, self.dist * 2, 270, 360)

            half_dist = self.dist / 2
            x = info['x'] + half_dist - 10
            y = info['y'] + half_dist - 10
            dc.DrawBitmap(self.bmp_cut, x, y)

        dc.SetLogicalFunction(lf)


    #--------------------------------------------------------------------------
    # コマンド

    def save(self):
        if not self.can_save():
            return

        self.lm().write(self.wav.labels_file)
        self.lm.clear_history()
        self.update_drawing(True)
        wx.PostEvent(self.Parent, LabelChangedEvent())


    def can_save(self):
        if self.wav and self.can_undo():
            return True
        else:
            return False


    def find(self, sil_lv, sil_dur, before_dur, after_dur):
        if self.wav is None:
            return

        self.lm.save()
        self.lm.labels = self.wav.find_sound(sil_lv, sil_dur, before_dur, after_dur)
        self.update_drawing(True)
        wx.PostEvent(self.Parent, LabelChangedEvent())


    def shift(self, val_s):
        if self.labels is None:
            return

        self.lm.save()
        self.lm().shift(val_s)
        self.update_drawing(True)
        wx.PostEvent(self.Parent, LabelChangedEvent())


    def insert_label(self, evt=None):
        if not self.can_insert_label():
            return

        self.lm.save()
        max_s = self.f_to_s(self.max_f)
        self.lm().insert_label(self.cur_s, INSERT_DUR, max_s)
        self.update_drawing(True)
        wx.PostEvent(self.Parent, LabelChangedEvent())


    def can_insert_label(self):
        if (self.lm is None):
            return False

        max_s = self.f_to_s(self.max_f)
        return self.lm().can_insert_label(self.cur_s, INSERT_DUR, max_s)


    def remove_label(self):
        if not self.can_remove_label():
            return

        self.lm.save()
        self.lm().remove_selected()
        self.update_drawing(True)
        wx.PostEvent(self.Parent, LabelChangedEvent())


    def can_remove_label(self):
        if (self.lm is None) or (self.lm().selected is None):
            return False

        return True


    def cut(self, evt=None):
        if not self.can_cut():
            return

        self.lm.save()
        self.lm().cut(self.cur_s)
        self.update_drawing(True)
        wx.PostEvent(self.Parent, LabelChangedEvent())


    def can_cut(self):
        if self.lm is None:
            return False

        return self.lm().can_cut(self.cur_s)


    def merge_left(self):
        if not self.can_merge_left():
            return

        self.lm.save()
        self.lm().merge_left()
        self.update_drawing(True)
        wx.PostEvent(self.Parent, LabelChangedEvent())


    def can_merge_left(self):
        if self.lm is None:
            return False

        return self.lm().can_merge_left()


    def merge_right(self):
        if not self.can_merge_right():
            return

        self.lm.save()
        self.lm().merge_right()
        self.update_drawing(True)
        wx.PostEvent(self.Parent, LabelChangedEvent())


    def can_merge_right(self):
        if self.lm is None:
            return False

        return self.lm().can_merge_right()


    def undo(self):
        if not self.can_undo():
            return

        self.lm.undo()
        self.update_drawing(True)
        wx.PostEvent(self.Parent, LabelChangedEvent())


    def can_undo(self):
        if self.lm is None:
            return False

        return self.lm.can_undo()


    def redo(self):
        if not self.can_redo():
            return

        self.lm.redo()
        self.update_drawing(True)
        wx.PostEvent(self.Parent, LabelChangedEvent())


    def can_redo(self):
        if self.lm is None:
            return False

        return self.lm.can_redo()


    def auto_shift(self):
        '''
        自動ずれ補正
        '''

        if not self.wav or not self.lm:
            return

        if self.lm().distinction_s == NO_DISTINCTION:
            if self.wav.distinction_s != NO_DISTINCTION:
                self.lm().distinction_s = self.wav.distinction_s
                self.lm().write(self.wav.labels_file)
        else:
            auto_shift_s = auto_shift_diff_s(self.wav.distinction_s, self.lm().distinction_s)

            if auto_shift_s != 0:
                self.lm().distinction_s = self.wav.distinction_s
                self.shift(auto_shift_s)
                self.lm().write(self.wav.labels_file)
                self.lm.clear_history()


    #--------------------------------------------------------------------------
    # ハンドル

    def get_in_handle(self, x, y):
        '''
        ハンドルの中か？

        @return ハンドルの中でないなら None。中ならdict
        '''

        if y > self.dist * 5:
            return None

        # ---- 現在位置の上にあるもしカット再生エリアかカットエリアの中か？

        cut_info = None

        info = {'x': self.cur_f - self.left_f,
                'y': 0}

        if self.hit_test(info['x'], info['y'], x, y, self.dist):
            if x <= info['x']:  # もしカット再生
                if self.Parent.can_play_ifcut():
                    info['type'] = INFO_IFCUT
                    return info
            else:  # カット
                if self.Parent.can_cut():
                    info['x'] += 1  # OnMotion で更新チェックできるように変える
                    info['type'] = INFO_CUT
                    cut_info = info

                    # ラベル右上のもしカット再生とかぶったらそっち優先

        cur_s = self.f_to_s(x) + self.left_s

        for i, label in enumerate(self.lm()):
            if label.end_s < cur_s:
                continue

            if label.start_s > cur_s:
                return cut_info


            # ---- ラベルの左側にある移動ハンドルの中か？

            info = {'x': self.s_to_f(label.start_s) - self.left_f,
                    'y': self._st_arrow_y}

            if self.hit_test(info['x'], info['y'], x, y, self.dist):
                if info['x'] <= x:
                    info['type'] = INFO_LEFT
                    info['drag_label_i'] = i
                    return info

            # ---- ラベルの右側にある移動ハンドルの中か？

            info = {'x': self.s_to_f(label.end_s) - self.left_f,
                    'y': self._ed_arrow_y}

            if self.hit_test(info['x'], info['y'], x, y, self.dist):
                if x <= info['x']:
                    info['type'] = INFO_RIGHT
                    info['drag_label_i'] = i
                    return info

            # ---- ラベルの右上にある境界再生エリアの中か？
            info = {'x': self.s_to_f(label.end_s) - self.left_f,
                    'y': 0}

            if self.hit_test(info['x'], info['y'], x, y, self.dist):
                if x <= info['x']:
                    info['type'] = INFO_BORDER
                    info['cut_s'] = label.end_s
                    info['drag_label_i'] = i
                    return info

        return cut_info


    #--------------------------------------------------------------------------
    # イベントハンドラ

    @mybinder(wx.EVT_SIZE)
    def OnSize(self, evt):
        h = self.ClientSize[1]

        d = h / 7
        self.dist = d

        self._st_arrow_y = d * 2
        self._ed_arrow_y = d * 4

        VolumeWindow.OnSize(self, evt)


    @mybinder(wx.EVT_LEFT_DOWN)
    def OnLeftDown(self, evt):
        self.SetFocus()

        if self.vol is None:
            # 親が処理する
            wx.PostEvent(self.Parent, evt)
            return

        if not self.playing and self.lm:
            # ラベル範囲変更のハンドルか？
            info = self.get_in_handle(evt.X, evt.Y)

            if info:
                if info['type'] == INFO_LEFT or info['type'] == INFO_RIGHT:
                    # ラベル範囲変更ハンドル
                    if info['type'] == INFO_LEFT:
                        self._drag_handle = LEFT_HANDLE
                    else:
                        self._drag_handle = RIGHT_HANDLE

                    self.lm.save()
                    self.lm().select_by_index(info['drag_label_i'])
                    self.CaptureMouse()
                    self.update_drawing(True)
                    return
                elif info['type'] == INFO_IFCUT:  # もしカット再生
                    self.Parent.play_ifcut()
                    wx.PostEvent(self.Parent, PlayIfCutEvent(self.cur_s))
                    return
                elif info['type'] == INFO_CUT:  # カット
                    self.Parent.cut()
                    return
                elif info['type'] == INFO_BORDER:  # 境界再生
                    wx.PostEvent(self.Parent, PlayIfCutEvent(info['cut_s']))
                    self.lm().select_by_index(info['drag_label_i'])
                    self.update_drawing(True)
                    return

            # ラベルを選択できるなら選択する
            if self._drag_handle == NO_HANDLE:
                prev_selected = self.lm().selected

                cur_s = self.f_to_s(self.left_f + evt.X)
                self.lm().select(cur_s)

                if self.lm().selected != prev_selected:
                    self.update_drawing(True)

        # ドラッグでスクロールする
        VolumeWindow.OnLeftDown(self, evt)


    @mybinder(wx.EVT_LEFT_UP)
    def OnLeftUp(self, evt):
        if self._drag_handle != NO_HANDLE:
            self.ReleaseMouse()
            wx.PostEvent(self.Parent, LabelChangedEvent())

        self._drag_handle = NO_HANDLE

        VolumeWindow.OnLeftUp(self, evt)


    @mybinder(wx.EVT_RIGHT_DOWN)
    def OnRightDown(self, evt):
        if self._drag_handle != NO_HANDLE:
            self.ReleaseMouse()
            self.lm.restore()
            self._drag_handle = NO_HANDLE
            self.update_drawing(True)
        else:
            if self.playing:
                return

            # ---- コンテキストメニューを表示

            menu = wx.Menu()
            menu.parent = self

            if self.can_cut():
                mi = wx.MenuItem(menu, wx.NewId(), u'カット')
                menu.AppendItem(mi)
                self.Bind(wx.EVT_MENU, self.cut, mi)

            if self.lm:
                selected = self.lm().selected

                if selected is not None:
                    if selected.is_pause():
                        mi = wx.MenuItem(menu, wx.NewId(), u'カットラベルに変更')
                        menu.AppendItem(mi)
                        menu.Bind(wx.EVT_MENU, self.OnToCutLabel, mi)
                    else:
                        mi = wx.MenuItem(menu, wx.NewId(), u'ポーズラベルに変更')
                        menu.AppendItem(mi)
                        menu.Bind(wx.EVT_MENU, self.OnToPauseLabel, mi)

            self.PopupMenu(menu, evt.Position)


    def OnToCutLabel(self, evt):
        '''
        カットラベルへ変更する
        '''

        if self.lm:
            selected = self.lm().selected

            if selected is not None and selected.is_pause():
                self.lm.save()
                self.lm().selected.set_cut()
                self.lm().clean_data()
                self.update_drawing(True)
                wx.PostEvent(self.Parent, LabelChangedEvent())


    def OnToPauseLabel(self, evt):
        '''
        ポーズラベルへ変更する
        '''

        if self.lm:
            selected = self.lm().selected

            if selected is not None and selected.is_cut():
                self.lm.save()
                self.lm().selected.set_pause()
                self.update_drawing(True)
                wx.PostEvent(self.Parent, LabelChangedEvent())


    @mybinder(wx.EVT_MOTION)
    def OnMotion(self, evt):
        if self.vol is None:
            return

        change_handle_active = False

        if self._drag_handle == NO_HANDLE:
            if self.playing == False and self.lm:
                prev_info = self._handle_active

                # ハンドルをクリックできる状態になったか？
                info = self.get_in_handle(evt.X, evt.Y)

                if info:
                    change_handle_active = True
                    self._handle_active = info

                    if prev_info and prev_info['x'] == info['x'] and prev_info['y'] == info['y']:
                        # 同じなら更新しない
                        pass
                    else:
                        self.update_drawing()
        else:
            # ラベル範囲を変更中
            cur_s = self.f_to_s(self.left_f + evt.X)

            if self._drag_handle == LEFT_HANDLE:
                self.lm().change_selected(start_s=cur_s, is_fit=evt.ShiftDown(), is_near=evt.ControlDown())
                self.cur_s = self.lm().selected.start_s
            elif self._drag_handle == RIGHT_HANDLE:
                self.lm().change_selected(end_s=cur_s, is_fit=evt.ShiftDown(), is_near=evt.ControlDown())
                self.cur_s = self.lm().selected.end_s

            self.update_drawing(True)

        # ハンドルを操作できる範囲からはずれた
        if self._handle_active and (not change_handle_active):
            self._handle_active = None
            self.update_drawing()

        VolumeWindow.OnMotion(self, evt)


    @mybinder(wx.EVT_LEAVE_WINDOW)
    def OnMouseLeave(self, evt):
        if self._handle_active:
            self._handle_active = None
            self.update_drawing()


    @mybinder(wx.EVT_KEY_DOWN)
    def OnKeyDown(self, evt):
        if self.vol is None:
            return

        key = evt.GetKeyCode()

        if key == wx.WXK_DELETE:
            self.remove_label()

        if self._drag_handle == LEFT_HANDLE:
            if key == wx.WXK_LEFT:
                cur_s = self.lm().selected.start_s - 0.002
                self.lm().change_selected(start_s=cur_s)
                self._handle_active = None
                self.cur_s = self.lm().selected.start_s
                self.update_drawing(True)
                return
            elif key == wx.WXK_RIGHT:
                cur_s = self.lm().selected.start_s + 0.002
                self.lm().change_selected(start_s=cur_s)
                self._handle_active = None
                self.cur_s = self.lm().selected.start_s
                self.update_drawing(True)
                return
        elif self._drag_handle == RIGHT_HANDLE:
            if key == wx.WXK_LEFT:
                cur_s = self.lm().selected.end_s - 0.002
                self.lm().change_selected(end_s=cur_s)
                self._handle_active = None
                self.cur_s = self.lm().selected.end_s
                self.update_drawing(True)
                return
            elif key == wx.WXK_RIGHT:
                cur_s = self.lm().selected.end_s + 0.002
                self.lm().change_selected(end_s=cur_s)
                self._handle_active = None
                self.cur_s = self.lm().selected.end_s
                self.update_drawing(True)
                return

        if 32 <= key <= 127:
            ch = chr(key)
            if ch == 'c' or ch == 'C':
                self.cut()
            elif ch == 'i' or ch == 'I':
                self.insert_label()
            elif ch == 'l' or ch == 'L':
                self.merge_left()
            elif ch == 'r' or ch == 'R':
                self.merge_right()
            elif ch == 's' or ch == 'S':
                if evt.ControlDown():
                    self.save()
            elif (ch == 'z' or ch == 'Z') and evt.ControlDown():
                self.undo()
            elif (ch == 'y' or ch == 'Y') and evt.ControlDown():
                self.redo()

        VolumeWindow.OnKeyDown(self, evt)

        wx.PostEvent(self.Parent, evt)


    def hit_test(self, ax, ay, bx, by, dist):
        ad = math.sqrt((bx - ax) * (bx - ax) + (by - ay) * (by - ay))
        if ad < dist:
            result = True
        else:
            result = False
        return result

    #--------------------------------------------------------------------------
    # プロパティ

    def set_view_factor(self, view_factor, x=0):
        self._handle_active = None

        VolumeWindow.set_view_factor(self, view_factor, x)


    # ラベル
    @property
    def labels(self):
        if self.lm is None:
            return []
        else:
            return self.lm()

    @labels.setter
    def labels(self, labels):
        self.lm = LabelsManager(labels)
        self.update_drawing()


class LabelChangedEvent(wx.PyEvent):
    def __init__(self):
        wx.PyEvent.__init__(self)
        self.SetEventType(EVT_LBL_CHANGED_ID)


class PlayIfCutEvent(wx.PyEvent):
    def __init__(self, cut_s):
        wx.PyEvent.__init__(self)
        self.SetEventType(EVT_PLAY_IFCUT_ID)
        self.cut_s = cut_s


if __name__ == '__main__':
    from mywave import MyWave

    def main():
        app = TestLabelsWindow(redirect=True, filename='log_labelswindow.txt')
        app.MainLoop()

    class TestLabelsWindow(wx.App):
        def OnInit(self):
            frame = wx.Frame(None, -1, 'TestLabelsWindow')
            panel = wx.Panel(frame)

            layout = wx.BoxSizer(wx.HORIZONTAL)
            panel.SetSizer(layout)

            window = LabelsWindow(panel)
            wav = MyWave('in.wav', '001.txt')
            window.wav = wav
            window.labels = wav.find_sound()
            layout.Add(window, proportion=1, flag=wx.EXPAND)

            window.Connect(-1, -1, EVT_LBL_CHANGED_ID, self.OnLabelChanged)

            frame.Centre()
            frame.Show()

            return True

        def OnChangeCur(self, evt):
            print 'OnChangeCur'

        def OnLabelChanged(self, evt):
            print 'OnLabelChanged'


    main()

