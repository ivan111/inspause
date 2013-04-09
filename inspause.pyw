# -*- coding: utf-8 -*-

'''
InsPause メイン
'''

__author__  = 'vanya'
__version__ = '2.0.0'
__date__    = '2013-04-08'


import os
import sys

import wx
import wx.lib.masked as masked
from wx import xrc
import wx_utils

import persist

from autolabels import AutoLabels
from labels import Labels
from labelswindow import EVT_LBL_CHANGED_ID
from myfile import get_wav_file_list, get_labels_file_list, get_ext, \
        get_labels_dir_d, get_pause_dir_d, get_labels_file_d, get_labels_file_f, DIR_LABELS
from mywave import MyWave, auto_shift_diff_s
from settings import *
from volumewindow import MIN_SCALE, EVT_CLICK_CUR_CHANGED_ID
from waveview import *


APP_NAME = 'InsPause'
XRC_FILE = 'inspause.xrc'  # GUI 設定ファイル

MIN_SIZE = 150


def main(persist_file):
    app = InsPause(redirect=True, filename='log.txt')
    app.set_persist(persist_file)
    app.MainLoop()


class InsPause(wx.App):

    binder = wx_utils.bind_manager()

    #--------------------------------------------------------------------------
    # 初期化

    def OnInit(self):
        self.init_instance_var()

        self.settings = Settings()
        self.settings.read_conf()

        self.res = xrc.XmlResource(XRC_FILE)

        self.init_frame()

        self.binder.parent = self.frame
        self.binder.bindall(self)

        self.al = AutoLabels()

        self.set_icon()

        wav_files = get_wav_file_list(self.dir_snd)

        if wav_files:
            self.update_flist()
        else:
            self.OnOpenDir(None)

        self.frame.Centre()
        self.frame.Show()

        return True


    def init_instance_var(self):
        self.settings   = None  # 設定
        self.res        = None  # GUI のリソース
        self.pm         = None  # persist（ウィンドウ位置やサイズを保持するためのクラス）管理
        self.al         = None  # 用意されたラベル情報

        self.dir_changed = True

        self.info_list = []  # 用意されたポーズ情報のリスト

        # ---- GUI 部品
        self.frame          = None  # フレーム
        self.view           = None  # 音声表示
        self.flist          = None  # ファイル一覧
        self.h_splitter     = None  # 水平スプリッタ
        self.v_splitter     = None  # 垂直スプリッタ

        self.win_settings   = None  # 左下に表示されている設定パネル
        self.cmb_auto_pause = None  # 用意されたポーズ情報コンボボックス
        self.btn_auto_pause = None  # 用意されたポーズ情報ボタン


    def init_frame(self):
        self.frame = self.res.LoadFrame(None, 'MainFrame')
        self.frame.Title = APP_NAME

        self.h_splitter = xrc.XRCCTRL(self.frame, 'HorizontalSplitter')

        # ---- 波形

        self.view = WaveView(self.frame, -1, listener=self)
        self.view.view_factor = self.settings['view_factor']
        self.view.scale       = self.settings['scale']
        self.view.factor      = self.settings['factor']
        self.view.add         = self.settings['add']
        self.res.AttachUnknownControl('WaveView', self.view, self.frame)

        self.v_splitter = xrc.XRCCTRL(self.frame, 'VerticalSplitter')


        # ---- 設定項目

        self.win_settings = xrc.XRCCTRL(self.frame, 'SettingsWindow')
        self.set_scroll(self.win_settings)

        # -------- 「表示範囲」スライダー
        disp_slider = xrc.XRCCTRL(self.frame, 'DispSlider')
        disp_slider.Value = self.settings['scale']

        # -------- ポーズ時間 = 範囲 * これ + add
        nc = self.create_numctrl(self.settings['factor'], FACTOR_MIN, FACTOR_MAX)
        self.res.AttachUnknownControl('TextFactor', nc, self.frame)

        # -------- ポーズ時間 = 範囲 * factor + これ
        nc = self.create_numctrl(self.settings['add'], ADD_MIN, ADD_MAX)
        self.res.AttachUnknownControl('TextAdd', nc, self.frame)

        # -------- 用意されたポーズ情報

        # コンボボックス
        self.cmb_auto_pause = xrc.XRCCTRL(self.frame, 'CmbAutoPause')

        # 「使用」ボタン
        self.btn_auto_pause = xrc.XRCCTRL(self.frame, 'BtnAutoPause')


        # ---- 色

        color_win = xrc.XRCCTRL(self.frame, 'ColorWindow')
        self.set_scroll(color_win)

        sld_r = xrc.XRCCTRL(self.frame, 'BGSliderR')
        sld_g = xrc.XRCCTRL(self.frame, 'BGSliderG')
        sld_b = xrc.XRCCTRL(self.frame, 'BGSliderB')

        sld_r.Value = self.settings['bg_r']
        sld_g.Value = self.settings['bg_g']
        sld_b.Value = self.settings['bg_b']

        sld_r = xrc.XRCCTRL(self.frame, 'FGSliderR')
        sld_g = xrc.XRCCTRL(self.frame, 'FGSliderG')
        sld_b = xrc.XRCCTRL(self.frame, 'FGSliderB')

        sld_r.Value = self.settings['fg_r']
        sld_g.Value = self.settings['fg_g']
        sld_b.Value = self.settings['fg_b']

        self.set_bg_color()
        self.set_fg_color()


        # ---- ファイルリスト

        self.flist = xrc.XRCCTRL(self.frame, 'FileList')

        self.flist.InsertColumn(0, u'音声')

        self.flist.SetColumnWidth(0, 200)

        self.Connect(-1, -1, EVT_CLICK_CUR_CHANGED_ID, self.OnClickCurChanged)
        self.Connect(-1, -1, EVT_EOF_ID,               self.OnEOF)
        self.Connect(-1, -1, EVT_LBL_CHANGED_ID,       self.OnLabelChanged)

        dd = DirDrop(self)
        self.frame.SetDropTarget(dd)


        # ---- メニューバーの設定

        self.menu = self.res.LoadMenuBar('MenuBar')
        self.frame.SetMenuBar(self.menu)

        # ----

        self.init_toolbar()
        self.set_enable()


    def set_scroll(self, ctrl):
        w, h = ctrl.Size
        su = 20
        ctrl.SetScrollbars(su, su, w, su, h / su)


    def init_toolbar(self):
        tools = []
        self.tools = tools

        tools += [{'name': 'ToolHead',       'check': self.view.can_head}]
        tools += [{'name': 'ToolPlay',       'check': self.view.can_play}]
        tools += [{'name': 'ToolPlayPause',  'check': self.view.can_pause_mode_play}]
        tools += [{'name': 'ToolPause',      'check': self.view.can_pause}]
        tools += [{'name': 'ToolTail',       'check': self.view.can_tail}]
        tools += [{'name': 'ToolZoomIn',     'check': self.view.can_zoomin}]
        tools += [{'name': 'ToolZoomOut',    'check': self.view.can_zoomout}]

        tools += [{'name': 'ToolCut',        'check': self.view.can_cut}]
        tools += [{'name': 'ToolMergeLeft',  'check': self.view.can_merge_left}]
        tools += [{'name': 'ToolMergeRight', 'check': self.view.can_merge_right}]
        tools += [{'name': 'ToolUndo',       'check': self.view.can_undo}]
        tools += [{'name': 'ToolRedo',       'check': self.view.can_redo}]
        tools += [{'name': 'ToolSaveLabels', 'check': self.view.can_save}]
        tools += [{'name': 'ToolInsert',     'check': self.view.can_insert_label}]
        tools += [{'name': 'ToolRemove',     'check': self.view.can_remove_label}]

        self.tool_bar = self.res.LoadToolBar(self.frame, 'ToolBar')
        self.tool_bar.Realize()


    def set_icon(self):
        try:
            icon = wx.Icon('myicon.ico', wx.BITMAP_TYPE_ICO)
            self.frame.SetIcon(icon)
        except:
            pass

        if sys.platform == 'win32':
            try:
                handle = win32api.GetModuleHandle(None)
                exeName = win32api.GetModuleFileName(handle)
                icon = wx.Icon(exeName, wx.BITMAP_TYPE_ICO)

                self.frame.SetIcon(icon)
            except:
                pass


    # persist （ウィンドウのサイズや最大化の保持）関連

    def set_persist(self, persist_file):
        self.pm = persist.PersistenceManager.Get()
        self.pm.SetPersistenceFile(persist_file)

        wx.CallAfter(self.register_controls)


    def register_controls(self):
        self.frame.Freeze()
        self.register()
        self.frame.Thaw()


    def register(self, children=None):
        self.pm.RegisterAndRestore(self.frame)
        self.pm.RegisterAndRestore(self.flist)
        self.pm.RegisterAndRestore(self.h_splitter)
        self.pm.RegisterAndRestore(self.v_splitter)


    #--------------------------------------------------------------------------

    def set_enable(self):
        '''
        ツールバーやコントロールの有効・無効を設定する
        '''

        # ---- メニュー
        item = self.menu.FindItemById(xrc.XRCID('MenuSave'))
        item.Enable(self.view.can_save())

        # ---- ツールバー
        for tool in self.tools:
            self.tool_bar.EnableTool(xrc.XRCID(tool['name']), tool['check']())

        # ---- 設定コントロール
        if self.view.playing or self.view.wav is None:
            self.win_settings.Enabled = False
            self.menu.EnableTop(1, False)  # 「ポーズ再検索」メニュー
        else:
            self.win_settings.Enabled = True
            self.menu.EnableTop(1, True)  # 「ポーズ再検索」メニュー


        # ---- 用意されたポーズ情報
        if self.cmb_auto_pause.Count == 0 or not self.win_settings.Enabled:
            self.cmb_auto_pause.Enabled = False
            self.btn_auto_pause.Enabled = False
        else:
            self.cmb_auto_pause.Enabled = True
            if self.cmb_auto_pause.Value != '':
                self.btn_auto_pause.Enabled = True
            else:
                self.btn_auto_pause.Enabled = False


    def set_bg_color(self):
        sld_r = xrc.XRCCTRL(self.frame, 'BGSliderR')
        sld_g = xrc.XRCCTRL(self.frame, 'BGSliderG')
        sld_b = xrc.XRCCTRL(self.frame, 'BGSliderB')
        rgb   = xrc.XRCCTRL(self.frame, 'LblBGRGB')
        rgb.Label = '#%02X%02X%02X' % (sld_r.Value, sld_g.Value, sld_b.Value)
        self.view.bg_color = rgb.Label

        self.settings['bg_r'] = sld_r.Value
        self.settings['bg_g'] = sld_g.Value
        self.settings['bg_b'] = sld_b.Value


    def set_fg_color(self):
        sld_r = xrc.XRCCTRL(self.frame, 'FGSliderR')
        sld_g = xrc.XRCCTRL(self.frame, 'FGSliderG')
        sld_b = xrc.XRCCTRL(self.frame, 'FGSliderB')
        rgb   = xrc.XRCCTRL(self.frame, 'LblFGRGB')
        rgb.Label = '#%02X%02X%02X' % (sld_r.Value, sld_g.Value, sld_b.Value)
        self.view.fg_color = rgb.Label

        self.settings['fg_r'] = sld_r.Value
        self.settings['fg_g'] = sld_g.Value
        self.settings['fg_b'] = sld_b.Value


    def confirm_save(self):
        '''
        保存を確認する
        '''

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


    def update_flist(self):
        '''
        音声ファイル一覧画面を更新する
        '''

        self.confirm_save()

        self.flist.DeleteAllItems()

        wav_files = get_wav_file_list(self.dir_snd)

        if not wav_files:
            self.settings['list_index'] = 0
            self.view.wav = None
            self.set_enable()
            return

        wav_files.sort()

        for i, name in enumerate(wav_files):
            index = self.flist.InsertStringItem(i, name)

        list_index = self.settings['list_index']
        list_index = max(0, min(list_index, self.flist.ItemCount - 1))
        self.settings['list_index'] = list_index

        self.flist.Select(list_index)
        self.flist.EnsureVisible(list_index)


    def set_sound(self, wav_file, labels_file, first=False):
        '''
        波形画面に音声を設定する

        @param first 音声ディレクトリ変更後、最初のオープンか？
        '''

        if self.view.playing:
            self.view.pause()
            self.set_enable()

        dlg = wx.ProgressDialog(u'読込', u'音声ファイルを読み込み中', parent=self.frame)

        wav = MyWave(wav_file, labels_file, dlg)

        dlg.Destroy()

        if wav.err_msg:
            wx.MessageBox(wav.err_msg)
            self.view.wav = None
            self.set_enable()
            return

        self.info_list = []

        if first:
            self.auto_detect_labels(wav)

        self.view.wav = wav

        wav_name = os.path.basename(wav_file)
        self.frame.Title = wav_name + ' - ' + APP_NAME

        self.set_enable()


    def auto_detect_labels(self, wav):
        '''
        用意されたラベルが使えるなら使えるようにする
        '''

        wav_files = get_wav_file_list(self.dir_snd)
        num_waves = len(wav_files)

        self.info_list = self.al.auto_detect(num_waves, wav.distinction_s, self.settings['list_index'])

        if not self.info_list:
            return

        self.cmb_auto_pause.Clear()

        for info in self.info_list:
            self.cmb_auto_pause.Append(info.name, info)


    def get_music_dir(self):
        '''
        ミュージックフォルダを取得する
        '''

        music_dir = ''

        if sys.platform == 'win32':
            try:
                import ctypes
                from ctypes.wintypes import MAX_PATH

                dll = ctypes.windll.shell32
                buf = ctypes.create_unicode_buffer(MAX_PATH + 1)

                if dll.SHGetSpecialFolderPathW(None, buf, 0x000d, False):  # MyMusic フォルダ
                    music_dir = buf.value
            except:
                pass

        return music_dir


    def insert_pause(self, is_all):
        '''
        ポーズファイルを作成する
        '''

        if not self.confirm_save():
            return

        wav_names = []
        labels_names = []

        list_index = self.settings['list_index']

        if not is_all:
            # このファイルのみ

            wav_names.append(self.flist.GetItem(list_index, 0).GetText())
            labels_file = get_labels_file_d(self.dir_snd, list_index + 1)
            labels_names.append(labels_file)
        else:
            # すべてのファイル

            for i in range(self.flist.ItemCount):
                wav_names.append(self.flist.GetItem(i, 0).GetText())
                labels_file = get_labels_file_d(self.dir_snd, i + 1)
                labels_names.append(labels_file)

        msg = u'ポーズ挿入中 %d / %d'
        max_n = len(wav_names)

        style = wx.PD_AUTO_HIDE | wx.PD_APP_MODAL | wx.PD_CAN_ABORT | wx.PD_ELAPSED_TIME | wx.PD_REMAINING_TIME
        dlg = wx.ProgressDialog(u'進捗', msg % (1, max_n), maximum=max_n, parent=self.frame, style=style)

        sil_lv     = self.settings['sil_lv']
        sil_dur    = self.settings['sil_dur_s']
        before_dur = self.settings['before_dur_s']
        after_dur  = self.settings['after_dur_s']
        factor     = self.settings['factor']
        add        = self.settings['add']

        labels_dir = get_labels_dir_d(self.dir_snd)

        for i, (wav_name, labels) in enumerate(zip(wav_names, labels_names)):
            keep_going, skip = dlg.Update(i, msg % (i + 1, max_n))

            if not keep_going:
                break

            try:
                wav_file    = os.path.join(self.dir_snd, wav_name)
                labels_file = os.path.join(labels_dir, labels)

                wav = MyWave(wav_file, labels_file)

                if wav.err_msg:
                    wx.MessageBox(wav.err_msg + '\n' + wav_name)
                    continue

                if os.path.exists(labels_file):
                    labels = Labels(open(labels_file, 'r').readlines())
                else:
                    labels = wav.find_sound(sil_lv, sil_dur, before_dur, after_dur)

                self.auto_shift(wav, labels)

                ext = get_ext(wav_file)

                wav.insert_pause(ext, labels, factor, add)
            except Exception as e:
                wx.MessageBox(e.message)

        dlg.Destroy()


        # ---- 結果を通知

        pause_dir = get_pause_dir_d(self.dir_snd)

        if sys.platform == 'win32':
            try:
                import subprocess
                subprocess.Popen('explorer "%s"' % pause_dir.encode('cp932'))
            except:
                wx.MessageBox(u'出力場所 : %s' % pause_dir, u'完了', wx.OK)
        else:
            wx.MessageBox(u'出力場所 : %s' % pause_dir, u'完了', wx.OK)


    def auto_shift(self, wav, labels):
        '''
        自動ずれ補正
        '''

        if labels.distinction_s == NO_DISTINCTION:
            if wav.distinction_s != NO_DISTINCTION:
                labels.distinction_s = wav.distinction_s
                labels.write(wav.labels_file)
        else:
            auto_shift_s = auto_shift_diff_s(wav.distinction_s, labels.distinction_s)

            if auto_shift_s != 0:
                labels.distinction_s = wav.distinction_s
                labels.shift(auto_shift_s)
                labels.write(wav.labels_file)


    #--------------------------------------------------------------------------
    # イベント

    @binder(wx.EVT_SIZE, control='MainFrame')
    def OnSize(self, evt):
        w, h = evt.Size

        if w > 900:
            self.v_splitter.SetSashPosition(600)
        else:
            self.v_splitter.SetSashPosition(w / 2)

        if h > 600:
            self.h_splitter.SetSashPosition(h - 300)

        evt.Skip()


    # ファイル一覧のクリック
    @binder(wx.EVT_LIST_ITEM_SELECTED, control='FileList')
    def OnWavClick(self, evt):
        # 同じファイルは読み直さない
        if not self.dir_changed and self.settings['list_index'] == evt.m_itemIndex:
            return

        first = False

        if self.dir_changed:
            first = True

        self.dir_changed = False

        self.confirm_save()

        wav_file = os.path.join(self.dir_snd, evt.GetText())
        labels_file = get_labels_file_f(wav_file, evt.m_itemIndex + 1)
        self.settings['list_index'] = evt.m_itemIndex

        self.set_sound(wav_file, labels_file, first)


    # 音声ディレクトリを開く
    @binder(wx.EVT_MENU, id='MenuOpen')
    def OnOpenDir(self, evt=None):
        dir_snd = self.dir_snd

        if not dir_snd:
            dir_snd = self.get_music_dir()

        if not os.path.exists(dir_snd):
            dir_snd = os.getcwd()

        dlg = wx.DirDialog(self.frame, u'音声フォルダの選択',
                defaultPath=dir_snd,
                style=wx.DD_DEFAULT_STYLE
                | wx.DD_DIR_MUST_EXIST)

        if dlg.ShowModal() == wx.ID_OK:
            self.dir_snd = dlg.GetPath()

        dlg.Destroy()


    # ポーズ自動検索
    @binder(wx.EVT_MENU, id='MenuSearch')
    def OnSearch(self, evt):
        sil_lv     = self.settings['sil_lv']
        sil_dur    = self.settings['sil_dur_s']
        before_dur = self.settings['before_dur_s']
        after_dur  = self.settings['after_dur_s']

        self.view.find(sil_lv, sil_dur, before_dur, after_dur)


    # 表示スライダーのスクロール
    @binder(wx.EVT_SCROLL, control='DispSlider')
    def OnDispSliderScroll(self, evt):
        pos = max(MIN_SCALE, min(evt.Position, 100))
        self.settings['scale'] = pos
        self.view.scale = pos


    # FACTOR テキスト変更
    @binder(wx.EVT_TEXT, control='TextFactor')
    def OnFactorChange(self, evt):
        self.settings['factor'] = float(evt.EventObject.Value)
        self.view.factor = self.settings['factor']


    # ADD テキスト変更
    @binder(wx.EVT_TEXT, control='TextAdd')
    def OnAddChange(self, evt):
        self.settings['add'] = float(evt.EventObject.Value)
        self.view.add = self.settings['add']


    # ポーズファイル作成（このファイルのみ）
    @binder(wx.EVT_BUTTON, control='BtnInsertPauseOne')
    def OnInsertPauseOne(self, evt):
        self.insert_pause(False)


    # ポーズファイル作成（全ファイル）
    @binder(wx.EVT_BUTTON, control='BtnInsertPauseAll')
    def OnInsertPauseAll(self, evt):
        self.insert_pause(True)


    # ずれ調整スライダーのスクロール
    @binder(wx.EVT_SCROLL, control='ShiftSlider')
    def OnShiftSliderScroll(self, evt):
        lbl_shift = xrc.XRCCTRL(self.frame, 'LblShift')
        lbl_shift.Label = '%.3f%s' % (float(evt.Position) / 1000, u'秒')

        btn_shift = xrc.XRCCTRL(self.frame, 'BtnShift')

        if evt.Position == 0:
            btn_shift.Enabled = False
        else:
            btn_shift.Enabled = True


    # ずれ調整
    @binder(wx.EVT_BUTTON, control='BtnShift')
    def OnShift(self, evt):
        shift_slider = xrc.XRCCTRL(self.frame, 'ShiftSlider')

        val_s = float(shift_slider.Value) / 1000
        self.view.shift(val_s)
        shift_slider.Value = 0

        evt = wx.ScrollEvent()
        evt.Position = shift_slider.Value
        self.OnShiftSliderScroll(evt)


    # 用意されたポーズ情報コンボボックス
    @binder(wx.EVT_COMBOBOX, control='CmbAutoPause')
    def OnChangeAutoCmb(self, evt):
        if self.cmb_auto_pause.Count == 0:
            self.cmb_auto_pause.Enabled = False
            self.btn_auto_pause.Enabled = False
        else:
            self.cmb_auto_pause.Enabled = True
            if self.cmb_auto_pause.Value != '':
                self.btn_auto_pause.Enabled = True
            else:
                self.btn_auto_pause.Enabled = False


    # 用意されたポーズ情報を使う
    @binder(wx.EVT_BUTTON, control='BtnAutoPause')
    def OnUseAutoPause(self, evt):
        selection =  self.cmb_auto_pause.Selection

        if selection == wx.NOT_FOUND:
            return

        info = self.cmb_auto_pause.GetClientData(selection)

        # ---- すでにラベルを作ってあるか？

        labels_dir = get_labels_dir_d(self.dir_snd)
        labels_files = get_labels_file_list(labels_dir, False)
        num_labels = len(labels_files)

        if num_labels != 0:
            wx.MessageBox(DIR_LABELS + u'フォルダの名前を変えて、もう１度実行してください',
                    u'上書きしたくない')

            if sys.platform == 'win32':
                try:
                    import subprocess
                    subprocess.Popen('explorer "%s"' % self.dir_snd)
                except:
                    pass

            return

        # ---- 用意されたラベルを配置

        self.al.setup_labels(labels_dir, info)

        self.view.load_labels()

        self.view.win.auto_shift()


    # 用意されたポーズ情報を追加
    @binder(wx.EVT_BUTTON, control='BtnAddAuto')
    def OnAddAutoPause(self, evt):
        info = None

        dlg = wx.FileDialog(self.frame, u'ポーズ情報ファイル', self.dir_snd, '', '*.zip', wx.OPEN)

        if dlg.ShowModal() == wx.ID_OK:
            info = self.al.load_labels_info_from_zip(dlg.Path)

        dlg.Destroy()

        if info:
            wav_files = get_wav_file_list(self.dir_snd)
            num_waves = len(wav_files)

            if self.al.match_info(info, num_waves, loose=True):
                i = self.cmb_auto_pause.Append(u'(一時的に追加) ' + info.name, info)
                self.cmb_auto_pause.Select(i)
                self.set_enable()
            else:
                wx.MessageBox(u'音声ファイル数が違います\n必要な数 : %d' % (info.num_labels))


    # 用意されたポーズ情報を作成
    @binder(wx.EVT_BUTTON, control='BtnCreateAuto')
    def OnCreateAutoPause(self, evt):
        labels_dir = get_labels_dir_d(self.dir_snd)
        labels_files = get_labels_file_list(labels_dir, False)
        num_labels = len(labels_files)
        num_waves  = self.flist.ItemCount

        if num_labels < num_waves:
            wx.MessageBox(u'まだポーズがついてない音声があります')
            return

        # 音声ファイル数以上にあるラベルファイルは無視する
        labels_files = labels_files[: num_waves]

        dlg = wx.FileDialog(self.frame, u'ポーズ情報ファイル', self.dir_snd, '', '*.zip', wx.SAVE)

        zip_file = None

        if dlg.ShowModal() == wx.ID_OK:
            self.confirm_save()

            zip_file = dlg.Path

            if not zip_file.lower().endswith('.zip'):
                zip_file += '.zip'

        dlg.Destroy()

        if not zip_file:
            return

        # ---- 表示名の設定

        name = os.path.basename(self.dir_snd)

        if self.view.wav and self.view.wav.tag and self.view.wav.tag.album:
            name = self.view.wav.tag.album

        dlg = wx.TextEntryDialog(self.frame, u'表示名', u'入力', name, style=wx.OK)

        if dlg.ShowModal() == wx.ID_OK:
            name = dlg.Value

        dlg.Destroy()

        self.al.create_labels_info(zip_file, name, labels_dir, labels_files)


    @binder(wx.EVT_SCROLL, control='BGSliderR')
    @binder(wx.EVT_SCROLL, control='BGSliderG')
    @binder(wx.EVT_SCROLL, control='BGSliderB')
    def OnScrollBGColor(self, evt):
        self.set_bg_color()


    @binder(wx.EVT_SCROLL, control='FGSliderR')
    @binder(wx.EVT_SCROLL, control='FGSliderG')
    @binder(wx.EVT_SCROLL, control='FGSliderB')
    def OnScrollFGColor(self, evt):
        self.set_fg_color()


    def create_numctrl(self, val, min_val, max_val):
        ctrl = masked.numctrl.NumCtrl(self.frame)
        ctrl.SetAllowNegative(False)
        ctrl.SetIntegerWidth(1)
        ctrl.SetFractionWidth(2)
        ctrl.SetValue(val)
        ctrl.SetMin(min_val)
        ctrl.SetMax(max_val)
        ctrl.SetLimited(True)

        return ctrl

    # フレームを閉じる
    @binder(wx.EVT_MENU, id='MenuExit')
    @binder(wx.EVT_CLOSE)
    def OnClose(self, evt):
        self.confirm_save()

        self.settings['view_factor'] = self.view.view_factor
        self.settings.write_conf()

        self.pm.SaveAndUnregister()

        self.view.cancel()

        self.frame.Destroy()


    # ---- ツールバー

    # 先頭へ移動
    @binder(wx.EVT_TOOL, id='ToolHead')
    def OnHead(self, evt):
        self.view.head()
        self.set_enable()
        if self.view.playing:
            self.tool_bar.EnableTool(xrc.XRCID('ToolHead'), True)

    # 再生
    @binder(wx.EVT_TOOL, id='ToolPlay')
    def OnPlay(self, evt):
        self.view.play()
        self.set_enable()
        self.tool_bar.EnableTool(xrc.XRCID('ToolHead'), True)

    # ポーズモード再生
    @binder(wx.EVT_TOOL, id='ToolPlayPause')
    def OnPlayPause(self, evt):
        self.view.pause_mode_play()
        self.set_enable()
        self.tool_bar.EnableTool(xrc.XRCID('ToolHead'), True)

    # 一時停止
    @binder(wx.EVT_TOOL, id='ToolPause')
    def OnPause(self, evt):
        self.view.pause()
        self.set_enable()

    # 末尾に移動
    @binder(wx.EVT_TOOL, id='ToolTail')
    def OnTail(self, evt):
        self.view.tail()
        self.set_enable()

    # 拡大
    @binder(wx.EVT_TOOL, id='ToolZoomIn')
    def OnZoomIn(self, evt):
        self.view.zoom_in()
        self.set_enable()

    # 縮小
    @binder(wx.EVT_TOOL, id='ToolZoomOut')
    def OnZoomOut(self, evt):
        self.view.zoom_out()
        self.set_enable()

    # カット
    @binder(wx.EVT_TOOL, id='ToolCut')
    def OnCut(self, evt):
        self.view.cut()
        self.set_enable()

    # 左と結合
    @binder(wx.EVT_TOOL, id='ToolMergeLeft')
    def OnMergeLeft(self, evt):
        self.view.merge_left()
        self.set_enable()

    # 右と結合
    @binder(wx.EVT_TOOL, id='ToolMergeRight')
    def OnMergeRight(self, evt):
        self.view.merge_right()
        self.set_enable()

    # もとに戻す
    @binder(wx.EVT_TOOL, id='ToolUndo')
    def OnUndo(self, evt):
        self.view.undo()
        self.set_enable()

    # やり直し
    @binder(wx.EVT_TOOL, id='ToolRedo')
    def OnRedo(self, evt):
        self.view.redo()
        self.set_enable()

    # 保存
    @binder(wx.EVT_MENU, id='MenuSave')
    @binder(wx.EVT_TOOL, id='ToolSaveLabels')
    def OnSaveLabels(self, evt):
        self.view.save()
        self.set_enable()

    # 新規ラベル
    @binder(wx.EVT_TOOL, id='ToolInsert')
    def OnInsert(self, evt):
        self.view.insert_label()
        self.set_enable()

    # ラベル削除
    @binder(wx.EVT_TOOL, id='ToolRemove')
    def OnRemove(self, evt):
        self.view.remove_label()
        self.set_enable()


    # ---- 自作コントロールイベント

    def OnLabelChanged(self, evt):
        self.set_enable()

    def OnChangeCur(self, evt):
        self.set_enable()

    def OnClickCurChanged(self, evt):
        self.set_enable()

    def OnEOF(self, evt):
        self.set_enable()


    #--------------------------------------------------------------------------
    # プロパティ

    # ---- 音声ディレクトリ名

    @property
    def dir_snd(self):
        return self.settings['dir_snd']

    @dir_snd.setter
    def dir_snd(self, dir_snd):
        if dir_snd != self.dir_snd:
            self.dir_changed = True

            self.settings['list_index'] = 0
            self.settings['dir_snd'] = dir_snd

            self.update_flist()


# ドラッグ・アンド・ドロップ処理
class DirDrop(wx.FileDropTarget):
    def __init__(self, app):
        wx.FileDropTarget.__init__(self)
        self.app = app

    def OnDropFiles(self, x, y, names):
        if len(names) == 1:
            if os.path.isdir(names[0]):
                dir_snd = names[0]
            else:
                dir_snd = os.path.dirname(names[0])

            self.app.dir_snd = dir_snd


def is_already_run():
    '''
    すでに起動しているか？

    '''

    if sys.platform == 'win32':
        try:
            import win32event
            import win32api
            import winerror

            win32event.CreateMutex(None, 1, 'inspause mutex')

            if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
                return True
        except:
            pass

    return False


if __name__ == '__main__':
    # カレントディレクトリを取得
    try:
        cur_dir = os.path.dirname(os.path.abspath(__file__))
    except:
        cur_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

    # 作業フォルダを実行ファイルのあるフォルダにする
    os.chdir(cur_dir or '.')

    # 多重起動を禁止
    if is_already_run():
        sys.exit(1)

    persist_file = os.path.join(cur_dir, 'persist.txt')

    main(persist_file)
