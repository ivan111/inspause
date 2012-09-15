# -*- coding: utf-8 -*-

import codecs
from ConfigParser import SafeConfigParser, NoSectionError, NoOptionError
import os
import random
import threading

try:
    import win32api
except:
    pass

import wx
import wx.lib.masked as masked
import wx.xrc as xrc

from findsound import find_sound, DEFAULT_SIL_LV, DEFAULT_SIL_DUR, DEFAULT_LABEL_DUR
from insertpause import insert_pause, DEFAULT_FACTOR, DEFAULT_ADD
from labels import Labels
from waveview import WaveView, EVT_CHANGE_CUR_ID, EVT_EOF_ID


CONFIG_FILE = 'settings.ini'
LABELS_DIR = 'labels'
PAUSE_DIR = 'pause'

ID_SAVE= wx.NewId()
ID_HEAD = wx.NewId()
ID_PLAY = wx.NewId()
ID_PLAYPAUSE = wx.NewId()
ID_PLAYSEL = wx.NewId()
ID_PLAYBORDER = wx.NewId()
ID_PAUSE = wx.NewId()
ID_TAIL = wx.NewId()
ID_ZOOMIN = wx.NewId()
ID_ZOOMOUT = wx.NewId()

ID_INSERT = wx.NewId()
ID_REMOVE = wx.NewId()
ID_CUT = wx.NewId()
ID_MERGE_L = wx.NewId()
ID_MERGE_R = wx.NewId()
ID_UNDO = wx.NewId()
ID_REDO = wx.NewId()

ONLY_SELECTED_FILE = 0
ALL_FILES = 1

surnames = [u'佐藤', u'鈴木', u'高橋', u'田中', u'伊藤', u'山本', u'渡辺', u'中村', u'小林', u'加藤',
        u'吉田', u'山田', u'佐々木', u'山口', u'松本', u'井上', u'木村', u'斎藤', u'林', u'清水',
        u'山崎', u'阿部', u'森', u'池田', u'橋本', u'山下', u'石川', u'中島', u'前田', u'藤田',
        u'小川', u'後藤', u'岡田', u'長谷川', u'村上', u'石井', u'近藤', u'坂本', u'遠藤', u'藤井',
        u'青木', u'西村', u'福田', u'斉藤', u'太田', u'藤原', u'三浦', u'岡本', u'松田', u'中川',
        u'中野', u'小野', u'原田', u'田村', u'竹内', u'金子', u'和田', u'中山', u'石田', u'上田',
        u'森田', u'柴田', u'酒井', u'原', u'横山', u'宮崎', u'工藤', u'宮本', u'内田', u'高木',
        u'谷口', u'安藤', u'大野', u'丸山', u'今井', u'高田', u'藤本', u'河野', u'小島', u'村田',
        u'武田', u'上野', u'杉山', u'増田', u'平野', u'菅原', u'小山', u'久保', u'大塚', u'千葉',
        u'松井', u'岩崎', u'木下', u'松尾', u'野口', u'野村', u'佐野', u'菊地', u'渡部', u'大西',
        u'ズルムケ', u'おっさん', u'おばはん', u'おやじ', u'おふくろ', u'海老蔵']


def main():
    app = wx.App(redirect=True, filename="log.txt")
    #app = wx.App()
    frame = MainFrame(None, -1, 'InsPause')
    frame.Show(True)
    app.MainLoop()


class DirDrop(wx.FileDropTarget):
    def __init__(self, window):
        wx.FileDropTarget.__init__(self)
        self.window = window

    def OnDropFiles(self, x, y, names):
        if len(names) == 1:
            if os.path.isdir(names[0]):
                self.window.set_dir(names[0])
            else:
                self.window.set_dir(os.path.dirname(names[0]))


class MainFrame(wx.Frame):
    def __init__(self, parent, id, title):
        wx.Frame.__init__(self, parent, id, title)

        try:
            exeName = win32api.GetModuleFileName(win32api.GetModuleHandle(None))
            icon = wx.Icon(exeName, wx.BITMAP_TYPE_ICO)
            self.SetIcon(icon)
        except:
            pass

        self.dir_name = None
        self.read_conf()
        self.InitUI()

        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Connect(-1, -1, EVT_CHANGE_CUR_ID, self.OnChangeCur)
        self.Connect(-1, -1, EVT_EOF_ID, self.OnEOF)

        if self.dir_name_conf and os.path.exists(self.dir_name_conf):
            self.set_dir(self.dir_name_conf)

        self.Centre()
        self.Show(True)

    def read_conf(self):
        try:
            conf = SafeConfigParser()
            f = codecs.open(CONFIG_FILE, 'r', 'utf8')
            conf.readfp(f)

            sil_lv = int(conf.get('find', 'sil_lv'))
            self.sil_lv = max(0, min(sil_lv, 100))
            sil_dur = float(conf.get('find', 'sil_dur'))
            self.sil_dur = max(0.01, min(sil_dur, 9.99))
            label_dur = float(conf.get('find', 'label_dur'))
            self.label_dur = max(0.0, min(label_dur, 9.99))

            factor = float(conf.get('pause', 'factor'))
            self.factor = max(0.01, min(factor, 9.99))
            add = float(conf.get('pause', 'add'))
            self.add = max(0.0, min(add, 9.99))

            self.dir_name_conf = conf.get('dir', 'wav')
        except (NoSectionError, IOError, NoOptionError):
            self.sil_lv = DEFAULT_SIL_LV
            self.sil_dur = DEFAULT_SIL_DUR
            self.label_dur = DEFAULT_LABEL_DUR

            self.factor = DEFAULT_FACTOR
            self.add = DEFAULT_ADD

            self.dir_name_conf = ''

    def write_conf(self):
        conf = SafeConfigParser()

        conf.add_section('find')
        conf.set('find', 'sil_lv', str(self.sld_sil_lv.GetValue()))
        conf.set('find', 'sil_dur', str(self.nc_sil_dur.GetValue()))
        conf.set('find', 'label_dur', str(self.nc_lbl_dur.GetValue()))

        conf.add_section('pause')
        conf.set('pause', 'factor', str(self.nc_factor.GetValue()))
        conf.set('pause', 'add', str(self.nc_add.GetValue()))

        conf.add_section('dir')
        if self.dir_name is None:
            self.dir_name = ''
        conf.set('dir', 'wav', self.dir_name.encode('utf8'))

        f = open(CONFIG_FILE, 'w')
        conf.write(f)

    def InitUI(self):
        self.init_toolbar()

        dd = DirDrop(self)
        self.SetDropTarget(dd)

        splitter = wx.SplitterWindow(self, -1, style=wx.SP_3D)

        # WaveView
        self.view = WaveView(splitter, -1, listener=self)

        panel = wx.Panel(splitter)
        hbox = wx.BoxSizer(wx.HORIZONTAL)

        # Find Sound Panel
        fsp = wx.Panel(panel)
        self.fsp = fsp
        hbox.Add(fsp)

        sb_fs = wx.StaticBox(fsp, label=u'ポーズ情報作成')
        vbox_fs = wx.StaticBoxSizer(sb_fs, wx.VERTICAL)
        
        st_sil_lv = wx.StaticText(fsp, label=u'無音レベル', style=wx.ALIGN_CENTRE)
        vbox_fs.Add(st_sil_lv, flag=wx.ALL, border=5)

        self.sld_sil_lv = wx.Slider(fsp, size=(120, -1), value=self.sil_lv, minValue=0, maxValue=100, style=wx.SL_HORIZONTAL)
        self.sld_sil_lv.Bind(wx.EVT_SCROLL, self.OnSilLvScroll)
        vbox_fs.Add(self.sld_sil_lv, flag=wx.LEFT|wx.RIGHT, border=5)

        st = wx.StaticText(fsp, label=u'無音の最低長さ', style=wx.ALIGN_CENTRE)
        vbox_fs.Add(st, flag=wx.ALL, border=5)

        pnl_fs1 = wx.Panel(fsp)
        hb = wx.BoxSizer(wx.HORIZONTAL)

        nc_sil_dur = masked.numctrl.NumCtrl(pnl_fs1) 
        nc_sil_dur.SetAllowNegative(False) 
        nc_sil_dur.SetIntegerWidth(3)
        nc_sil_dur.SetFractionWidth(2)
        nc_sil_dur.SetValue(self.sil_dur)
        self.nc_sil_dur = nc_sil_dur
        hb.Add(self.nc_sil_dur, flag=wx.LEFT, border=5)

        st = wx.StaticText(pnl_fs1, label=u'秒', style=wx.ALIGN_CENTRE)
        hb.Add(st, flag=wx.ALL, border=5)

        vbox_fs.Add(pnl_fs1)
        pnl_fs1.SetSizer(hb)


        st_lbl_dur = wx.StaticText(fsp, label=u'余裕感', style=wx.ALIGN_CENTRE)
        vbox_fs.Add(st_lbl_dur, flag=wx.ALL, border=5)

        pnl_fs2 = wx.Panel(fsp)
        hb = wx.BoxSizer(wx.HORIZONTAL)

        nc_lbl_dur = masked.numctrl.NumCtrl(pnl_fs2) 
        nc_lbl_dur.SetAllowNegative(False) 
        nc_lbl_dur.SetIntegerWidth(3)
        nc_lbl_dur.SetFractionWidth(2)
        nc_lbl_dur.SetValue(self.label_dur)
        self.nc_lbl_dur = nc_lbl_dur
        hb.Add(self.nc_lbl_dur, flag=wx.LEFT, border=5)

        st = wx.StaticText(pnl_fs2, label=u'秒', style=wx.ALIGN_CENTRE)
        hb.Add(st, flag=wx.ALL, border=5)

        vbox_fs.Add(pnl_fs2)
        pnl_fs2.SetSizer(hb)


        self.btn_find = wx.Button(fsp, label=u'ポーズ情報作成')
        vbox_fs.Add(self.btn_find, flag=wx.ALL, border=5)
        self.btn_find.Bind(wx.EVT_BUTTON, self.OnFindSound)
        
        fsp.SetSizer(vbox_fs)

        # Insert Pause Panel
        ipp = wx.Panel(panel)
        self.ipp = ipp
        hbox.Add(ipp)

        sb_ip = wx.StaticBox(ipp, label=u'ポーズ音声作成')
        vbox_ip = wx.StaticBoxSizer(sb_ip, wx.VERTICAL)
        

        sb = wx.StaticBox(ipp, label=u'ポーズの長さ')
        sbvbox = wx.StaticBoxSizer(sb, wx.VERTICAL)
        vbox_ip.Add(sbvbox, flag=wx.ALL, border=5)

        pnl_ip1 = wx.Panel(ipp)
        hb = wx.BoxSizer(wx.HORIZONTAL)

        st = wx.StaticText(pnl_ip1, label=u'選択範囲 ×', style=wx.ALIGN_CENTRE)
        hb.Add(st, flag=wx.ALL, border=5)

        nc_factor = masked.numctrl.NumCtrl(pnl_ip1) 
        nc_factor.SetAllowNegative(False) 
        nc_factor.SetIntegerWidth(3)
        nc_factor.SetFractionWidth(2)
        nc_factor.SetValue(self.factor)
        self.nc_factor = nc_factor
        hb.Add(nc_factor)

        sbvbox.Add(pnl_ip1)
        pnl_ip1.SetSizer(hb)


        pnl_ip2 = wx.Panel(ipp)
        hb = wx.BoxSizer(wx.HORIZONTAL)

        st = wx.StaticText(pnl_ip2, label=u'＋', style=wx.ALIGN_CENTRE)
        hb.Add(st, flag=wx.ALL, border=5)

        nc_add = masked.numctrl.NumCtrl(pnl_ip2) 
        nc_add.SetAllowNegative(False) 
        nc_add.SetIntegerWidth(3)
        nc_add.SetFractionWidth(2)
        nc_add.SetValue(self.add)
        self.nc_add = nc_add
        hb.Add(nc_add)

        st = wx.StaticText(pnl_ip2, label=u'秒', style=wx.ALIGN_CENTRE)
        hb.Add(st, flag=wx.ALL, border=5)

        sbvbox.Add(pnl_ip2)
        pnl_ip2.SetSizer(hb)


        choices = (u'右画面で選択したやつ', u'全ファイル')
        self.rb = wx.RadioBox(ipp, label=u'対象', choices=choices, style=wx.RA_VERTICAL)
        vbox_ip.Add(self.rb, flag=wx.ALL, border=5)


        self.btn_inspa = wx.Button(ipp, label=u'ポーズ音声作成')
        vbox_ip.Add(self.btn_inspa, flag=wx.ALL, border=5)
        self.btn_inspa.Bind(wx.EVT_BUTTON, self.OnInsertPause)

        ipp.SetSizer(vbox_ip)

        # ListCtrl
        self.list = wx.ListCtrl(panel, -1, style=wx.LC_REPORT)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnWavClick, self.list)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected, self.list)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnItemDeselected, self.list)
        hbox.Add(self.list, 1, wx.EXPAND)

        panel.SetSizer(hbox)

        splitter.SplitHorizontally(self.view, panel)

        self.set_enable()

    def init_toolbar(self):

        self.tb = self.CreateToolBar()
        tb_head = self.tb.AddLabelTool(ID_HEAD, 'Head', wx.Bitmap('icon/head.png'))
        tb_head.ShortHelp = u'先頭へ'
        tb_play = self.tb.AddLabelTool(ID_PLAY, 'Play', wx.Bitmap('icon/play.png'))
        tb_play.ShortHelp = u'再生'
        tb_playpause = self.tb.AddLabelTool(ID_PLAYPAUSE, 'Pause Mode Play', wx.Bitmap('icon/playpause.png'))
        tb_playpause.ShortHelp = u'ポーズモード再生'
        tb_playsel = self.tb.AddLabelTool(ID_PLAYSEL, 'Play Selected Range', wx.Bitmap('icon/playsel.png'))
        tb_playsel.ShortHelp = u'選択範囲を再生'
        tb_playborder = self.tb.AddLabelTool(ID_PLAYBORDER, 'Play Border', wx.Bitmap('icon/playborder.png'))
        tb_playborder.ShortHelp = u'境界を再生'
        tb_pause = self.tb.AddLabelTool(ID_PAUSE, 'Pause', wx.Bitmap('icon/pause.png'))
        tb_pause.ShortHelp = u'一時停止'
        tb_tail = self.tb.AddLabelTool(ID_TAIL, 'Tail', wx.Bitmap('icon/tail.png'))
        tb_tail.ShortHelp = u'末尾へ'
        tb_zoomin = self.tb.AddLabelTool(ID_ZOOMIN, 'Zooom In', wx.Bitmap('icon/zoomin.png'))
        tb_zoomin.ShortHelp = u'拡大'
        tb_zoomout = self.tb.AddLabelTool(ID_ZOOMOUT, 'Zooom Out', wx.Bitmap('icon/zoomout.png'))
        tb_zoomout.ShortHelp = u'縮小'

        self.tb.AddSeparator()

        tb_cut = self.tb.AddLabelTool(ID_CUT, 'Cut', wx.Bitmap('icon/cut.png'))
        tb_cut.ShortHelp = u'分割'
        tb_mergel = self.tb.AddLabelTool(ID_MERGE_L, 'Merge Left', wx.Bitmap('icon/mergeleft.png'))
        tb_mergel.ShortHelp = u'左と結合'
        tb_merger = self.tb.AddLabelTool(ID_MERGE_R, 'Merge Right', wx.Bitmap('icon/mergeright.png'))
        tb_merger.ShortHelp = u'右と結合'
        tb_undo = self.tb.AddLabelTool(ID_UNDO, 'Undo', wx.Bitmap('icon/undo.png'))
        tb_undo.ShortHelp = u'元に戻す'
        tb_redo = self.tb.AddLabelTool(ID_REDO, 'Redo', wx.Bitmap('icon/redo.png'))
        tb_redo.ShortHelp = u'やり直し'
        tb_save = self.tb.AddLabelTool(ID_SAVE, 'Save', wx.Bitmap('icon/save.png'))
        tb_save.ShortHelp = u'ポーズ情報の保存'
        tb_insert = self.tb.AddLabelTool(ID_INSERT, 'Insert Label', wx.Bitmap('icon/insert.png'))
        tb_insert.ShortHelp = u'ポーズの挿入'
        tb_remove = self.tb.AddLabelTool(ID_REMOVE, 'Remove Label', wx.Bitmap('icon/remove.png'))
        tb_remove.ShortHelp = u'ポーズの削除'
        self.tb.Realize()

        self.Bind(wx.EVT_TOOL, self.OnSave, tb_save)
        self.Bind(wx.EVT_TOOL, self.OnHead, tb_head)
        self.Bind(wx.EVT_TOOL, self.OnPlay, tb_play)
        self.Bind(wx.EVT_TOOL, self.OnPlayPause, tb_playpause)
        self.Bind(wx.EVT_TOOL, self.OnPlaySel, tb_playsel)
        self.Bind(wx.EVT_TOOL, self.OnPlayBorder, tb_playborder)
        self.Bind(wx.EVT_TOOL, self.OnPause, tb_pause)
        self.Bind(wx.EVT_TOOL, self.OnTail, tb_tail)
        self.Bind(wx.EVT_TOOL, self.OnZoomIn, tb_zoomin)
        self.Bind(wx.EVT_TOOL, self.OnZoomOut, tb_zoomout)

        self.Bind(wx.EVT_TOOL, self.OnCut, tb_cut)
        self.Bind(wx.EVT_TOOL, self.OnMergeLeft, tb_mergel)
        self.Bind(wx.EVT_TOOL, self.OnMergeRight, tb_merger)
        self.Bind(wx.EVT_TOOL, self.OnUndo, tb_undo)
        self.Bind(wx.EVT_TOOL, self.OnRedo, tb_redo)
        self.Bind(wx.EVT_TOOL, self.OnInsert, tb_insert)
        self.Bind(wx.EVT_TOOL, self.OnRemove, tb_remove)

    def set_enable(self):
        self.tb.EnableTool(ID_SAVE, self.view.can_save())
        self.tb.EnableTool(ID_HEAD, self.view.can_head())
        self.tb.EnableTool(ID_PLAY, self.view.can_play())
        self.tb.EnableTool(ID_PLAYPAUSE, self.view.can_pause_mode_play())
        self.tb.EnableTool(ID_PLAYSEL, self.view.can_playsel())
        self.tb.EnableTool(ID_PLAYBORDER, self.view.can_play_border())
        self.tb.EnableTool(ID_PAUSE, self.view.can_pause())
        self.tb.EnableTool(ID_TAIL, self.view.can_tail())
        self.tb.EnableTool(ID_ZOOMIN, self.view.can_zoomin())
        self.tb.EnableTool(ID_ZOOMOUT, self.view.can_zoomout())

        self.tb.EnableTool(ID_CUT, self.view.can_cut())
        self.tb.EnableTool(ID_MERGE_L, self.view.can_merge_left())
        self.tb.EnableTool(ID_MERGE_R, self.view.can_merge_right())
        self.tb.EnableTool(ID_UNDO, self.view.can_undo())
        self.tb.EnableTool(ID_REDO, self.view.can_redo())
        self.tb.EnableTool(ID_INSERT, self.view.can_insert_label())
        self.tb.EnableTool(ID_REMOVE, self.view.can_remove_label())

        if self.dir_name and (not self.view.playing):
            self.fsp.Enable()
            self.ipp.Enable()
            if self.list.SelectedItemCount == 0:
                self.rb.EnableItem(ONLY_SELECTED_FILE, False)
                self.rb.SetSelection(ALL_FILES)
            else:
                self.rb.EnableItem(ONLY_SELECTED_FILE, True)
        else:
            self.fsp.Disable()
            self.ipp.Disable()

    def confirm_save(self):
        if self.view.can_save():
            your_name = surnames[random.randint(0, len(surnames)-1)]
            dlg = wx.MessageDialog(self, u'%sさん、変更を保存しますか？' % your_name, u'確認',  wx.YES_NO)
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

        self.dir_name = dir_name

        self.list.ClearAll()
        self.list.InsertColumn(0, 'wave', width=100)
        self.list.InsertColumn(1, 'labels', width=100)

        wav_files = []

        for name in os.listdir(dir_name):
            if name.endswith('.wav'):
                wav_files.append(name)

        if len(wav_files) == 0:
            return

        labels_dir = os.path.join(dir_name, LABELS_DIR)
        if not os.path.exists(labels_dir):
            os.mkdir(labels_dir)            

        wav_files.sort()

        for i, name in enumerate(wav_files):
            index = self.list.InsertStringItem(i, name)
            self.list.SetStringItem(index, 1, '%03d.txt' % (i+1))

        self.list.Select(0)
        wav_name = self.list.GetItem(0, 0).GetText()
        wav_file = os.path.join(self.dir_name,  wav_name)
        labels_name = self.list.GetItem(0, 1).GetText()
        labels_file = os.path.join(self.dir_name, LABELS_DIR, labels_name)
        self.set_sound(wav_file, labels_file)

    def OnSilLvScroll(self, evt):
        val = self.sld_sil_lv.GetValue()
        self.view.sil_lv = val

    def OnWavClick(self, evt):
        self.confirm_save()

        wav_file = os.path.join(self.dir_name, evt.GetText())
        labels_file = self.list.GetItem(evt.m_itemIndex, 1).GetText()
        labels_file = os.path.join(self.dir_name, LABELS_DIR, labels_file)

        self.set_sound(wav_file, labels_file)

    def set_sound(self, wav_file, labels_file):
        if not self.view.set_sound(wav_file):
            return

        if not os.path.exists(labels_file):
            labels = find_sound(wav_file)
            labels.write(labels_file)

        self.view.set_labels(labels_file)
        self.view.sil_lv = self.sld_sil_lv.GetValue()

        self.set_enable()

    def OnItemSelected(self, evt):
        self.rb.EnableItem(ONLY_SELECTED_FILE, True)

    def OnItemDeselected(self, evt):
        self.rb.EnableItem(ONLY_SELECTED_FILE, False)
        self.rb.SetSelection(ALL_FILES)

    def OnFindSound(self, evt):
        sil_lv = self.sld_sil_lv.GetValue()
        sil_dur = self.nc_sil_dur.GetValue()
        before_label_dur = after_label_dur = self.nc_lbl_dur.GetValue()

        self.view.find(sil_lv, sil_dur, before_label_dur, after_label_dur)

    def OnInsertPause(self, evt):
        if not self.confirm_save():
            wx.MessageBox(u'じゃあ、作ってやらん。', u'もう怒った', wx.OK)
            return

        pause_dir = os.path.join(self.dir_name, PAUSE_DIR)
        if not os.path.exists(pause_dir):
            os.mkdir(pause_dir)

        wav_names = []
        labels_names = []

        if (self.rb.Selection == ONLY_SELECTED_FILE) and (self.list.SelectedItemCount != 0):
            item = self.list.GetFirstSelected()
            while item != -1:
                wav_names.append(self.list.GetItemText(item))
                labels_names.append(self.list.GetItem(item, 1).GetText())
                item = self.list.GetNextSelected(item)
        else:
            for i in range(self.list.ItemCount):
                wav_names.append(self.list.GetItem(i, 0).GetText())
                labels_names.append(self.list.GetItem(i, 1).GetText())

        dlg = wx.ProgressDialog(u'ポーズファイル作成', u'ポーズファイル作成中\n残りファイル数%d' % len(wav_names),
                maximum=len(wav_names), parent=self, style = wx.PD_AUTO_HIDE | wx.PD_APP_MODAL)

        for i, (wav_name, labels_name) in enumerate(zip(wav_names, labels_names)):
            dlg.Update(i, u'ポーズファイル作成中\n残りファイル数%d' % (len(wav_names) - i))

            wav_file = os.path.join(self.dir_name, wav_name)
            labels_file = os.path.join(self.dir_name, LABELS_DIR, labels_name)
            pause_file = os.path.join(self.dir_name, PAUSE_DIR, wav_name)

            if not os.path.exists(labels_file):
                labels = find_sound(wav_file)
                labels.write(labels_file)

            insert_pause(wav_file, pause_file, labels_file, self.nc_factor.GetValue(), self.nc_add.GetValue())

        dlg.Destroy()

        your_name = surnames[random.randint(0, len(surnames)-1)]
        pause_dir = os.path.join(self.dir_name, PAUSE_DIR)
        wx.MessageBox(u'おい、%s！ここにできちょんけん\n%s' % (your_name, pause_dir), u'できたで', wx.OK)

    def OnInsert(self, evt):
        self.view.insert_label()
        self.set_enable()

    def OnRemove(self, evt):
        self.view.remove_label()
        self.set_enable()

    def OnSave(self, evt):
        self.view.save()
        self.set_enable()

    def OnHead(self, evt):
        self.view.head()
        self.set_enable()
        if self.view.playing:
            self.tb.EnableTool(ID_HEAD, True)

    def OnPlay(self, evt):
        self.view.play()
        self.set_enable()
        self.tb.EnableTool(ID_HEAD, True)

    def OnPlayPause(self, evt):
        factor = self.nc_factor.GetValue()
        add = self.nc_add.GetValue()
        self.view.pause_mode_play(factor, add)
        self.set_enable()
        self.tb.EnableTool(ID_HEAD, True)

    def OnPlaySel(self, evt):
        self.view.playsel()
        self.set_enable()
        self.tb.EnableTool(ID_HEAD, True)

    def OnPlayBorder(self, evt):
        self.view.play_border()
        self.set_enable()
        self.tb.EnableTool(ID_HEAD, True)

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

        self.view.cancel()
        self.write_conf()
        self.Destroy()

if __name__ == '__main__':
    main()

