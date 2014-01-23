#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
InsPause メイン
'''

__author__  = 'vanya'
__version__ = '2.10.0'
__date__    = '2014-01-22'

APP_NAME = 'inspause'

# 早めにAPPディレクトリを作成しておく
import myfile as mf
mf.init_dir(APP_NAME)


import os
import sys

import wx.lib.agw.persist as PM
from wx.lib.masked.numctrl import NumCtrl
from wx import xrc

from autoshift import auto_shift, find_dist_s
from backup import Backup
from conf import *
from convtable import Conv_table
from findsnd import find_sound, FIND_RATE, SIL_LV, SIL_DUR_S, BEFORE_DUR_S, AFTER_DUR_S
import insp
from label import Label, LBL_PAUSE
from labels import Labels
from labelswindow import *
from mylog import *
import pausewave
from volume import Volume
from waveplayer import WavePlayer, EVT_EOW, EVT_CUR_POS_CHANGE
import wx_utils


# ---- ステータスバー
STB_TEXT = 0
STB_POS = 1

# ---- もしカット再生
IFCUT_DUR_S   = 0.8  # 再生長さ（秒）。前後それぞれに設定される。
IFCUT_PAUSE_S = 0.5  # ポーズ時間（秒）

# ---- ImageList インデックス
IMG_HAS_LABELS = 0
IMG_NO_LABELS = 1


def main():
    # カレントディレクトリを取得
    cur_dir = get_cur_dir()

    # 作業フォルダを実行ファイルのあるフォルダにする
    os.chdir(cur_dir or '.')

    # 多重起動を禁止
    if is_already_run():
        sys.exit(1)

    app = InsPause()
    app.MainLoop()


class InsPause(wx.App):

    binder = wx_utils.bind_manager()

    def OnInit(self):
        self.conf = Config(mf.app_data_dir)

        if os.path.exists(mf.persist_path):
            self._processing_persist = True
        else:
            self._processing_persist = False

        self.wp = WavePlayer()
        self.snd = None
        self.bk = Backup()

        self.InitUI()

        self.binder.parent = self.frame
        self.binder.bindall(self)

        self.SetPersist()

        self.frame.Centre()
        self.frame.Show()

        self.RegisterControls()

        # spl_logの位置を記憶しておくため
        # register_controlsを呼び出したあとにログ画面を閉じる。
        if not self.conf.show_log:
            self.OnLog(None)

        self.UpdateFlist()

        if self._processing_persist:
            # exe化したときにも正しく動くように遅らせて実行
            wx.CallLater(1000, self.OffProcessingPersist)

        return True

    def OffProcessingPersist(self):
        self._processing_persist = False

    #--------------------------------------------------------------------------
    # persist （ウィンドウのサイズや最大化の保持）関連

    def SetPersist(self):
        self.pm = PM.PersistenceManager.Get()
        self.pm.SetPersistenceFile(mf.persist_path)
        self.pm.RegisterAndRestore(self.frame)

    def RegisterControls(self):
        self.frame.Freeze()

        # ここに記憶させたいウィジェットを書く
        self.pm.RegisterAndRestore(self.spl_h)
        self.pm.RegisterAndRestore(self.spl_v)
        self.pm.RegisterAndRestore(self.spl_log)
        self.pm.RegisterAndRestore(self.flist)

        self.frame.Thaw()

    #--------------------------------------------------------------------------
    # UI 初期化

    def InitUI(self):
        self.res = xrc.XmlResource(mf.xrc_path)

        self.InitFrame()
        self.InitLog()
        self.InitView()
        self.InitSetting()
        self.InitFileList()
        self.InitMenu()
        self.InitToolbar()
        self.InitStatusbar()

        self.EnableUI()

    def InitFrame(self):
        self.frame = self.res.LoadFrame(None, 'MainFrame')
        self.frame.Title = APP_NAME
        self.wp.add_listener(self.frame)
        SetIcon(self.frame)

        self.spl_h = xrc.XRCCTRL(self.frame, 'HorizontalSplitter')
        self.spl_v = xrc.XRCCTRL(self.frame, 'VerticalSplitter')

        # ドラッグアンドドロップ
        dd = DirDrop(self)
        self.frame.SetDropTarget(dd)

    def InitLog(self):
        self.spl_log = xrc.XRCCTRL(self.frame, 'LogSplitter')
        self.win1 = self.spl_log.GetWindow1()
        self.win2 = self.spl_log.GetWindow2()

        logtext = xrc.XRCCTRL(self.frame, 'LogText')
        sys.stdout = sys.stderr = self.log = Mylog(logtext, mf.log_path)

        self.auto_show_log = xrc.XRCCTRL(self.frame, 'ChkAutoShowLog')
        self.auto_show_log.SetValue(self.conf.auto_show_log)

    def InitView(self):
        self.view = LabelsWindow(parent=self.frame)
        self.view.view_factor = self.conf.view_factor
        self.view.scale = self.conf.scale
        self.res.AttachUnknownControl('WaveView', self.view, self.frame)

    def InitSetting(self):
        # ---- ポーズ音声作成
        self.SetDefaultSaveDir()

        # ---- ポーズ時間
        self.NumCtrl('TextFactor', self.conf.factor, MIN_FACTOR, MAX_FACTOR)
        self.NumCtrl('TextAdd', self.conf.add_s, MIN_ADD_S, MAX_ADD_S)

        # ---- バックアップ（コンボボックス、復元ボタン）
        self.cmb_backup = xrc.XRCCTRL(self.frame, 'CmbBackup')
        for info in self.bk:
            self.AddBackupInfo(info)
        self.btn_restore = xrc.XRCCTRL(self.frame, 'BtnRestore')
        self.btn_delbackup = xrc.XRCCTRL(self.frame, 'BtnDelBackup')

        # ---- ラベル検索（無音認識時間、無音レベル、前余裕、後余裕）
        self.NumCtrl('TextSilDur', self.conf.sil_dur_s, MIN_SIL_DUR_S, MAX_SIL_DUR_S)
        xrc.XRCCTRL(self.frame, 'SilLvSlider').Value = self.conf.sil_lv
        self.NumCtrl('TextBeforeDur', self.conf.before_dur_s, 0.0, 9.99)
        self.NumCtrl('TextAfterDur', self.conf.after_dur_s, 0.0, 9.99)

        # ---- 色
        self.SetViewBgColour(self.conf.bg)
        self.SetViewFgColour(self.conf.fg)
        self.view.SetHandleColour(self.conf.handle)

        # ---- 表示範囲
        self.sld_scale = xrc.XRCCTRL(self.frame, 'SldScale')
        self.sld_scale.SetValue(self.conf.scale)

        # ---- ファイルリストの幅
        self.sld_flist_width = xrc.XRCCTRL(self.frame, 'SldFlistWidth')
        self.sld_flist_width.SetValue(self.conf.flist_width)

        self.SetScroll('ScrMain')
        self.SetScroll('ScrTool')
        self.SetScroll('ScrView')

    def AddBackupInfo(self, info, tail=True):
        name = '(%02d) %s' % (info.num_labels, info.name)
        if tail:
            self.cmb_backup.Append(name, info)
        else:
            self.cmb_backup.Insert(name, 0, info)

    def InitFileList(self):
        self.flist = xrc.XRCCTRL(self.frame, 'FileList')
        self.flist.InsertColumn(0, u'音声')

        icon = wx.ArtProvider.GetIcon(wx.ART_LIST_VIEW, size=(16, 16))

        bmp = wx.EmptyBitmap(16, 16)
        dc = wx.BufferedDC(None, bmp)
        dc.SetBackground(wx.WHITE_BRUSH)
        dc.Clear()
        del dc

        il = wx.ImageList(16, 16, False, 2)
        il.AddIcon(icon)
        il.Add(bmp)
        self.flist.AssignImageList(il, wx.IMAGE_LIST_SMALL)

    def InitMenu(self):
        self.menu = self.res.LoadMenuBar('MenuBar')
        self.frame.SetMenuBar(self.menu)
        self.menu.Check(xrc.XRCID('MenuLog'), self.conf.show_log)

    def InitToolbar(self):
        tools = []
        self.tools = tools

        tools += [{'name': 'ToolHead',       'check': self.view.can_head}]
        tools += [{'name': 'ToolPlay',       'check': self.CanPlay}]
        tools += [{'name': 'ToolPlayPause',  'check': self.CanPlay}]
        tools += [{'name': 'ToolPause',      'check': self.CanPause}]
        tools += [{'name': 'ToolZoomIn',     'check': self.view.can_zoom_in}]
        tools += [{'name': 'ToolZoomOut',    'check': self.view.can_zoom_out}]
        tools += [{'name': 'ToolUndo',       'check': self.view.can_undo}]
        tools += [{'name': 'ToolRedo',       'check': self.view.can_redo}]
        tools += [{'name': 'ToolSaveLabels', 'check': self.view.can_save}]

        self.tool_bar = self.res.LoadToolBar(self.frame, 'ToolBar')
        self.tool_bar.Realize()

    def CanPlay(self):
        if self.snd and self.wp.can_play():
            return True
        else:
            return False

    def CanPause(self):
        if self.snd and self.wp.can_pause():
            return True
        else:
            return False

    def InitStatusbar(self):
        statusbar = self.frame.CreateStatusBar()
        statusbar.SetFieldsCount(2)
        label = '  00:00.000 / 00:00.000   '
        cw = wx.ClientDC(statusbar).GetTextExtent(label)[0]
        statusbar.SetStatusWidths([-1, cw])
        self.statusbar = statusbar

    def SetFlistIcon(self):
        for i in range(self.flist.GetItemCount()):
            labels_path = mf.get_labels_path(self.snd_dir, i + 1)

            if os.path.exists(labels_path):
                image_no = IMG_HAS_LABELS
            else:
                image_no = IMG_NO_LABELS

            self.flist.SetItemImage(i, image_no, image_no)

    def SetDefaultSaveDir(self):
        path = mf.get_default_pause_dir(self.snd_dir)
        ctrl = xrc.XRCCTRL(self.frame, 'TextSaveDir')
        ctrl.SetValue(path)

    #--------------------------------------------------------------------------
    # UI

    def SetTitleBar(self, snd_path):
        snd_file = os.path.basename(snd_path)
        self.frame.Title = snd_file + ' - ' + APP_NAME

    def NumCtrl(self, name, val, min_val, max_val):
        '''
        小数テキストコントロールの作成
        #.## 形式で、最小値は引数min_val、最大値は引数max_valに制限される。
        '''

        ctrl = NumCtrl(self.frame)
        ctrl.SetAllowNegative(False)
        ctrl.SetIntegerWidth(1)
        ctrl.SetFractionWidth(2)
        ctrl.SetValue(val)
        ctrl.SetMin(min_val)
        ctrl.SetMax(max_val)
        ctrl.SetLimited(True)
        cw, ch = ctrl.GetTextExtent('X0.00X')
        ctrl.SetMinSize((cw, -1))

        self.res.AttachUnknownControl(name, ctrl, self.frame)

        return ctrl

    def SetStatusPosText(self, pos_f):
        '''
        ステータスバーに現在位置（秒）を設定
        @param pos_f 現在位置（フレーム）
        '''

        pos_s = self.view.f_to_s(pos_f)
        pos_str = sec_to_str(pos_s)
        s = '  %s / %s' % (pos_str, self.dur_str)
        self.statusbar.SetStatusText(s, STB_POS)

    def LogIsVisible(self):
        '''
        ログ画面が表示されているか？
        '''

        return self.spl_log.IsSplit()

    def SetScroll(self, name):
        '''
        設定ノートブックの中の領域をスクロールできるようにする
        '''

        ctrl = xrc.XRCCTRL(self.frame, name)
        w, h = ctrl.Size
        su = 20
        ctrl.SetScrollbars(su, su, w, su, h / su)

    def EnableUI(self):
        '''
        ツールバーやコントロールの有効・無効を設定する
        '''

        # ---- メニュー
        self.menu.Enable(xrc.XRCID('MenuSave'), self.view.can_save())

        # ---- ツールバー
        for tool in self.tools:
            self.tool_bar.EnableTool(xrc.XRCID(tool['name']), tool['check']())

        # ---- 設定コントロール
        notebook = xrc.XRCCTRL(self.frame, 'NoteBook')

        if self.wp.is_playing or self.snd is None:
            notebook.Enabled = False
        else:
            notebook.Enabled = True

        self.EnableBackup()

    def EnableBackup(self):
        '''
        バックアップコンボボックス・バックアップボタン・復元ボタン・
        削除ボタンの有効／無効を設定
        '''

        if self.cmb_backup.Count == 0:
            self.cmb_backup.Enabled = False
            self.btn_restore.Enabled = False
            self.btn_delbackup.Enabled = False
        else:
            self.cmb_backup.Enabled = True
            if self.cmb_backup.Value != '':
                self.btn_restore.Enabled = True

                info = self.GetSelectedBkInfo()
                if info.is_sys:
                    self.btn_delbackup.Enabled = False
                else:
                    self.btn_delbackup.Enabled = True
            else:
                self.btn_restore.Enabled = False
                self.btn_delbackup.Enabled = False

    # ---- 色

    def SetViewBgColour(self, colour):
        self.conf.bg = self.GetColour(colour)
        ctrl = xrc.XRCCTRL(self.frame, 'BtnBg')
        ctrl.SetBackgroundColour(colour)
        self.view.SetBackgroundColour(colour)

    def SetViewFgColour(self, colour):
        self.conf.fg = self.GetColour(colour)
        ctrl = xrc.XRCCTRL(self.frame, 'BtnFg')
        ctrl.SetBackgroundColour(colour)
        self.view.SetForegroundColour(colour)

    def GetColour(self, colour):
        if isinstance(colour, basestring):
            name = colour
            colour = wx.Colour()
            colour.SetFromName(name)

        return colour

    #--------------------------------------------------------------------------

    def ConfirmSave(self, cancel=False):
        '''
        保存するかをユーザに確認する

        @param cancel Trueならキャンセルボタンも表示する
        @return 保存の必要がないならNone
                それ以外はユーザの選択によりwx.YES, wx.NO, wx.CANCEL
        '''

        if self.view.can_save():
            flg = wx.YES_NO | wx.ICON_QUESTION
            if cancel:
                flg |= wx.CANCEL

            res = wx.MessageBox(u'変更を保存しますか？', u'確認',  flg)

            if res == wx.YES:
                self.view.save()
                self.EnableUI()
                return wx.YES
            else:
                return res

        return None

    def UpdateFlist(self):
        '''
        音声ファイル一覧画面を更新する
        '''

        self.ConfirmSave()

        self.flist.DeleteAllItems()

        snd_files = mf.get_snd_files(self.snd_dir)

        if not snd_files:
            self.conf.list_index = 0
            self.snd = None
            self.view.SetVolume(None)
            self.view.SetLabels(Labels(), '')
            self.EnableUI()
            return

        snd_files.sort()

        for i, name in enumerate(snd_files):
            labels_path = mf.get_labels_path(self.snd_dir, i + 1)

            if os.path.exists(labels_path):
                image_no = IMG_HAS_LABELS
            else:
                image_no = IMG_NO_LABELS

            self.flist.InsertImageStringItem(i, name, image_no)

        list_index = self.conf.list_index
        list_index = max(0, min(list_index, self.flist.ItemCount - 1))
        self.conf.list_index = list_index

        self.conf.list_index = -1  # OnSelectSndで波形画面を更新するため
        self.flist.Select(list_index)
        self.flist.EnsureVisible(list_index)
        self.flist.SetColumnWidth(0, self.conf.flist_width)

    def SetSound(self, snd_path, labels_path):
        '''
        波形画面に音声を設定する
        '''

        if self.wp.is_playing:
            self.Pause()

        msg = u'音声ファイルを読み込み中'
        dlg = wx.ProgressDialog(u'読込', msg, parent=self.frame)

        try:
            self.snd = pausewave.open(snd_path, 'rb', dlg.Update)
            if self.snd.getnframes() == 0:
                raise Exception('num of frames == 0')
        except Exception as e:
            print str(e)
            msg = u'音声ファイルの読み込みに失敗しました。\n\n' \
                  u'音声ファイル=%s\nラベルファイル=%s' % (snd_path, labels_path)
            wx.MessageBox(msg)

            self.view.SetVolume(None)
            self.view.SetLabels(Labels(), labels_path)
            self.EnableUI()
            return
        finally:
            dlg.Destroy()

        vol = Volume(self.snd)
        self.view.SetVolume(vol)

        labels = self.LoadLabels(labels_path, self.snd)
        self.view.SetLabels(labels, labels_path)

        item = self.flist.GetFirstSelected()
        if item != -1:
            self.flist.SetItemImage(item, IMG_HAS_LABELS, IMG_HAS_LABELS)

        self.SetTitleBar(snd_path)

        nframes = self.snd.getnframes()
        rate = self.snd.getframerate()
        self.dur_str = sec_to_str(float(nframes) / rate)
        self.SetStatusPosText(self.view.pos_f)

        self.EnableUI()

    def LoadLabels(self, f, snd):
        '''
        ラベル情報ファイルを読み込む。なければ作成する
        '''

        if os.path.exists(f):
            labels = Labels(f)
        else:
            sil_lv = self.conf.sil_lv
            sil_dur = self.conf.sil_dur_s
            before_dur = self.conf.before_dur_s
            after_dur = self.conf.after_dur_s

            vol = Volume(snd, FIND_RATE)
            labels = find_sound(vol, sil_lv, sil_dur, before_dur, after_dur)

            labels.write(f)

        if not hasattr(labels, 'dist_s') or labels.dist_s == NO_DISTINCTION:
            labels.dist_s = find_dist_s(snd)
            labels.write(f)

        return labels

    def InsertPause(self):
        '''
        ポーズファイルを作成する
        '''

        if self.ConfirmSave() == wx.NO:
            return

        pause_dir = self.GetPauseDir()
        if not pause_dir:
            return

        if not self.ExistsLabels():
            return

        snd_paths, labels_paths, pause_paths = self.GetFilesList(pause_dir)

        msg = u'ポーズ挿入中 %d / %d'
        max_n = len(snd_paths)
        style = wx.PD_AUTO_HIDE | wx.PD_APP_MODAL | wx.PD_CAN_ABORT | wx.PD_ELAPSED_TIME | wx.PD_REMAINING_TIME
        dlg = wx.ProgressDialog(u'進捗', msg % (1, max_n), maximum=max_n, parent=self.frame, style=style)

        err_num = 0

        for i, (snd_path, labels_path, pause_path) in \
                enumerate(zip(snd_paths, labels_paths, pause_paths)):

            keep_going, skip = dlg.Update(i, msg % (i + 1, max_n))

            if not keep_going:
                break

            try:
                insp.insert_pause(snd_path, pause_path, labels_path,
                        self.conf.factor, self.conf.add_s)
            except Exception:
                try:
                    if not pause_path.endswith('.wav'):
                        base = os.path.splitext(pause_path)[0]
                        pause_path = base + '.wav'
                        insp.insert_pause(snd_path, pause_path, labels_path,
                                self.conf.factor, self.conf.add_s)
                        print u'[Encoder Error] wav形式に自動的に変更しました:', pause_path
                        continue
                except Exception as e:
                    print str(type(e)), str(e)
                    err_num += 1

        dlg.Destroy()

        if err_num > 0:
            msg = u'ポーズ音声の作成中にエラーが発生しました'
            wx.MessageBox(msg, u'エラー', wx.OK | wx.ICON_ERROR)

        # ---- 結果を通知
        if sys.platform == 'win32':
            try:
                import subprocess
                subprocess.Popen('explorer "%s"' % pause_dir.encode('cp932'))
            except:
                wx.MessageBox(u'出力場所 : %s' % pause_dir, u'完了', wx.OK)
        else:
            wx.MessageBox(u'出力場所 : %s' % pause_dir, u'完了', wx.OK)

    def GetPauseDir(self):
        '''
        ポーズ音声出力先ディレクトリの取得
        '''

        pause_dir = xrc.XRCCTRL(self.frame, 'TextSaveDir').GetValue()
        if not os.path.exists(pause_dir):
            parent = os.path.dirname(pause_dir)
            if os.path.exists(parent):
                msg = u'フォルダを新しく作りますか？'
                flg = wx.YES_NO | wx.ICON_QUESTION
                res = wx.MessageBox(msg, u'確認', flg)

                if res == wx.YES:
                    os.mkdir(pause_dir)
                else:
                    return None
            else:
                msg = u'存在しないフォルダです:%s' % pause_dir
                wx.MessageBox(msg)
                return None

        if pause_dir == self.snd_dir:
            msg = u'入力音声ファイルと同じ場所には出力できません'
            wx.MessageBox(msg)
            return None

        return pause_dir

    def ExistsLabels(self):
        '''
        ラベルファイルが存在するか？
        '''

        is_all = xrc.XRCCTRL(self.frame, 'RadAllFiles').GetValue()
        if is_all:  # すべてのファイル
            labels_paths = self.GetFullLabelsPath()
            if not labels_paths:
                return False

        return True

    def GetFilesList(self, pause_dir):
        '''
        入力音声ファイル・ラベルファイル・ポーズ付き音声ファイルの
        それぞれのリストを取得
        '''

        is_all = xrc.XRCCTRL(self.frame, 'RadAllFiles').GetValue()
        if is_all:  # すべてのファイル
            rng = range(self.flist.ItemCount)
        else:  # このファイルのみ
            list_index = self.conf.list_index
            rng = range(list_index, list_index+1)

        snd_paths = []
        labels_paths = []
        pause_paths = []

        for i in rng:
            snd_path, labels_path, pause_path = self.GetFiles(i, pause_dir)
            snd_paths.append(snd_path)
            labels_paths.append(labels_path)
            pause_paths.append(pause_path)

        return snd_paths, labels_paths, pause_paths

    def GetFiles(self, i, pause_dir):
        snd_file = self.flist.GetItem(i, 0).GetText()
        snd_path = os.path.join(self.snd_dir, snd_file)

        labels_path = mf.get_labels_path(self.snd_dir, i + 1)

        pause_path = os.path.join(pause_dir, snd_file)

        return snd_path, labels_path, pause_path

    #--------------------------------------------------------------------------
    # 再生／停止

    def Play(self):
        self.snd.settable(None)
        self.snd.setpos(self.view.pos_f, True)
        self.pos_f_after_eow = self.snd.tell(True)
        self.view.playing = True
        self.wp.play(self.snd, True)
        self.EnableUI()
        self.tool_bar.EnableTool(xrc.XRCID('ToolHead'), True)

    def PausePlay(self):
        factor = self.conf.factor
        add = self.conf.add_s
        rate = self.snd.getframerate()
        nframes = self.snd.getnframes(True)

        labels = self.view.GetLabels()
        tbl = Conv_table(labels, rate, nframes, factor, add)
        self.snd.settable(tbl)

        self.snd.setpos(self.view.pos_f, True)
        self.pos_f_after_eow = self.snd.tell(True)
        self.view.playing = True
        self.wp.play(self.snd, True)
        self.EnableUI()
        self.tool_bar.EnableTool(xrc.XRCID('ToolHead'), True)

    def IfcutPlay(self, pos_s):
        tbl = self.CreateIfcutTable(pos_s)
        self.snd.settable(tbl)

        rate = self.snd.getframerate()
        pos_f = pos_s * rate
        start_f = max(0, int((pos_s - IFCUT_DUR_S) * rate))

        self.snd.setpos(start_f, True)
        self.pos_f_after_eow = pos_f
        self.view.playing = True
        self.wp.play(self.snd, False)
        self.EnableUI()
        self.tool_bar.EnableTool(xrc.XRCID('ToolHead'), True)

    def CreateIfcutTable(self, pos_s):
        '''
        引数で指定された位置にポーズを入れるような変換テーブルを作成
        '''

        pause_lbl = Label(pos_s, pos_s, LBL_PAUSE)
        labels = Labels([str(pause_lbl)])
        rate = self.snd.getframerate()
        end_f = int((pos_s + IFCUT_DUR_S) * rate)
        return Conv_table(labels, rate, end_f, 0, IFCUT_PAUSE_S)

    def Pause(self):
        self.wp.pause()
        self.view.playing = False
        self.EnableUI()

    #--------------------------------------------------------------------------
    # ラベル情報のバックアップ

    # バックアップ
    def Backup(self, prefix=''):
        info = self.bk.backup(self.snd_dir, prefix)
        if info:
            self.AddBackupInfo(info, False)
            self.cmb_backup.SetSelection(0)
            self.EnableBackup()

    # 復元
    def Restore(self):
        self.ConfirmSave()

        info = self.GetSelectedBkInfo()

        if not info:
            return

        # 自動バックアップ
        try:
            self.Backup('auto_')
        except:
            pass

        self.bk.restore(self.snd_dir, info)
        self.view.ReloadLabels()
        self.SetFlistIcon()

    # 削除
    def DelBackup(self):
        info = self.GetSelectedBkInfo()

        if info and not info.is_sys:
            flg = wx.YES_NO | wx.ICON_QUESTION
            res = wx.MessageBox(u'本当に削除しますか？', u'確認',  flg)

            if res != wx.YES:
                self.view.save()
                self.EnableUI()
                return

            if self.bk.delete(info):
                self.DelSelectedBkInfo()
                self.EnableBackup()

    # 自動ずれ調整
    def AutoShift(self):
        if self.ConfirmSave() == wx.NO:
            return

        if not self.ExistsLabels():
            return

        # 自動バックアップ
        try:
            self.Backup('auto_')
        except:
            pass

        snd_paths, labels_paths, pause_paths = self.GetFilesList('.')

        msg = u'自動ずれ調整中 %d / %d'
        max_n = len(snd_paths)
        style = wx.PD_AUTO_HIDE | wx.PD_APP_MODAL | wx.PD_CAN_ABORT | wx.PD_ELAPSED_TIME | wx.PD_REMAINING_TIME
        dlg = wx.ProgressDialog(u'進捗', msg % (1, max_n), maximum=max_n, parent=self.frame, style=style)

        err_num = 0

        for i, (snd_path, labels_path, pause_path) in \
                enumerate(zip(snd_paths, labels_paths, pause_paths)):

            keep_going, skip = dlg.Update(i, msg % (i + 1, max_n))

            if not keep_going:
                break

            try:
                auto_shift(snd_path, labels_path)
            except Exception as e:
                print str(e)
                err_num += 1

        dlg.Destroy()

        if err_num > 0:
            msg = u'エラーが発生しました'
            wx.MessageBox(msg, u'エラー', wx.OK | wx.ICON_ERROR)

    def GetFullLabelsPath(self):
        labels_paths = mf.get_labels_paths(self.snd_dir)
        num_labels = len(labels_paths)
        num_snds = self.flist.ItemCount

        if num_labels < num_snds:
            wx.MessageBox(u'まだポーズがついてない音声があります')
            return None

        # 音声ファイル数以上にあるラベルファイルは無視する
        return labels_paths[:num_snds]

    def GetSelectedBkInfo(self):
        selection = self.cmb_backup.Selection

        if selection == wx.NOT_FOUND:
            return None

        return self.cmb_backup.GetClientData(selection)

    def DelSelectedBkInfo(self):
        selection = self.cmb_backup.Selection

        if selection == wx.NOT_FOUND or self.cmb_backup.Value == '':
            return

        self.cmb_backup.Delete(selection)
        self.cmb_backup.SetSelection(0)

    #--------------------------------------------------------------------------
    # イベント

    @binder(wx.EVT_SIZE, control='MainFrame')
    def OnSize(self, evt):
        if not self._processing_persist:
            w, h = evt.Size
            self.spl_h.SetSashPosition(h / 2)
            self.spl_v.SetSashPosition(w / 2)
            self.spl_log.SetSashPosition(w / 2)

        evt.Skip()

    # ---- ログ

    @binder(wx.EVT_BUTTON, control='BtnClearLog')
    def OnClearLog(self, evt):
        self.log.clear()

    @binder(wx.EVT_CHECKBOX, control='ChkAutoShowLog')
    def OnChangeAutoShowLog(self, evt):
        self.conf.auto_show_log = self.auto_show_log.IsChecked()

    @binder(EVT_LOG_CHANGE)
    def OnLogChange(self, evt):
        if not self.LogIsVisible() and self.conf.auto_show_log:
            self.OnLog(None)

    @binder(wx.EVT_MENU, id='MenuLog')
    @binder(wx.EVT_BUTTON, control='BtnCloseLog')
    def OnLog(self, evt):
        if self.LogIsVisible():
            self.log_sash_pos = self.spl_log.GetSashPosition()
            self.spl_log.Unsplit()
            self.conf.show_log = False
            self.menu.Check(xrc.XRCID('MenuLog'), False)
        else:
            self.spl_log.SplitVertically(self.win1, self.win2, self.log_sash_pos)
            self.conf.show_log = True
            self.menu.Check(xrc.XRCID('MenuLog'), True)

    # ----

    # 音声ファイル一覧のクリック
    @binder(wx.EVT_LIST_ITEM_SELECTED, control='FileList')
    def OnSelectSnd(self, evt):
        # 同じファイルは読み直さない
        if self.conf.list_index == evt.m_itemIndex:
            return

        self.ConfirmSave()

        snd_path = os.path.join(self.snd_dir, evt.GetText())
        labels_path = mf.get_labels_path(self.snd_dir, evt.m_itemIndex + 1)
        self.conf.list_index = evt.m_itemIndex

        self.SetSound(snd_path, labels_path)

    # 音声ディレクトリを開く
    @binder(wx.EVT_MENU, id='MenuOpen')
    def OnOpenDir(self, evt=None):
        snd_dir = self.snd_dir

        if not snd_dir:
            snd_dir = mf.get_music_dir()

        if not os.path.exists(snd_dir):
            snd_dir = os.getcwd()

        msg = u'音声フォルダの選択'
        style = wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST

        dlg = wx.DirDialog(self.frame, msg, snd_dir, style)
        if dlg.ShowModal() == wx.ID_OK:
            self.snd_dir = dlg.GetPath()
        dlg.Destroy()

    # ---- 設定項目

    # FACTOR テキスト変更
    @binder(wx.EVT_TEXT, control='TextFactor')
    def OnFactorChange(self, evt):
        self.conf.factor = float(evt.EventObject.Value)

    # ADD テキスト変更
    @binder(wx.EVT_TEXT, control='TextAdd')
    def OnAddChange(self, evt):
        self.conf.add_s = float(evt.EventObject.Value)

    # -------- ポーズファイル作成

    @binder(wx.EVT_BUTTON, control='BtnSaveDir')
    def OnSaveDir(self, evt):
        msg = u'ポーズ音声の保存先フォルダの選択'
        style = wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST | wx.DD_NEW_DIR_BUTTON
        default_dir = mf.get_default_pause_dir(self.snd_dir)

        dlg = wx.DirDialog(self.frame, msg, default_dir, style)

        if dlg.ShowModal() == wx.ID_OK:
            if dlg.GetPath() == self.snd_dir:
                msg = u'入力音声ファイルと同じ場所には出力できません'
                wx.MessageBox(msg)
                return

            ctrl = xrc.XRCCTRL(self.frame, 'TextSaveDir')
            ctrl.SetValue(dlg.GetPath())

        dlg.Destroy()

    @binder(wx.EVT_BUTTON, control='BtnInsertPause')
    def OnInsertPauseAll(self, evt):
        self.InsertPause()

    # -------- ずれ調整

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

    @binder(wx.EVT_BUTTON, control='BtnShift')
    def OnShift(self, evt):
        shift_slider = xrc.XRCCTRL(self.frame, 'ShiftSlider')

        val_s = float(shift_slider.Value) / 1000
        self.view.shift(val_s)
        shift_slider.Value = 0

        evt = wx.ScrollEvent()
        evt.Position = shift_slider.Value
        self.OnShiftSliderScroll(evt)

    # -------- バックアップ

    # ポーズ情報コンボボックス
    @binder(wx.EVT_COMBOBOX, control='CmbBackup')
    def OnChangeBackupCmb(self, evt):
        self.EnableBackup()

    # バックアップの作成
    @binder(wx.EVT_BUTTON, control='BtnBackup')
    def OnBackup(self, evt):
        self.Backup()

    # 復元
    @binder(wx.EVT_BUTTON, control='BtnRestore')
    def OnRestore(self, evt):
        self.Restore()

    # 削除
    @binder(wx.EVT_BUTTON, control='BtnDelBackup')
    def OnDelBackup(self, evt):
        self.DelBackup()

    # 自動ずれ調整
    @binder(wx.EVT_BUTTON, control='BtnAutoShift')
    def OnAutoShift(self, evt):
        self.AutoShift()

    # -------- ポーズ再検索

    # 無音認識時間 テキスト変更
    @binder(wx.EVT_TEXT, control='TextSilDur')
    def OnSilDurChange(self, evt):
        self.conf.sil_dur_s = float(evt.EventObject.Value)

    # 無音レベルスライダーのスクロール
    @binder(wx.EVT_SCROLL, control='SilLvSlider')
    def OnSilLvSliderScroll(self, evt):
        pos = max(0, min(evt.Position, 100))
        self.conf.sil_lv = pos

    # 前余裕 テキスト変更
    @binder(wx.EVT_TEXT, control='TextBeforeDur')
    def OnBeforeDurChange(self, evt):
        self.conf.before_dur_s = float(evt.EventObject.Value)

    # 後余裕 テキスト変更
    @binder(wx.EVT_TEXT, control='TextAfterDur')
    def OnAfterDurChange(self, evt):
        self.conf.after_dur_s = float(evt.EventObject.Value)

    @binder(wx.EVT_BUTTON, control='BtnResetSearch')
    def OnResetSearch(self, evt):
        xrc.XRCCTRL(self.frame, 'TextSilDur').Value = str(SIL_DUR_S)
        xrc.XRCCTRL(self.frame, 'SilLvSlider').Value = SIL_LV
        self.conf.sil_lv = SIL_LV
        xrc.XRCCTRL(self.frame, 'TextBeforeDur').Value = str(BEFORE_DUR_S)
        xrc.XRCCTRL(self.frame, 'TextAfterDur').Value = str(AFTER_DUR_S)

    @binder(wx.EVT_BUTTON, control='BtnSearch')
    def OnSearch(self, evt):
        sil_lv = self.conf.sil_lv
        sil_dur = self.conf.sil_dur_s
        before_dur = self.conf.before_dur_s
        after_dur = self.conf.after_dur_s

        self.view.find(sil_lv, sil_dur, before_dur, after_dur)

    # -------- 色

    @binder(wx.EVT_BUTTON, control='BtnBg')
    def OnBgColour(self, evt):
        colour = wx.GetColourFromUser(self.frame, self.conf.bg)
        if colour.IsOk():
            self.SetViewBgColour(colour)
            self.view.UpdateDrawing()

    @binder(wx.EVT_BUTTON, control='BtnFg')
    def OnFgColour(self, evt):
        colour = wx.GetColourFromUser(self.frame, self.conf.fg)
        if colour.IsOk():
            self.SetViewFgColour(colour)
            self.view.UpdateDrawing()

    @binder(wx.EVT_BUTTON, control='BtnResetColour')
    def OnResetColour(self, evt):
        self.SetViewBgColour(BG_COLOUR)
        self.SetViewFgColour(FG_COLOUR)
        self.view.UpdateDrawing()

    # -------- 表示範囲

    @binder(wx.EVT_SLIDER, control='SldScale')
    def OnScaleSlider(self, evt):
        self.conf.scale = self.sld_scale.GetValue()
        self.view.scale = self.conf.scale

    # -------- ファイルリストの幅

    @binder(wx.EVT_SLIDER, control='SldFlistWidth')
    def OnFlistWidth(self, evt):
        self.conf.flist_width = self.sld_flist_width.GetValue()
        self.flist.SetColumnWidth(0, self.conf.flist_width)

    # ---- ツールバー

    # 先頭へ移動
    @binder(wx.EVT_TOOL, id='ToolHead')
    def OnHead(self, evt):
        self.view.head()
        self.EnableUI()

        if self.view.playing:
            self.tool_bar.EnableTool(xrc.XRCID('ToolHead'), True)

        if self.wp.is_playing:
            self.snd.rewind()

    # 再生
    @binder(wx.EVT_TOOL, id='ToolPlay')
    def OnPlay(self, evt):
        self.Play()

    # ポーズモード再生
    @binder(wx.EVT_TOOL, id='ToolPlayPause')
    def OnPausePlay(self, evt):
        self.PausePlay()

    # 一時停止
    @binder(wx.EVT_TOOL, id='ToolPause')
    def OnPause(self, evt):
        self.Pause()

    # 拡大
    @binder(wx.EVT_TOOL, id='ToolZoomIn')
    def OnZoomIn(self, evt):
        self.view.zoom_in()
        self.EnableUI()

    # 縮小
    @binder(wx.EVT_TOOL, id='ToolZoomOut')
    def OnZoomOut(self, evt):
        self.view.zoom_out()
        self.EnableUI()

    # もとに戻す
    @binder(wx.EVT_TOOL, id='ToolUndo')
    def OnUndo(self, evt):
        self.view.undo()
        self.EnableUI()

    # やり直し
    @binder(wx.EVT_TOOL, id='ToolRedo')
    def OnRedo(self, evt):
        self.view.redo()
        self.EnableUI()

    # 保存
    @binder(wx.EVT_MENU, id='MenuSave')
    @binder(wx.EVT_TOOL, id='ToolSaveLabels')
    def OnSaveLabels(self, evt):
        self.view.save()
        self.EnableUI()

    # ---- メニュー

    # フレームを閉じる
    @binder(wx.EVT_MENU, id='MenuExit')
    @binder(wx.EVT_CLOSE)
    def OnClose(self, evt):
        if self.ConfirmSave(True) == wx.CANCEL:
            evt.Veto()
            return

        self._processing_persist = True

        self.conf.view_factor = self.view.view_factor
        self.conf.scale = self.view.scale
        self.conf.store()
        mf.store_map()

        if not self.spl_log.IsSplit():
            self.frame.Hide()
            # スプリッタの位置を記憶させるために、一時的にスプリッタを表示
            self.spl_log.SplitVertically(self.win1, self.win2, self.log_sash_pos)

        self.pm.SaveAndUnregister()

        self.wp.pause()

        self.frame.Destroy()

    # ---- 自作コントロールイベント

    @binder(EVT_REQ_PLAY)
    def OnReqPlay(self, evt):
        self.Play()
        self.view.UpdateDrawing(2)

    @binder(EVT_REQ_PAUSE_PLAY)
    def OnReqPausePlay(self, evt):
        self.PausePlay()
        self.view.UpdateDrawing(2)

    @binder(EVT_REQ_IFCUT_PLAY)
    def OnReqIfCutPlay(self, evt):
        self.IfcutPlay(evt.GetSec())
        self.view.UpdateDrawing(2)

    @binder(EVT_REQ_PAUSE)
    def OnReqPause(self, evt):
        self.Pause()

    # WavePlayer からの現在位置変更イベント
    @binder(EVT_CUR_POS_CHANGE)
    def OnWPPosChange(self, evt):
        pos_f = self.snd.tell(True)
        self.view.pos_f = pos_f
        self.SetStatusPosText(pos_f)

    # LabelsWindow からの現在位置変更イベント
    @binder(EVT_VW_POS_CHANGE)
    def OnLWPosChange(self, evt):
        self.SetStatusPosText(evt.GetPos())

        if self.wp.is_playing:
            self.snd.setpos(evt.GetPos(), True)

        self.EnableUI()

    @binder(EVT_OPEN_SND)
    def OnOpenSnd(self, evt):
        self.OnOpenDir(None)

    @binder(EVT_STATUS_MSG)
    def OnStatusMsg(self, evt):
        self.statusbar.SetStatusText(evt.GetMsg())

    @binder(EVT_LABEL_CHANGE)
    def OnLabelChange(self, evt):
        self.EnableUI()

    @binder(EVT_SCALE_CHANGE)
    def OnScaleChange(self, evt):
        self.conf.scale = evt.GetPos()
        self.sld_scale.SetValue(self.conf.scale)

    @binder(EVT_EOW)
    def OnEOW(self, evt):
        self.view.playing = False
        self.view.pos_f = self.pos_f_after_eow
        self.EnableUI()

    #--------------------------------------------------------------------------
    # プロパティ

    # ---- 音声ディレクトリ名

    @property
    def snd_dir(self):
        return self.conf.snd_dir

    @snd_dir.setter
    def snd_dir(self, snd_dir):
        if snd_dir != self.snd_dir:
            self.conf.list_index = 0
            self.conf.snd_dir = snd_dir

            self.snd = None
            self.view.SetVolume(None)

            self.frame.Title = APP_NAME
            self.UpdateFlist()
            self.SetDefaultSaveDir()
            self.EnableUI()


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
    else:
        # wx.SingleInstanceChecker を使えばできるけど、
        # そこまで必死になって阻止する必要もない
        pass

    return False


def sec_to_str(sec):
    m = sec / 60
    s = int(sec) % 60
    ms = int(sec * 1000) % 1000

    time_str = '%01d:%02d.%03d' % (m, s, ms)

    return time_str


def SetIcon(frame):
    try:
        icon = wx.Icon('icon.ico', wx.BITMAP_TYPE_ICO)
        frame.SetIcon(icon)
    except:
        pass

    if sys.platform == 'win32':
        try:
            handle = win32api.GetModuleHandle(None)
            exeName = win32api.GetModuleFileName(handle)
            icon = wx.Icon(exeName, wx.BITMAP_TYPE_ICO)

            frame.SetIcon(icon)
        except:
            pass


# ドラッグ・アンド・ドロップ処理
class DirDrop(wx.FileDropTarget):
    def __init__(self, app):
        wx.FileDropTarget.__init__(self)
        self.app = app

    def OnDropFiles(self, x, y, names):
        if len(names) == 1:
            if os.path.isdir(names[0]):
                snd_dir = names[0]
            else:
                snd_dir = os.path.dirname(names[0])

            self.app.snd_dir = snd_dir


# py2exeでは、この関数をmyfile.pyに置くと
# __file__がlib/library.zipになってしまうのでここに置く
def get_cur_dir():
    try:
        cur_dir = os.path.dirname(os.path.abspath(__file__))
    except:
        cur_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

    return cur_dir


if __name__ == '__main__':
    main()
