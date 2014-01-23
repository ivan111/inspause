# -*- coding: utf-8 -*-

'''
ログの内容を、wxTextCtrlとログファイルに記録する
'''

import codecs
import os
import sys
import wx


class Mylog(object):
    '''
    ログの内容を、wxTextCtrlとログファイルに記録する
    '''

    def __init__(self, tc, log_path):
        if os.path.exists(log_path):
            f = self._open(log_path)
            tc.SetValue(f.read())
            f.close()

        tc.SetInsertionPointEnd()
        tc.ShowPosition(tc.GetInsertionPoint())
        self.tc = tc
        self.path = log_path
        self.f = self._open(log_path, 'a')

    def _open(self, path, mode='r'):
        if sys.platform == 'win32':
            f = codecs.open(path, mode, 'CP932')
        else:
            f = codecs.open(path, mode, 'utf8')

        return f

    def write(self, data):
        self.tc.WriteText(data)
        try:
            self.f.write(data)
            self.f.flush()
        except Exception as e:
            self.tc.WriteText('[WriteLogError] %s' % str(e))
        self.post_log_change_evt()

    def clear(self):
        self.tc.Clear()
        self.f.close()
        self.f = self._open(self.path, 'w')

    def post_log_change_evt(self):
        evt = LogChangeEvent(self.tc.GetId())
        self.tc.GetEventHandler().ProcessEvent(evt)


# ---- イベント
myEVT_LOG_CHANGE = wx.NewEventType()
EVT_LOG_CHANGE = wx.PyEventBinder(myEVT_LOG_CHANGE, 1)


class LogChangeEvent(wx.PyCommandEvent):
    def __init__(self, id):
        wx.PyCommandEvent.__init__(self, myEVT_LOG_CHANGE, id)
