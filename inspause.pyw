# -*- coding: utf-8 -*-

import codecs
import os
import sys

already_exists = False

try:
    import win32event
    import win32api
    import winerror
    handle = win32event.CreateMutex(None, 1, 'inspause mutex')
    if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
        # 多重起動しない
        already_exists = True
except:
    pass

if already_exists:
    sys.exit(1)

import wx
import wx.lib.agw.ultimatelistctrl as ULC
import wx.lib.masked as masked
from wx import xrc

import persist

from findsound import find_sound
from insertpause import insert_pause
from labels import Labels
import revpause
from revpause import rev_pause
from settings import Settings
import waveview
from waveview import WaveView, EVT_CHANGE_CUR_ID, EVT_CHANGE_SEL_ID, EVT_CHANGE_LBL_ID, EVT_EOF_ID

APP_NAME = 'InsPause'

XRC_FILE = 'inspause.xrc'
PERSIST_FILE = 'persist.txt'
LOG_FILE = 'log.txt'
LABELS_DIR = 'labels'
PAUSE_DIR = 'pause'
REVERSE_DIR = 'reverse'
ERROR_FILE = 'error.txt'

SIL_DUR_MIN = 0.01
SIL_DUR_MAX = 9.99
FACTOR_MIN = 0.0
FACTOR_MAX = 9.99
ADD_MIN = 0.0
ADD_MAX = 9.99

# テーブル用
COL_START = 0
COL_END = 1
COL_TYPE = 2
COL_DUR = 3
COL_TEXT = 4

try:
    dirName = os.path.dirname(os.path.abspath(__file__))
except:
    dirName = os.path.dirname(os.path.abspath(sys.argv[0]))

persist_file = os.path.join(dirName, PERSIST_FILE)


def main():
    app = InsPause(redirect=True, filename=LOG_FILE)
    app.MainLoop()


class InsPause(wx.App):
    def OnInit(self):
        # アイコンを設定
        try:
            handle = win32api.GetModuleHandle(None)
            exeName = win32api.GetModuleFileName(handle)
            icon = wx.Icon(exeName, wx.BITMAP_TYPE_ICO)
            self.SetIcon(icon)
        except:
            pass

        self.settings = Settings()
        self.settings.read_conf()

        self.set_debug()

        self.res = xrc.XmlResource(XRC_FILE)

        self.InitFrame()
        self.InitMenu()
        self.InitToolbar()
        self.set_enable()

        self.pm = persist.PersistenceManager.Get()
        self.pm.SetPersistenceFile(persist_file)

        wx.CallAfter(self.register_controls)

        if self.settings['dir_name'] != '':
            self.set_dir(self.settings['dir_name'])

        self.from_view = False

        self.frame.Centre()
        self.frame.Show()

        return True

    def InitFrame(self):
        self.frame = self.res.LoadFrame(None, 'MainFrame')
        self.frame.Bind(wx.EVT_CLOSE, self.OnClose)

        self.h_splitter = xrc.XRCCTRL(self.frame, 'HorizontalSplitter')

        self.view = WaveView(self.frame, -1, listener=self.frame)
        self.res.AttachUnknownControl('WaveView', self.view, self.frame)

        self.v_splitter = xrc.XRCCTRL(self.frame, 'VerticalSplitter')

        self.choice_type = xrc.XRCCTRL(self.frame, 'TypeChoice')
        self.choice_type.AppendItems([u'ポーズ', u'カット', u'固定ポーズ'])
        self.frame.Bind(wx.EVT_CHOICE, self.OnChoiceType, self.choice_type)

        self.table = xrc.XRCCTRL(self.frame, 'LabelsList')
        self.frame.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnLabelClick, self.table)

        self.list = xrc.XRCCTRL(self.frame, 'FileList')
        self.frame.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnWavClick, self.list)

        self.frame.Connect(-1, -1, EVT_CHANGE_CUR_ID, self.OnChangeCur)
        self.frame.Connect(-1, -1, EVT_CHANGE_SEL_ID, self.OnChangeSelectedLabel)
        self.frame.Connect(-1, -1, EVT_CHANGE_LBL_ID, self.OnChangeLabels)
        self.frame.Connect(-1, -1, EVT_EOF_ID, self.OnEOF)

        dd = DirDrop(self)
        self.frame.SetDropTarget(dd)

    def InitMenu(self):

        menu = []
        self.menu = menu

        menu += [{'name': 'MenuOpenDir', 'func': self.OnOpenDir, 'check': None}]
        menu += [{'name': 'MenuSaveLabels', 'func': self.OnSaveLabels, 'check': self.view.can_save}]
        menu += [{'name': 'MenuQuitApp', 'func': self.OnClose, 'check': None}]

        menu += [{'name': 'MenuUndo', 'func': self.OnUndo, 'check': self.view.can_undo}]
        menu += [{'name': 'MenuRedo', 'func': self.OnRedo, 'check': self.view.can_redo}]
        menu += [{'name': 'MenuInsert', 'func': self.OnInsert, 'check': self.view.can_insert_label}]
        menu += [{'name': 'MenuRemove', 'func': self.OnRemove, 'check': self.view.can_remove_label}]
        menu += [{'name': 'MenuCut', 'func': self.OnCut, 'check': self.view.can_cut}]
        menu += [{'name': 'MenuMergeLeft', 'func': self.OnMergeLeft, 'check': self.view.can_merge_left}]
        menu += [{'name': 'MenuMergeRight', 'func': self.OnMergeRight, 'check': self.view.can_merge_right}]
        menu += [{'name': 'MenuSettings', 'func': self.OnSettings, 'check': None}]

        menu += [{'name': 'MenuZoomIn', 'func': self.OnZoomIn, 'check': self.view.can_zoomin}]
        menu += [{'name': 'MenuZoomOut', 'func': self.OnZoomOut, 'check': self.view.can_zoomout}]

        menu += [{'name': 'MenuRefind', 'func': self.OnRefind, 'check': None}]
        menu += [{'name': 'MenuShift', 'func': self.OnShift, 'check': None}]
        menu += [{'name': 'MenuReverse', 'func': self.OnReverse, 'check': None}]

        menu += [{'name': 'MenuInsertPause', 'func': self.OnInsertPause, 'check': None}]

        self.menuBar = self.res.LoadMenuBar('MenuBar')
        self.frame.SetMenuBar(self.menuBar)

        for menu in self.menu:
            self.frame.Bind(wx.EVT_MENU, menu['func'], id=xrc.XRCID(menu['name']))

    def InitToolbar(self):
        if not self.settings['dsp_toolbar']:
            return

        tools = []
        self.tools = tools

        tools += [{'name': 'ToolHead', 'func': self.OnHead, 'dsp': 'dsp_head', 'check': self.view.can_head}]
        tools += [{'name': 'ToolPlay', 'func': self.OnPlay, 'dsp': 'dsp_play', 'check': self.view.can_play}]
        tools += [{'name': 'ToolPlayPause', 'func': self.OnPlayPause, 'dsp': 'dsp_playpause', 'check': self.view.can_pause_mode_play}]
        tools += [{'name': 'ToolPlayBorder', 'func': self.OnPlayBorder, 'dsp': 'dsp_playborder', 'check': self.view.can_play_border}]
        tools += [{'name': 'ToolPause', 'func': self.OnPause, 'dsp': 'dsp_pause', 'check': self.view.can_pause}]
        tools += [{'name': 'ToolTail', 'func': self.OnTail, 'dsp': 'dsp_tail', 'check': self.view.can_tail}]
        tools += [{'name': 'ToolZoomIn', 'func': self.OnZoomIn, 'dsp': 'dsp_zoomin', 'check': self.view.can_zoomin}]
        tools += [{'name': 'ToolZoomOut', 'func': self.OnZoomOut, 'dsp': 'dsp_zoomout', 'check': self.view.can_zoomout}]

        tools += [{'name': 'ToolCut', 'func': self.OnCut, 'dsp': 'dsp_cut', 'check': self.view.can_cut}]
        tools += [{'name': 'ToolMergeLeft', 'func': self.OnMergeLeft, 'dsp': 'dsp_mergeleft', 'check': self.view.can_merge_left}]
        tools += [{'name': 'ToolMergeRight', 'func': self.OnMergeRight, 'dsp': 'dsp_mergeright', 'check': self.view.can_merge_right}]
        tools += [{'name': 'ToolUndo', 'func': self.OnUndo, 'dsp': 'dsp_undo', 'check': self.view.can_undo}]
        tools += [{'name': 'ToolRedo', 'func': self.OnRedo, 'dsp': 'dsp_redo', 'check': self.view.can_redo}]
        tools += [{'name': 'ToolSaveLabels', 'func': self.OnSaveLabels, 'dsp': 'dsp_save', 'check': self.view.can_save}]
        tools += [{'name': 'ToolInsert', 'func': self.OnInsert, 'dsp': 'dsp_insert', 'check': self.view.can_insert_label}]
        tools += [{'name': 'ToolRemove', 'func': self.OnRemove, 'dsp': 'dsp_remove', 'check': self.view.can_remove_label}]

        self.toolBar = self.res.LoadToolBar(self.frame, 'ToolBar')

        for tool in tools:
            xrcid = xrc.XRCID(tool['name'])
            if self.settings[tool['dsp']]:
                self.frame.Bind(wx.EVT_TOOL, tool['func'], id=xrcid)
            else:
                self.toolBar.DeleteTool(xrcid)

        self.toolBar.Realize()

    def set_debug(self):
        if self.settings['debug']:
            revpause.DEBUG = True
            waveview.DEBUG = True

    def register_controls(self):
        self.frame.Freeze()
        self.register()
        self.frame.Thaw()

    def register(self, children=None):
        self.pm.RegisterAndRestore(self.frame)
        self.pm.RegisterAndRestore(self.table)
        self.pm.RegisterAndRestore(self.list)
        self.pm.RegisterAndRestore(self.h_splitter)
        self.pm.RegisterAndRestore(self.v_splitter)

    def set_enable(self):
        for menu in self.menu:
            if menu['check'] is not None:
                item = self.menuBar.FindItemById(xrc.XRCID(menu['name']))
                item.Enable(menu['check']())

        if self.settings['dsp_toolbar']:
            for tool in self.tools:
                if self.settings[tool['dsp']]:
                    self.toolBar.EnableTool(xrc.XRCID(tool['name']), tool['check']())

    def confirm_save(self):
        if self.view.can_save():
            dlg = wx.MessageDialog(self.frame, u'変更を保存しますか？', u'確認',  wx.YES_NO)
            response = dlg.ShowModal()
            dlg.Destroy()

            if response == wx.ID_YES:
                self.view.save()
                self.set_enable()
            else:
                return False

        return True

    def set_dir(self, dir_name):
        self.confirm_save()

        self.settings['dir_name'] = dir_name

        self.list.ClearAll()
        self.list.InsertColumn(0, u'音声')
        self.list.InsertColumn(1, u'ラベル')

        wav_files = []

        for name in os.listdir(dir_name):
            if name.endswith('.wav'):
                wav_files.append(name)

        if len(wav_files) == 0:
            self.settings['list_index'] = 0
            return

        labels_dir = os.path.join(dir_name, LABELS_DIR)
        if not os.path.exists(labels_dir):
            os.mkdir(labels_dir)

        wav_files.sort()

        for i, name in enumerate(wav_files):
            index = self.list.InsertStringItem(i, name)
            self.list.SetStringItem(index, 1, '%03d.txt' % (i + 1))

        list_index = self.settings['list_index']
        list_index = max(0, min(list_index,
                                     self.list.ItemCount - 1))
        self.settings['list_index'] = list_index

        self.list.Select(list_index)

        wav_name = self.list.GetItem(list_index, 0).GetText()
        wav_file = os.path.join(dir_name,  wav_name)

        labels_name = self.list.GetItem(list_index, 1).GetText()
        labels_file = os.path.join(dir_name, LABELS_DIR, labels_name)

        self.set_sound(wav_file, labels_file)

    def set_sound(self, wav_file, labels_file):
        if not self.view.set_sound(wav_file):
            return

        if not os.path.exists(labels_file):
            sil_lv = self.settings['sil_lv']
            sil_dur = self.settings['sil_dur']
            before_dur = self.settings['label_before_dur']
            after_dur = self.settings['label_after_dur']
            rate = self.settings['rate']
            snd_dur = self.settings['snd_dur']

            labels = find_sound(wav_file, sil_lv, sil_dur, before_dur, after_dur, rate, snd_dur)
            labels.write(labels_file)

        self.view.set_labels(labels_file)
        self.view.sil_lv = self.settings['sil_lv']

        wav_name = os.path.basename(wav_file)
        self.frame.Title = wav_name

        self.set_labels()

        self.set_enable()

    def set_labels(self):
        self.table.ClearAll()
        self.table.InsertColumn(COL_START + 1, u'開始', wx.LIST_FORMAT_RIGHT)
        self.table.InsertColumn(COL_END + 1, u'終了', wx.LIST_FORMAT_RIGHT)
        self.table.InsertColumn(COL_TYPE + 1, u'種別')
        self.table.InsertColumn(COL_DUR + 1, u'実効時間', wx.LIST_FORMAT_RIGHT)
        #self.table.InsertColumn(COL_TEXT + 1, u'テキスト')

        labels = self.view.get_labels()

        factor = self.settings['factor']
        add = self.settings['add']

        for label in labels:
            index = self.table.InsertStringItem(sys.maxint, '')
            self.table.SetStringItem(index, COL_START, '%.2f' % label.start)
            self.table.SetStringItem(index, COL_END, '%.2f' % label.end)

            lbl = 'unknown'
            dur = 0

            if label.is_cut():
                lbl = u'カット'
                dur = label.dur
            elif label.is_spec():
                lbl = u'固定ポーズ'
                dur = label.dur
            elif label.is_pause():
                lbl = u'ポーズ'
                dur = label.dur * factor + add

            self.table.SetStringItem(index, COL_TYPE, lbl)
            self.table.SetStringItem(index, COL_DUR, '%.2f' % dur)

        self.choice_type.Enable(False)

        self.set_enable()

    def OnOpenDir(self, evt):
        dlg = wx.DirDialog(self.frame, u'音声ファイルが入ったフォルダの選択',
                style=wx.DD_DEFAULT_STYLE
                | wx.DD_DIR_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            self.settings['list_index'] = 0
            self.set_dir(dlg.GetPath())
        dlg.Destroy()

    def OnShift(self, evt):
        if not self.confirm_save():
            return

        dlg = self.res.LoadDialog(self.frame, 'ShiftLabelsDialog')

        nc_shift = masked.numctrl.NumCtrl(dlg)
        nc_shift.SetIntegerWidth(3)
        nc_shift.SetMin(-1000)
        nc_shift.SetMax(1000)
        nc_shift.SetLimited(True)
        self.res.AttachUnknownControl('TextShift', nc_shift, dlg)

        btn_shift = dlg.FindWindowByName('ButtonRunShift')
        btn_shift.SetId(wx.ID_OK)
        btn_cancel = dlg.FindWindowByName('ButtonCancelShift')
        btn_cancel.SetId(wx.ID_CANCEL)

        result = dlg.ShowModal()

        if result == wx.ID_OK:
            radio_all = dlg.FindWindowByName('RadioShiftAll')
            shift = 0
            try:
                shift = int(nc_shift.Value)
            except:
                wx.MessageBox(u'数値を入力してください。', u'メッセージ', wx.OK)
                return

            if shift == 0:
                wx.MessageBox(u'0以外の値を入力してください。', u'メッセージ', wx.OK)
                return

            self.shift_labels(radio_all.Value, shift / 1000.0)

    def shift_labels(self, is_all, shift):
        dir_name = self.settings['dir_name']
        list_index = self.settings['list_index']

        labels_dir = os.path.join(dir_name, LABELS_DIR)
        if not os.path.exists(labels_dir):
            wx.MessageBox(u'ポーズ情報フォルダがありません。', u'メッセージ', wx.OK)
            return

        labels_files = []
        cur_labels_file = os.path.join(labels_dir, '%03d.txt' % (list_index + 1))

        if is_all:
            for i in range(self.list.ItemCount):
                labels_file = os.path.join(labels_dir, '%03d.txt' % (i + 1))
                if not os.path.exists(labels_file):
                    wx.MessageBox(u'ポーズ情報ファイル「%s」がありません。' % labels_file, u'メッセージ', wx.OK)
                    return
                labels_files += [labels_file]
        else:
            if not os.path.exists(cur_labels_file):
                wx.MessageBox(u'ポーズ情報ファイル「%s」がありません。' % cur_labels_file, u'メッセージ', wx.OK)
                return
            labels_files += [cur_labels_file]

        for labels_file in labels_files:
            labels = Labels(open(labels_file, 'r').readlines())
            labels.shift(shift)
            labels.write(labels_file)

        self.view.set_labels(cur_labels_file)

        wx.MessageBox(u'ラベルのずらしが完了しました。', u'メッセージ', wx.OK)

    def OnSettings(self, evt):
        dlg = self.res.LoadObject(self.frame, 'SettingsDialog', 'wxPropertySheetDialog')

        sld_sil_lv = dlg.FindWindowByName('SilLvSlider')
        sld_sil_lv.Value = self.settings['sil_lv']

        nc_sil_dur = masked.numctrl.NumCtrl(dlg)
        nc_sil_dur.SetAllowNegative(False)
        nc_sil_dur.SetIntegerWidth(1)
        nc_sil_dur.SetFractionWidth(2)
        nc_sil_dur.SetValue(self.settings['sil_dur'])
        nc_sil_dur.SetMin(SIL_DUR_MIN)
        nc_sil_dur.SetMax(SIL_DUR_MAX)
        nc_sil_dur.SetLimited(True)
        self.res.AttachUnknownControl('TextSilDur', nc_sil_dur, dlg)

        nc_factor = masked.numctrl.NumCtrl(dlg)
        nc_factor.SetAllowNegative(False)
        nc_factor.SetIntegerWidth(1)
        nc_factor.SetFractionWidth(2)
        nc_factor.SetValue(self.settings['factor'])
        nc_factor.SetMin(FACTOR_MIN)
        nc_factor.SetMax(FACTOR_MAX)
        nc_factor.SetLimited(True)
        self.res.AttachUnknownControl('TextFactor', nc_factor, dlg)

        nc_add = masked.numctrl.NumCtrl(dlg)
        nc_add.SetAllowNegative(False)
        nc_add.SetIntegerWidth(1)
        nc_add.SetFractionWidth(2)
        nc_add.SetValue(self.settings['add'])
        nc_add.SetMin(ADD_MIN)
        nc_add.SetMax(ADD_MAX)
        nc_add.SetLimited(True)
        self.res.AttachUnknownControl('TextAdd', nc_add, dlg)

        nc_seek = masked.numctrl.NumCtrl(dlg)
        nc_seek.SetAllowNegative(False)
        nc_seek.SetIntegerWidth(3)
        nc_seek.SetValue(self.settings['seek'])
        nc_seek.SetMin(1)
        nc_seek.SetMax(999)
        nc_seek.SetLimited(True)
        self.res.AttachUnknownControl('TextSeek', nc_seek, dlg)

        nc_seek_ctrl = masked.numctrl.NumCtrl(dlg)
        nc_seek_ctrl.SetAllowNegative(False)
        nc_seek_ctrl.SetIntegerWidth(3)
        nc_seek_ctrl.SetValue(self.settings['seek_ctrl'])
        nc_seek_ctrl.SetMin(1)
        nc_seek_ctrl.SetMax(999)
        nc_seek_ctrl.SetLimited(True)
        self.res.AttachUnknownControl('TextSeekCtrl', nc_seek_ctrl, dlg)

        nc_seek_shift = masked.numctrl.NumCtrl(dlg)
        nc_seek_shift.SetAllowNegative(False)
        nc_seek_shift.SetIntegerWidth(3)
        nc_seek_shift.SetValue(self.settings['seek_shift'])
        nc_seek_shift.SetMin(1)
        nc_seek_shift.SetMax(999)
        nc_seek_shift.SetLimited(True)
        self.res.AttachUnknownControl('TextSeekShift', nc_seek_shift, dlg)

        dsp_list = ['dsp_toolbar', 'dsp_head', 'dsp_play', 'dsp_playpause', 'dsp_playborder', 'dsp_pause',
                'dsp_tail', 'dsp_zoomin', 'dsp_zoomout', 'dsp_cut', 'dsp_mergeleft',
                'dsp_mergeright', 'dsp_undo', 'dsp_redo', 'dsp_save', 'dsp_insert', 'dsp_remove']

        for dsp in dsp_list:
            chk_dsp = dlg.FindWindowByName(dsp)
            chk_dsp.Value = self.settings[dsp]

        result = dlg.ShowModal()

        if result == wx.ID_OK:
            self.settings['sil_lv'] = sld_sil_lv.Value
            self.view.sil_lv = self.settings['sil_lv']

            sil_dur = self.get_nc_float(nc_sil_dur, 1.3)
            self.settings['sil_dur'] = sil_dur

            factor = self.get_nc_float(nc_factor, 1.2)
            self.settings['factor'] = factor

            add = self.get_nc_float(nc_add, 0.5)
            self.settings['add'] = add

            seek = self.get_nc_int(nc_seek, 1)
            self.settings['seek'] = seek

            seek_ctrl = self.get_nc_int(nc_seek_ctrl, 1)
            self.settings['seek_ctrl'] = seek_ctrl

            seek_shift = self.get_nc_int(nc_seek_shift, 1)
            self.settings['seek_shift'] = seek_shift

            self.view.set_seek(seek, seek_ctrl, seek_shift)

            for dsp in dsp_list:
                chk_dsp = dlg.FindWindowByName(dsp)
                self.settings[dsp] = chk_dsp.Value

    def get_nc_int(self, nc, def_val):
        val = def_val
        try:
            val = int(nc.Value)
        except:
            pass
        return val

    def get_nc_float(self, nc, def_val):
        val = def_val
        try:
            val = float(nc.Value)
        except:
            pass
        return val

    def OnChoiceType(self, evt):
        i = self.table.GetFirstSelected()
        if i == -1:
            return

        labels = self.view.get_labels()

        if len(labels) <= i:
            return

        label = labels[i]

        if evt.Selection == 0:
            if label.is_pause() and not label.is_spec():
                return
        elif evt.Selection == 1:
            if label.is_cut():
                return
        elif evt.Selection == 2:
            if label.is_spec():
                return
        else:
            return

        self.view.ml.save()

        labels = self.view.get_labels()
        label = labels[i]

        if evt.Selection == 0:
            label.change_to_pause()
        elif evt.Selection == 1:
            label.change_to_cut()
        elif evt.Selection == 2:
            label.change_to_spec(self.settings['factor'], self.settings['add'])

        self.view.UpdateDrawing()

        self.set_labels()

    def OnChangeSelectedLabel(self, evt):
        self.from_view = True
        self.table.Select(self.view.get_selected_label())
        self.set_enable()

    def OnChangeLabels(self, evt):
        self.set_labels()

    def OnLabelClick(self, evt):
        if self.from_view:
            self.from_view = False
            return

        self.view.set_selected_label(evt.m_itemIndex)

        lbl_type = self.table.GetItem(evt.m_itemIndex, COL_TYPE).GetText()
        if lbl_type == u'ポーズ':
            self.choice_type.Select(0)
        elif lbl_type == u'カット':
            self.choice_type.Select(1)
        elif lbl_type == u'固定ポーズ':
            self.choice_type.Select(2)

        self.choice_type.Enable(True)

        self.set_enable()

    def OnWavClick(self, evt):
        self.confirm_save()

        dir_name = self.settings['dir_name']

        wav_file = os.path.join(dir_name, evt.GetText())
        labels_file = self.list.GetItem(evt.m_itemIndex, 1).GetText()
        labels_file = os.path.join(dir_name, LABELS_DIR, labels_file)
        self.settings['list_index'] = evt.m_itemIndex

        self.set_sound(wav_file, labels_file)

    def OnRefind(self, evt):
        sil_lv = self.settings['sil_lv']
        sil_dur = self.settings['sil_dur']
        before_dur = self.settings['label_before_dur']
        after_dur = self.settings['label_after_dur']

        self.view.find(sil_lv, sil_dur, before_dur, after_dur)

        self.set_labels()

    def OnReverse(self, evt):
        not_found = False

        dir_name = self.settings['dir_name']

        rev_dir = os.path.join(dir_name, REVERSE_DIR)
        rev_names = []

        if not os.path.exists(rev_dir):
            os.mkdir(rev_dir)
            not_found = True
        else:
            for name in os.listdir(rev_dir):
                if name.endswith('.wav'):
                    rev_names.append(name)
            rev_names.sort()

            if len(rev_names) == 0:
                not_found = True

        if not_found:
            wx.MessageBox(u'ここに手作業でつくったポーズ付きwavを入れてください\n%s' %
                          rev_dir, u'やほ', wx.OK)
            return

        wav_files = []

        for i in range(self.list.ItemCount):
            wav_name = self.list.GetItem(i, 0).GetText()
            wav_file = os.path.join(dir_name, wav_name)
            wav_files.append(wav_file)

        if len(wav_files) != len(rev_names):
            wx.MessageBox(u'wavの数(%d)とreverseの数(%d)が違います' %
                          (len(wav_files), len(rev_names)), u'^^', wx.OK)
            return

        dlg = wx.MessageDialog(self.frame, u'ポーズ情報が上書きされますが' +
                               u'よろしいでしょうか？', u'確認',  wx.YES_NO)
        response = dlg.ShowModal()
        dlg.Destroy()

        if response == wx.ID_NO:
            return

        dlg = wx.MessageDialog(self.frame, u'すべてのファイルのポーズを探しますか？' +
                               u'\n「いいえ」なら表示されているファイルのみ',
                               u'何度も確認して申し訳ございません',  wx.YES_NO)
        response = dlg.ShowModal()
        dlg.Destroy()

        rev_files = []

        list_index = self.settings['list_index']

        if response == wx.ID_NO:
            rev_name = rev_names[list_index]
            rev_file = os.path.join(dir_name, REVERSE_DIR, rev_name)
            rev_files.append(rev_file)
            wav_files = [wav_files[list_index]]
        else:
            for rev_name in rev_names:
                rev_file = os.path.join(dir_name, REVERSE_DIR, rev_name)
                rev_files.append(rev_file)

        dlg = wx.ProgressDialog(u'ポーズ情報作成',
                                u'ポーズ情報作成中\n残りファイル数%d' %
                                len(wav_files), maximum=len(wav_files),
                                parent=self.frame,
                                style=wx.PD_AUTO_HIDE | wx.PD_APP_MODAL)

        error_files = []

        fit_mod = True
        rev_spec = self.settings['rev_spec']
        rev_sil_lv = self.settings['rev_sil_lv']
        rev_sil_dur = self.settings['rev_sil_dur']
        rev_rate = self.settings['rev_rate']
        before_dur = self.settings['label_before_dur']
        after_dur = self.settings['label_after_dur']

        if rev_spec:
            fit_mod = False

        for i, (wav_file, rev_file) in \
                enumerate(zip(wav_files, rev_files)):
            dlg.Update(i + 1, u'ポーズ情報作成中\n残りファイル数%d' %
                       (len(wav_files) - i))

            try:
                result = rev_pause(wav_file, rev_file, rev_sil_lv,
                        rev_sil_dur, rev_rate,
                        before_dur, after_dur, fit_mod)
            except Exception as e:
                print e.message
                result = [[], True]
            labels, err = result
            labels_name = '%03d.txt' % (i + 1)
            labels_file = os.path.join(dir_name, LABELS_DIR, labels_name)
            labels.write(labels_file)

            if err:
                error_files.append(os.path.basename(wav_file))

        dlg.Destroy()

        if len(error_files) != 0:
            error_file = os.path.join(dir_name, ERROR_FILE)
            if os.name == 'nt':
                f = codecs.open(error_file, 'w', 'CP932')
            else:
                f = codecs.open(error_file, 'w', 'utf8')
            for ef in error_files:
                f.write(ef + '\n')
            f.close()
            msg = u'%d個のファイルが検索に失敗しました。\n' + \
                  u'ここに検索に失敗したファイルが書いてあります\n%s'
            wx.MessageBox(msg % (len(error_files), error_file), u'失敗', wx.OK)
        else:
            wx.MessageBox(u'完了しました', u'メッセージ', wx.OK)

        labels_file = self.list.GetItem(list_index, 1).GetText()
        labels_file = os.path.join(dir_name, LABELS_DIR, labels_file)
        self.view.set_labels(labels_file)
        self.set_labels()

    def OnInsertPause(self, evt):
        if not self.confirm_save():
            return

        dir_name = self.settings['dir_name']

        pause_dir = os.path.join(dir_name, PAUSE_DIR)
        if not os.path.exists(pause_dir):
            os.mkdir(pause_dir)

        dlg = wx.MessageDialog(self.frame, u'すべてのファイルにポーズをつけますか？' +
                               u'\n「いいえ」なら表示されているファイルのみ',
                               u'確認',  wx.YES_NO)
        response = dlg.ShowModal()
        dlg.Destroy()

        wav_names = []
        labels_names = []

        list_index = self.settings['list_index']

        if response == wx.ID_NO:
            wav_names.append(self.list.GetItem(list_index, 0).GetText())
            labels_names.append(
                self.list.GetItem(list_index, 1).GetText())
        else:
            for i in range(self.list.ItemCount):
                wav_names.append(self.list.GetItem(i, 0).GetText())
                labels_names.append(self.list.GetItem(i, 1).GetText())

        dlg = wx.ProgressDialog(u'ポーズファイル作成',
                                u'ポーズファイル作成中\n残りファイル数%d' %
                                len(wav_names), maximum=len(wav_names),
                                parent=self.frame,
                                style=wx.PD_AUTO_HIDE | wx.PD_APP_MODAL)

        sil_lv = self.settings['sil_lv']
        sil_dur = self.settings['sil_dur']
        before_dur = self.settings['label_before_dur']
        after_dur = self.settings['label_after_dur']
        rate = self.settings['rate']
        snd_dur = self.settings['snd_dur']
        factor = self.settings['factor']
        add = self.settings['add']

        for i, (wav, labels) in enumerate(zip(wav_names, labels_names)):
            dlg.Update(i, u'ポーズファイル作成中\n残りファイル数%d' %
                       (len(wav_names) - i))

            wav_file = os.path.join(dir_name, wav)
            labels_file = os.path.join(dir_name, LABELS_DIR, labels)
            pause_file = os.path.join(dir_name, PAUSE_DIR, wav)

            if not os.path.exists(labels_file):
                labels = find_sound(wav_file, sil_lv, sil_dur,
                    before_dur, after_dur, rate, snd_dur)
                labels.write(labels_file)

            insert_pause(wav_file, pause_file, labels_file, factor, add)

        dlg.Destroy()

        pause_dir = os.path.join(dir_name, PAUSE_DIR)
        wx.MessageBox(u'このフォルダにできています\n%s' % pause_dir, u'完了', wx.OK)

    def OnInsert(self, evt):
        self.view.insert_label()
        self.set_enable()

    def OnRemove(self, evt):
        self.view.remove_label()
        self.set_enable()

    def OnSaveLabels(self, evt):
        self.view.save()
        self.set_enable()

    def OnHead(self, evt):
        self.view.head()
        self.set_enable()
        if self.view.playing:
            self.toolBar.EnableTool(xrc.XRCID('ToolHead'), True)

    def OnPlay(self, evt):
        self.view.play()
        self.set_enable()
        self.toolBar.EnableTool(xrc.XRCID('ToolHead'), True)

    def OnPlayPause(self, evt):
        factor = self.settings['factor']
        add = self.settings['add']
        self.view.pause_mode_play(factor, add)
        self.set_enable()
        self.toolBar.EnableTool(xrc.XRCID('ToolHead'), True)

    def OnPlayBorder(self, evt):
        self.view.play_border()
        self.set_enable()
        self.toolBar.EnableTool(xrc.XRCID('ToolHead'), True)

    def OnPause(self, evt):
        self.view.pause()
        self.set_enable()

    def OnTail(self, evt):
        self.view.tail()
        self.set_enable()

    def OnZoomIn(self, evt):
        self.view.zoom_in()
        self.set_enable()

    def OnZoomOut(self, evt):
        self.view.zoom_out()
        self.set_enable()

    def OnCut(self, evt):
        self.view.cut()
        self.set_enable()

    def OnMergeLeft(self, evt):
        self.view.merge_left()
        self.set_enable()

    def OnMergeRight(self, evt):
        self.view.merge_right()
        self.set_enable()

    def OnUndo(self, evt):
        self.view.undo()
        self.set_enable()

    def OnRedo(self, evt):
        self.view.redo()
        self.set_enable()

    def OnChangeCur(self, evt):
        self.set_enable()

    def OnEOF(self, evt):
        self.set_enable()

    def OnClose(self, evt):
        self.confirm_save()

        self.settings.write_conf()

        self.pm.SaveAndUnregister()

        self.view.cancel()

        self.frame.Destroy()


class DirDrop(wx.FileDropTarget):
    def __init__(self, window):
        wx.FileDropTarget.__init__(self)
        self.window = window

    def OnDropFiles(self, x, y, names):
        if len(names) == 1:
            if os.path.isdir(names[0]):
                self.window.settings['list_index'] = 0
                self.window.set_dir(names[0])
            else:
                self.window.settings['list_index'] = 0
                self.window.set_dir(os.path.dirname(names[0]))


if __name__ == '__main__':
    main()
