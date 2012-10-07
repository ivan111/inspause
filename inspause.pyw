# -*- coding: utf-8 -*-

import codecs
from ConfigParser import SafeConfigParser, NoSectionError, NoOptionError
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
import wx.lib.masked as masked

import persist

import findsound
from findsound import find_sound, SIL_LV, SIL_DUR, RATE, SND_DUR
from findsound import LABEL_BEFORE_DUR, LABEL_AFTER_DUR, WAV_SCALE
from insertpause import insert_pause, FACTOR, ADD
import labels
from labels import MIN_DUR as LBL_MIN_DUR
import revpause
from revpause import rev_pause, SIL_LV as REV_SIL_LV, SIL_DUR as REV_SIL_DUR
from revpause import RATE as REV_RATE, TOLERABLE_SCORE
from revpause import WAV_SCALE as REV_WAV_SCALE
import waveview
from waveview import WaveView, EVT_CHANGE_CUR_ID, EVT_EOF_ID
from waveview import SEEK, SEEK_CTRL, SEEK_SHIFT, RATE as WV_RATE
from waveview import MIN_RATE as WV_MIN_RATE, MAX_RATE as WV_MAX_RATE

APP_NAME = 'InsPause'

PERSIST_FILE = 'persist.txt'
LOG_FILE = 'log.txt'
CONFIG_FILE = 'settings.ini'
LABELS_DIR = 'labels'
PAUSE_DIR = 'pause'
REVERSE_DIR = 'reverse'
ERROR_FILE = 'error.txt'

ID_SAVE = wx.NewId()
ID_HEAD = wx.NewId()
ID_PLAY = wx.NewId()
ID_PLAYPAUSE = wx.NewId()
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

SIL_DUR_MIN = 0.01
SIL_DUR_MAX = 9.99
FACTOR_MIN = 0.0
FACTOR_MAX = 9.99
ADD_MIN = 0.0
ADD_MAX = 9.99

try:
    dirName = os.path.dirname(os.path.abspath(__file__))
except:
    dirName = os.path.dirname(os.path.abspath(sys.argv[0]))

persist_file = os.path.join(dirName, PERSIST_FILE)


def main():
    app = wx.App(redirect=True, filename=LOG_FILE)
    frame = MainFrame(None, -1, APP_NAME)
    frame.Show(True)
    app.MainLoop()


class MainFrame(wx.Frame):
    def __init__(self, parent, id, title):
        wx.Frame.__init__(self, parent, id, title,
                          size=(600, 500), name='inspause')

        self.pm = persist.PersistenceManager.Get()
        self.pm.SetPersistenceFile(persist_file)

        try:
            handle = win32api.GetModuleHandle(None)
            exeName = win32api.GetModuleFileName(handle)
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

        wx.CallAfter(self.register_controls)

        self.set_debug()

        self.Centre()
        self.Show(True)

    def set_debug(self):
        if self.debug:
            revpause.DEBUG = True
            waveview.DEBUG = True

    def register_controls(self):
        self.Freeze()
        self.register()
        self.Thaw()

    def register(self, children=None):
        self.pm.RegisterAndRestore(self)
        self.pm.RegisterAndRestore(self.list)
        self.pm.RegisterAndRestore(self.splitter)

    def read_conf(self):
        conf = MyConfigParser()
        try:
            if os.name == 'nt':
                f = codecs.open(CONFIG_FILE, 'r', 'CP932')
            else:
                f = codecs.open(CONFIG_FILE, 'r', 'utf8')
            conf.readfp(f)
        except IOError:
            pass

        self.debug = conf.mygetboolean('DEFAULT', 'debug', False)

        self.dir_name_conf = conf.myget('dir', 'wav', '')
        self.list_index = conf.mygetint('dir', 'index', 0)

        self.lbl_min_dur = conf.mygetfloat('label', 'min_dur', LBL_MIN_DUR)
        labels.MIN_DUR = self.lbl_min_dur

        self.sil_lv = conf.mygetint('find', 'sil_lv', SIL_LV, 0, 100)
        self.sil_dur = conf.mygetfloat('find', 'sil_dur', SIL_DUR,
            SIL_DUR_MIN, SIL_DUR_MAX)
        self.label_before_dur = conf.mygetfloat('find', 'label_before_dur',
            LABEL_BEFORE_DUR)
        self.label_after_dur = conf.mygetfloat('find', 'label_after_dur',
            LABEL_AFTER_DUR)
        self.rate = conf.mygetint('find', 'rate', RATE)
        self.snd_dur = conf.mygetfloat('find', 'snd_dur', SND_DUR)

        self.factor = conf.mygetfloat('pause', 'factor', FACTOR,
            FACTOR_MIN, FACTOR_MAX)
        self.add = conf.mygetfloat('pause', 'add', ADD, ADD_MIN, ADD_MAX)

        self.seek = conf.mygetint('view', 'seek', SEEK)
        waveview.SEEK = self.seek
        self.seek_ctrl = conf.mygetint('view', 'seek_ctrl', SEEK_CTRL)
        waveview.SEEK_CTRL = self.seek_ctrl
        self.seek_shift = conf.mygetint('view', 'seek_shift', SEEK_SHIFT)
        waveview.SEEK_SHIFT = self.seek_shift
        self.wv_rate = conf.mygetint('view', 'default_rate', WV_RATE)
        waveview.RATE = self.wv_rate
        self.wv_min_rate = conf.mygetint('view', 'min_rate', WV_MIN_RATE)
        waveview.MIN_RATE = self.wv_min_rate
        self.wv_max_rate = conf.mygetint('view', 'max_rate', WV_MAX_RATE)
        waveview.MAX_RATE = self.wv_max_rate
        self.wav_scale = conf.mygetint('view', 'wav_scale', WAV_SCALE, 1, 100)
        findsound.WAV_SCALE = self.wav_scale
        waveview.WAV_SCALE = self.wav_scale

        self.rev_sil_lv = conf.mygetint('reverse', 'sil_lv', REV_SIL_LV)
        self.rev_sil_dur = conf.mygetfloat('reverse', 'sil_dur', REV_SIL_DUR)
        self.rev_rate = conf.mygetint('reverse', 'rate', REV_RATE)
        self.tolerable_score = conf.mygetint('reverse', 'tolerable_score',
                TOLERABLE_SCORE)
        revpause.TOLERABLE_SCORE = self.tolerable_score
        self.rev_wav_scale = conf.mygetint('reverse', 'wav_scale',
                REV_WAV_SCALE, 1, 100)
        revpause.WAV_SCALE = self.rev_wav_scale

        self.dsp_toolbar = conf.mygetboolean('button', 'toolbar', True)
        self.dsp_head = conf.mygetboolean('button', 'head', True)
        self.dsp_play = conf.mygetboolean('button', 'play', True)
        self.dsp_playpause = conf.mygetboolean('button', 'pause_mode_play',
                True)
        self.dsp_playborder = conf.mygetboolean('button', 'play_near_cursor',
                True)
        self.dsp_pause = conf.mygetboolean('button', 'pause', True)
        self.dsp_tail = conf.mygetboolean('button', 'tail', True)
        self.dsp_zoomin = conf.mygetboolean('button', 'zoomin', True)
        self.dsp_zoomout = conf.mygetboolean('button', 'zoomout', True)
        self.dsp_separator = conf.mygetboolean('button', 'separator', True)
        self.dsp_cut = conf.mygetboolean('button', 'cut', True)
        self.dsp_mergeleft = conf.mygetboolean('button', 'merge_left', True)
        self.dsp_mergeright = conf.mygetboolean('button', 'merge_right', True)
        self.dsp_undo = conf.mygetboolean('button', 'undo', True)
        self.dsp_redo = conf.mygetboolean('button', 'redo', True)
        self.dsp_save = conf.mygetboolean('button', 'save', True)
        self.dsp_insert = conf.mygetboolean('button', 'insert', True)
        self.dsp_remove = conf.mygetboolean('button', 'remove', True)

    def write_conf(self):
        conf = SafeConfigParser()

        conf.set('DEFAULT', 'debug', self.to_onoff(self.debug))

        conf.add_section('dir')
        if self.dir_name is None:
            self.dir_name = ''
        if os.name == 'nt':
            conf.set('dir', 'wav', self.dir_name.encode('CP932'))
        else:
            conf.set('dir', 'wav', self.dir_name.encode('utf8'))

        conf.set('dir', 'index', str(self.list_index))

        conf.add_section('label')
        conf.set('label', 'min_dur', str(self.lbl_min_dur))

        conf.add_section('find')
        conf.set('find', 'sil_lv', str(self.sld_sil_lv.GetValue()))
        conf.set('find', 'sil_dur', str(self.nc_sil_dur.GetValue()))
        conf.set('find', 'label_before_dur', str(self.label_before_dur))
        conf.set('find', 'label_after_dur', str(self.label_after_dur))
        conf.set('find', 'rate', str(self.rate))
        conf.set('find', 'snd_dur', str(self.snd_dur))

        conf.add_section('pause')
        conf.set('pause', 'factor', str(self.nc_factor.GetValue()))
        conf.set('pause', 'add', str(self.nc_add.GetValue()))

        conf.add_section('view')
        conf.set('view', 'seek', str(self.seek))
        conf.set('view', 'seek_ctrl', str(self.seek_ctrl))
        conf.set('view', 'seek_shift', str(self.seek_shift))
        conf.set('view', 'default_rate', str(self.wv_rate))
        conf.set('view', 'min_rate', str(self.wv_min_rate))
        conf.set('view', 'max_rate', str(self.wv_max_rate))
        conf.set('view', 'wav_scale', str(self.wav_scale))

        conf.add_section('reverse')
        conf.set('reverse', 'sil_lv', str(self.rev_sil_lv))
        conf.set('reverse', 'sil_dur', str(self.rev_sil_dur))
        conf.set('reverse', 'rate', str(self.rev_rate))
        conf.set('reverse', 'tolerable_score', str(self.tolerable_score))
        conf.set('reverse', 'wav_scale', str(self.rev_wav_scale))

        conf.add_section('button')
        conf.set('button', 'toolbar', self.to_onoff(self.dsp_toolbar))
        conf.set('button', 'head', self.to_onoff(self.dsp_head))
        conf.set('button', 'play', self.to_onoff(self.dsp_play))
        conf.set('button', 'pause_mode_play',
                self.to_onoff(self.dsp_playpause))
        conf.set('button', 'play_near_cursor',
                self.to_onoff(self.dsp_playborder))
        conf.set('button', 'pause', self.to_onoff(self.dsp_pause))
        conf.set('button', 'tail', self.to_onoff(self.dsp_tail))
        conf.set('button', 'zoomin', self.to_onoff(self.dsp_zoomin))
        conf.set('button', 'zoomout', self.to_onoff(self.dsp_zoomout))
        conf.set('button', 'separator', self.to_onoff(self.dsp_separator))
        conf.set('button', 'cut', self.to_onoff(self.dsp_cut))
        conf.set('button', 'merge_left', self.to_onoff(self.dsp_mergeleft))
        conf.set('button', 'merge_right', self.to_onoff(self.dsp_mergeright))
        conf.set('button', 'undo', self.to_onoff(self.dsp_undo))
        conf.set('button', 'redo', self.to_onoff(self.dsp_redo))
        conf.set('button', 'save', self.to_onoff(self.dsp_save))
        conf.set('button', 'insert', self.to_onoff(self.dsp_insert))
        conf.set('button', 'remove', self.to_onoff(self.dsp_remove))

        f = open(CONFIG_FILE, 'w')
        conf.write(f)

    def to_onoff(self, val):
        if val:
            return "on"
        else:
            return "off"

    def InitUI(self):
        self.init_toolbar()

        dd = DirDrop(self)
        self.SetDropTarget(dd)

        splitter = wx.SplitterWindow(self, -1, style=wx.SP_3D,
                                     name='view_splitter')
        splitter.Bind(wx.EVT_SPLITTER_DCLICK, self.OnDoubleClick)
        splitter.SetMinimumPaneSize(50)
        self.splitter = splitter

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

        self.sld_sil_lv = wx.Slider(fsp, size=(120, -1), value=self.sil_lv,
                                    minValue=0, maxValue=100,
                                    style=wx.SL_HORIZONTAL)
        self.sld_sil_lv.Bind(wx.EVT_SCROLL, self.OnSilLvScroll)
        vbox_fs.Add(self.sld_sil_lv, flag=wx.LEFT | wx.RIGHT, border=5)

        st = wx.StaticText(fsp, label=u'無音の最低長さ', style=wx.ALIGN_CENTRE)
        vbox_fs.Add(st, flag=wx.ALL, border=5)

        pnl_fs1 = wx.Panel(fsp)
        hb = wx.BoxSizer(wx.HORIZONTAL)

        nc_sil_dur = masked.numctrl.NumCtrl(pnl_fs1)
        nc_sil_dur.SetAllowNegative(False)
        nc_sil_dur.SetIntegerWidth(1)
        nc_sil_dur.SetFractionWidth(2)
        nc_sil_dur.SetValue(self.sil_dur)
        nc_sil_dur.SetMin(SIL_DUR_MIN)
        nc_sil_dur.SetMax(SIL_DUR_MAX)
        nc_sil_dur.SetLimited(True)
        self.nc_sil_dur = nc_sil_dur
        hb.Add(self.nc_sil_dur, flag=wx.LEFT, border=5)

        st = wx.StaticText(pnl_fs1, label=u'秒', style=wx.ALIGN_CENTRE)
        hb.Add(st, flag=wx.ALL, border=5)

        vbox_fs.Add(pnl_fs1)
        pnl_fs1.SetSizer(hb)

        self.btn_find = wx.Button(fsp, label=u'ポーズ情報作成')
        vbox_fs.Add(self.btn_find, flag=wx.ALL, border=5)
        self.btn_find.Bind(wx.EVT_BUTTON, self.OnFindSound)

        self.btn_reverse = wx.Button(fsp, label=u'ポーズwavから作成')
        vbox_fs.Add(self.btn_reverse, flag=wx.ALL, border=5)
        self.btn_reverse.Bind(wx.EVT_BUTTON, self.OnReverse)

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
        nc_factor.SetIntegerWidth(1)
        nc_factor.SetFractionWidth(2)
        nc_factor.SetValue(self.factor)
        nc_factor.SetMin(FACTOR_MIN)
        nc_factor.SetMax(FACTOR_MAX)
        nc_factor.SetLimited(True)
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
        nc_add.SetIntegerWidth(1)
        nc_add.SetFractionWidth(2)
        nc_add.SetValue(self.add)
        nc_add.SetMin(ADD_MIN)
        nc_add.SetMax(ADD_MAX)
        nc_add.SetLimited(True)
        self.nc_add = nc_add
        hb.Add(nc_add)

        st = wx.StaticText(pnl_ip2, label=u'秒', style=wx.ALIGN_CENTRE)
        hb.Add(st, flag=wx.ALL, border=5)

        sbvbox.Add(pnl_ip2)
        pnl_ip2.SetSizer(hb)

        self.btn_inspa = wx.Button(ipp, label=u'ポーズ音声作成')
        vbox_ip.Add(self.btn_inspa, flag=wx.ALL, border=5)
        self.btn_inspa.Bind(wx.EVT_BUTTON, self.OnInsertPause)

        ipp.SetSizer(vbox_ip)

        # ListCtrl
        self.list = wx.ListCtrl(panel, -1, style=wx.LC_REPORT,
                                name='file_list_ctrl')
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnWavClick, self.list)
        hbox.Add(self.list, 1, wx.EXPAND)

        panel.SetSizer(hbox)

        splitter.SplitHorizontally(self.view, panel)

        self.set_enable()

    def init_toolbar(self):
        if not self.dsp_toolbar:
            return

        self.tb = self.CreateToolBar()

        if self.dsp_head:
            tb_head = self.tb.AddLabelTool(ID_HEAD, 'Head',
                    wx.Bitmap('icon/head.png'))
            tb_head.ShortHelp = u'先頭へ(Home)'
            self.Bind(wx.EVT_TOOL, self.OnHead, tb_head)

        if self.dsp_play:
            tb_play = self.tb.AddLabelTool(ID_PLAY, 'Play',
                    wx.Bitmap('icon/play.png'))
            tb_play.ShortHelp = u'再生(Space)'
            self.Bind(wx.EVT_TOOL, self.OnPlay, tb_play)

        if self.dsp_playpause:
            tb_playpause = self.tb.AddLabelTool(ID_PLAYPAUSE,
                    'Pause Mode Play', wx.Bitmap('icon/playpause.png'))
            tb_playpause.ShortHelp = u'ポーズモード再生'
            self.Bind(wx.EVT_TOOL, self.OnPlayPause, tb_playpause)

        if self.dsp_playborder:
            tb_playborder = self.tb.AddLabelTool(ID_PLAYBORDER, 'Play Border',
                    wx.Bitmap('icon/playborder.png'))
            tb_playborder.ShortHelp = u'もしカット再生(b)'
            self.Bind(wx.EVT_TOOL, self.OnPlayBorder, tb_playborder)

        if self.dsp_pause:
            tb_pause = self.tb.AddLabelTool(ID_PAUSE, 'Pause',
                    wx.Bitmap('icon/pause.png'))
            tb_pause.ShortHelp = u'一時停止(Space)'
            self.Bind(wx.EVT_TOOL, self.OnPause, tb_pause)

        if self.dsp_tail:
            tb_tail = self.tb.AddLabelTool(ID_TAIL, 'Tail',
                    wx.Bitmap('icon/tail.png'))
            tb_tail.ShortHelp = u'末尾へ(End)'
            self.Bind(wx.EVT_TOOL, self.OnTail, tb_tail)

        if self.dsp_zoomin:
            tb_zoomin = self.tb.AddLabelTool(ID_ZOOMIN, 'Zooom In',
                    wx.Bitmap('icon/zoomin.png'))
            tb_zoomin.ShortHelp = u'拡大(+)'
            self.Bind(wx.EVT_TOOL, self.OnZoomIn, tb_zoomin)

        if self.dsp_zoomout:
            tb_zoomout = self.tb.AddLabelTool(ID_ZOOMOUT, 'Zooom Out',
                    wx.Bitmap('icon/zoomout.png'))
            tb_zoomout.ShortHelp = u'縮小(-)'
            self.Bind(wx.EVT_TOOL, self.OnZoomOut, tb_zoomout)

        if self.dsp_separator:
            self.tb.AddSeparator()

        if self.dsp_cut:
            tb_cut = self.tb.AddLabelTool(ID_CUT, 'Cut',
                    wx.Bitmap('icon/cut.png'))
            tb_cut.ShortHelp = u'分割(c)'
            self.Bind(wx.EVT_TOOL, self.OnCut, tb_cut)

        if self.dsp_mergeleft:
            tb_mergel = self.tb.AddLabelTool(ID_MERGE_L, 'Merge Left',
                    wx.Bitmap('icon/mergeleft.png'))
            tb_mergel.ShortHelp = u'左と結合(l)'
            self.Bind(wx.EVT_TOOL, self.OnMergeLeft, tb_mergel)

        if self.dsp_mergeright:
            tb_merger = self.tb.AddLabelTool(ID_MERGE_R, 'Merge Right',
                    wx.Bitmap('icon/mergeright.png'))
            tb_merger.ShortHelp = u'右と結合(r)'
            self.Bind(wx.EVT_TOOL, self.OnMergeRight, tb_merger)

        if self.dsp_undo:
            tb_undo = self.tb.AddLabelTool(ID_UNDO, 'Undo',
                    wx.Bitmap('icon/undo.png'))
            tb_undo.ShortHelp = u'元に戻す(Ctrl+z)'
            self.Bind(wx.EVT_TOOL, self.OnUndo, tb_undo)

        if self.dsp_redo:
            tb_redo = self.tb.AddLabelTool(ID_REDO, 'Redo',
                    wx.Bitmap('icon/redo.png'))
            tb_redo.ShortHelp = u'やり直し(Ctrl+y)'
            self.Bind(wx.EVT_TOOL, self.OnRedo, tb_redo)

        if self.dsp_save:
            tb_save = self.tb.AddLabelTool(ID_SAVE, 'Save',
                    wx.Bitmap('icon/save.png'))
            tb_save.ShortHelp = u'ポーズ情報の保存(Ctrl+s)'
            self.Bind(wx.EVT_TOOL, self.OnSave, tb_save)

        if self.dsp_insert:
            tb_insert = self.tb.AddLabelTool(ID_INSERT, 'Insert Label',
                    wx.Bitmap('icon/insert.png'))
            tb_insert.ShortHelp = u'ポーズの挿入(i)'
            self.Bind(wx.EVT_TOOL, self.OnInsert, tb_insert)

        if self.dsp_remove:
            tb_remove = self.tb.AddLabelTool(ID_REMOVE, 'Remove Label',
                    wx.Bitmap('icon/remove.png'))
            tb_remove.ShortHelp = u'ポーズの削除(Delete)'
            self.Bind(wx.EVT_TOOL, self.OnRemove, tb_remove)

        self.tb.Realize()

    def set_enable(self):
        if not self.dsp_toolbar:
            return

        if self.dsp_head:
            self.tb.EnableTool(ID_HEAD, self.view.can_head())
        if self.dsp_play:
            self.tb.EnableTool(ID_PLAY, self.view.can_play())
        if self.dsp_playpause:
            self.tb.EnableTool(ID_PLAYPAUSE, self.view.can_pause_mode_play())
        if self.dsp_playborder:
            self.tb.EnableTool(ID_PLAYBORDER, self.view.can_play_border())
        if self.dsp_pause:
            self.tb.EnableTool(ID_PAUSE, self.view.can_pause())
        if self.dsp_tail:
            self.tb.EnableTool(ID_TAIL, self.view.can_tail())
        if self.dsp_zoomin:
            self.tb.EnableTool(ID_ZOOMIN, self.view.can_zoomin())
        if self.dsp_zoomout:
            self.tb.EnableTool(ID_ZOOMOUT, self.view.can_zoomout())

        if self.dsp_cut:
            self.tb.EnableTool(ID_CUT, self.view.can_cut())
        if self.dsp_mergeleft:
            self.tb.EnableTool(ID_MERGE_L, self.view.can_merge_left())
        if self.dsp_mergeright:
            self.tb.EnableTool(ID_MERGE_R, self.view.can_merge_right())
        if self.dsp_undo:
            self.tb.EnableTool(ID_UNDO, self.view.can_undo())
        if self.dsp_redo:
            self.tb.EnableTool(ID_REDO, self.view.can_redo())
        if self.dsp_save:
            self.tb.EnableTool(ID_SAVE, self.view.can_save())
        if self.dsp_insert:
            self.tb.EnableTool(ID_INSERT, self.view.can_insert_label())
        if self.dsp_remove:
            self.tb.EnableTool(ID_REMOVE, self.view.can_remove_label())

        if self.dir_name and (not self.view.playing):
            self.fsp.Enable()
            self.ipp.Enable()
        else:
            self.fsp.Disable()
            self.ipp.Disable()

    def confirm_save(self):
        if self.view.can_save():
            dlg = wx.MessageDialog(self, u'変更を保存しますか？', u'確認',  wx.YES_NO)
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
            self.list_index = 0
            return

        labels_dir = os.path.join(dir_name, LABELS_DIR)
        if not os.path.exists(labels_dir):
            os.mkdir(labels_dir)

        wav_files.sort()

        for i, name in enumerate(wav_files):
            index = self.list.InsertStringItem(i, name)
            self.list.SetStringItem(index, 1, '%03d.txt' % (i + 1))

        self.list_index = max(0, min(self.list_index,
                                     self.list.ItemCount - 1))
        self.list.Select(self.list_index)
        wav_name = self.list.GetItem(self.list_index, 0).GetText()
        wav_file = os.path.join(self.dir_name,  wav_name)
        labels_name = self.list.GetItem(self.list_index, 1).GetText()
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
        self.list_index = evt.m_itemIndex

        self.set_sound(wav_file, labels_file)

    def OnDoubleClick(self, evt):
        evt.Veto()

    def set_sound(self, wav_file, labels_file):
        if not self.view.set_sound(wav_file):
            return

        if not os.path.exists(labels_file):
            labels = find_sound(wav_file, self.sil_lv, self.sil_dur,
                    self.label_before_dur, self.label_after_dur,
                    self.rate, self.snd_dur)
            labels.write(labels_file)

        self.view.set_labels(labels_file)
        self.view.sil_lv = self.sld_sil_lv.GetValue()

        wav_name = os.path.basename(wav_file)
        self.Title = wav_name

        self.set_enable()

    def OnFindSound(self, evt):
        sil_lv = self.sld_sil_lv.GetValue()
        sil_dur = self.nc_sil_dur.GetValue()

        self.view.find(sil_lv, sil_dur,
                self.label_before_dur, self.label_after_dur)

    def OnReverse(self, evt):
        not_found = False

        rev_dir = os.path.join(self.dir_name, REVERSE_DIR)
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
            wx.MessageBox(u'ここに手作業でつくったポーズ付きwavを入れて\n%s' %
                          rev_dir, u'やほ', wx.OK)
            return

        wav_files = []

        for i in range(self.list.ItemCount):
            wav_name = self.list.GetItem(i, 0).GetText()
            wav_file = os.path.join(self.dir_name, wav_name)
            wav_files.append(wav_file)

        if len(wav_files) != len(rev_names):
            wx.MessageBox(u'wavの数(%d)とreverseの数(%d)が違います' %
                          (len(wav_files), len(rev_names)), u'^^', wx.OK)
            return

        dlg = wx.MessageDialog(self, u'ポーズ情報が上書きされますが' +
                               u'よろしいでしょうか？', u'確認',  wx.YES_NO)
        response = dlg.ShowModal()
        dlg.Destroy()

        if response == wx.ID_NO:
            return

        dlg = wx.MessageDialog(self, u'すべてのファイルのポーズを探しますか？' +
                               u'\n「いいえ」なら表示されているファイルのみ',
                               u'何度も確認して申し訳ございません',  wx.YES_NO)
        response = dlg.ShowModal()
        dlg.Destroy()

        rev_files = []

        if response == wx.ID_NO:
            rev_name = rev_names[self.list_index]
            rev_file = os.path.join(self.dir_name, REVERSE_DIR, rev_name)
            rev_files.append(rev_file)
            wav_files = [wav_files[self.list_index]]
        else:
            for rev_name in rev_names:
                rev_file = os.path.join(self.dir_name, REVERSE_DIR, rev_name)
                rev_files.append(rev_file)

        dlg = wx.ProgressDialog(u'ポーズ情報作成',
                                u'ポーズ情報作成中\n残りファイル数%d' %
                                len(wav_files), maximum=len(wav_files),
                                parent=self,
                                style=wx.PD_AUTO_HIDE | wx.PD_APP_MODAL)

        error_files = []

        for i, (wav_file, rev_file) in \
                enumerate(zip(wav_files, rev_files)):
            dlg.Update(i + 1, u'ポーズ情報作成中\n残りファイル数%d' %
                       (len(wav_files) - i))

            try:
                result = rev_pause(wav_file, rev_file, self.rev_sil_lv,
                        self.rev_sil_dur, self.rev_rate,
                        self.label_before_dur, self.label_after_dur)
            except Exception as e:
                print e.message
                result = [[], True]
            labels, err = result
            labels_name = '%03d.txt' % (i + 1)
            labels_file = os.path.join(self.dir_name, LABELS_DIR, labels_name)
            labels.write(labels_file)

            if err:
                error_files.append(os.path.basename(wav_file))

        dlg.Destroy()

        if len(error_files) != 0:
            error_file = os.path.join(self.dir_name, ERROR_FILE)
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

        labels_file = self.list.GetItem(self.list_index, 1).GetText()
        labels_file = os.path.join(self.dir_name, LABELS_DIR, labels_file)
        self.view.set_labels(labels_file)

    def OnInsertPause(self, evt):
        if not self.confirm_save():
            wx.MessageBox(u'じゃあ、作ってやらん。', u'もう怒った', wx.OK)
            return

        pause_dir = os.path.join(self.dir_name, PAUSE_DIR)
        if not os.path.exists(pause_dir):
            os.mkdir(pause_dir)

        dlg = wx.MessageDialog(self, u'すべてのファイルにポーズをつけますか？' +
                               u'\n「いいえ」なら表示されているファイルのみ',
                               u'確認',  wx.YES_NO)
        response = dlg.ShowModal()
        dlg.Destroy()

        wav_names = []
        labels_names = []

        if response == wx.ID_NO:
            wav_names.append(self.list.GetItem(self.list_index, 0).GetText())
            labels_names.append(
                self.list.GetItem(self.list_index, 1).GetText())
        else:
            for i in range(self.list.ItemCount):
                wav_names.append(self.list.GetItem(i, 0).GetText())
                labels_names.append(self.list.GetItem(i, 1).GetText())

        dlg = wx.ProgressDialog(u'ポーズファイル作成',
                                u'ポーズファイル作成中\n残りファイル数%d' %
                                len(wav_names), maximum=len(wav_names),
                                parent=self,
                                style=wx.PD_AUTO_HIDE | wx.PD_APP_MODAL)

        for i, (wav, labels) in enumerate(zip(wav_names, labels_names)):
            dlg.Update(i, u'ポーズファイル作成中\n残りファイル数%d' %
                       (len(wav_names) - i))

            wav_file = os.path.join(self.dir_name, wav)
            labels_file = os.path.join(self.dir_name, LABELS_DIR, labels)
            pause_file = os.path.join(self.dir_name, PAUSE_DIR, wav)

            if not os.path.exists(labels_file):
                labels = find_sound(wav_file, self.sil_lv, self.sil_dur,
                    self.label_before_dur, self.label_after_dur,
                    self.rate, self.snd_dur)
                labels.write(labels_file)

            insert_pause(wav_file, pause_file, labels_file,
                         self.nc_factor.GetValue(), self.nc_add.GetValue())

        dlg.Destroy()

        pause_dir = os.path.join(self.dir_name, PAUSE_DIR)
        wx.MessageBox(u'このフォルダにできています\n%s' % pause_dir, u'完了', wx.OK)

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

        self.pm.SaveAndUnregister()

        self.Destroy()


class DirDrop(wx.FileDropTarget):
    def __init__(self, window):
        wx.FileDropTarget.__init__(self)
        self.window = window

    def OnDropFiles(self, x, y, names):
        if len(names) == 1:
            if os.path.isdir(names[0]):
                self.window.list_index = 0
                self.window.set_dir(names[0])
            else:
                self.window.list_index = 0
                self.window.set_dir(os.path.dirname(names[0]))


class MyConfigParser(SafeConfigParser):
    def myget(self, section, option, default):
        try:
            return SafeConfigParser.get(self, section, option)
        except (NoSectionError, NoOptionError):
            return default
        except Exception as e:
            print e.message
            return default

    def mygetint(self, section, option, default, min_v=None, max_v=None):
        try:
            result = SafeConfigParser.getint(self, section, option)
        except (NoSectionError, NoOptionError):
            return default
        except Exception as e:
            print e.message

            result = default

        if min_v is not None:
            result = max(min_v, result)

        if max_v is not None:
            result = min(max_v, result)

        return result

    def mygetfloat(self, section, option, default, min_v=None, max_v=None):
        try:
            result = SafeConfigParser.getfloat(self, section, option)
        except (NoSectionError, NoOptionError):
            return default
        except Exception as e:
            print e.message

            result = default

        if min_v is not None:
            result = max(min_v, result)

        if max_v is not None:
            result = min(max_v, result)

        return result

    def mygetboolean(self, section, option, default):
        try:
            return SafeConfigParser.getboolean(self, section, option)
        except (NoSectionError, NoOptionError):
            return default
        except Exception as e:
            print e.message

            return default


if __name__ == '__main__':
    main()
