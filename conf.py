# -*- coding: utf-8 -*-

'''
設定
'''

import codecs
from ConfigParser import SafeConfigParser, NoSectionError, NoOptionError
import os
import sys

import wx

from findsnd import SIL_LV, SIL_DUR_S, BEFORE_DUR_S, AFTER_DUR_S
from insp import FACTOR, MIN_FACTOR, MAX_FACTOR, ADD_S, MIN_ADD_S, MAX_ADD_S
from labelswindow import (BG_COLOUR, FG_COLOUR, HANDLE_COLOUR,
        MIN_SCALE, MAX_VIEW_FACTOR)


CONFIG_FILE = 'conf.ini'

# ---- pause
MIN_SIL_DUR_S = 0.01
MAX_SIL_DUR_S = 0.99

# ---- 型
T_INT    = 'int'
T_FLOAT  = 'float'
T_BOOL   = 'bool'
T_STR    = 'str'
T_PATH   = 'path'
T_COLOUR = 'colour'

# 設定項目
# 形式：
# [セクション,
#     [項目名, 型, デフォルト値, 範囲?]*
# ]*
conf_data = [
['dir', [
    ['snd_dir',    T_PATH, '', None],
    ['list_index', T_INT,  0,  None],
]],
[T_COLOUR, [
    ['bg',     T_COLOUR, BG_COLOUR,     None],
    ['fg',     T_COLOUR, FG_COLOUR,     None],
    ['handle', T_COLOUR, HANDLE_COLOUR, None],
]],
['find', [
    ['sil_lv',       T_INT,   SIL_LV,       (0, 100)],
    ['sil_dur_s',    T_FLOAT, SIL_DUR_S,    (MIN_SIL_DUR_S, MAX_SIL_DUR_S)],
    ['before_dur_s', T_FLOAT, BEFORE_DUR_S, (0.0, 9.99)],
    ['after_dur_s',  T_FLOAT, AFTER_DUR_S,  (0.0, 9.99)],
]],
['pause', [
    ['factor', T_FLOAT, FACTOR, (MIN_FACTOR, MAX_FACTOR)],
    ['add_s',  T_FLOAT, ADD_S,  (MIN_ADD_S, MAX_ADD_S)],
]],
['view', [
    ['show_save2',    T_BOOL, True,  None],
    ['scale',         T_INT,  100,   (MIN_SCALE, 100)],
    ['view_factor',   T_INT,  2,     (1, MAX_VIEW_FACTOR)],
    ['show_log',      T_BOOL, False, None],
    ['auto_show_log', T_BOOL, True,  None],
    ['flist_width',   T_INT,  200,   (50, 400)],
]],
]


class Config(dict):
    '''
    設定

    ＜使用例＞
    conf = Config(app_data_dir)
    print conf.snd_dir
    '''

    def __init__(self, app_data_dir):
        conf = SafeConfigParser()

        try:
            path = os.path.join(app_data_dir, CONFIG_FILE)
            if sys.platform == 'win32':
                f = codecs.open(path, 'r', 'CP932')
            else:
                f = codecs.open(path, 'r', 'utf8')

            conf.readfp(f)
        except IOError:
            pass

        self.conf_path = path

        self._load(conf)

    def store(self):
        conf = SafeConfigParser()

        self._store(conf)

        f = open(self.conf_path, 'w')
        conf.write(f)

    # d['name']の取得を、d.nameでできるようにする
    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, val):
        if name in self:
            self[name] = val
        else:
            dict.__setattr__(self, name, val)

    def _load(self, conf):
        for section, options in conf_data:
            for option in options:
                name, typ, default, rng = option

                if typ == T_INT:
                    val = self._load_int(conf, section, name, default, rng)
                elif typ == T_FLOAT:
                    val = self._load_float(conf, section, name, default, rng)
                elif typ == T_BOOL:
                    val = self._load_bool(conf, section, name, default)
                elif typ == T_STR:
                    val = self._load_str(conf, section, name, default)
                elif typ == T_PATH:
                    val = self._load_path(conf, section, name, default)
                elif typ == T_COLOUR:
                    val = self._load_colour(conf, section, name, default)

                self[name] = val

    def _store(self, conf):
        for section, options in conf_data:
            if not conf.has_section(section):
                conf.add_section(section)

            for option in options:
                name, typ, default, rng = option

                val = self[name]

                if typ == T_INT:
                    self._store_int(conf, section, name, val)
                elif typ == T_FLOAT:
                    self._store_float(conf, section, name, val)
                elif typ == T_BOOL:
                    self._store_bool(conf, section, name, val)
                elif typ == T_STR:
                    self._store_str(conf, section, name, val)
                elif typ == T_PATH:
                    self._store_path(conf, section, name, val)
                elif typ == T_COLOUR:
                    self._store_colour(conf, section, name, val)

    # ---- int

    def _load_int(self, conf, section, name, default, rng):
        val = default

        try:
            val = conf.getint(section, name)
        except (NoSectionError, NoOptionError):
            pass
        except Exception as e:
            print str(e)

        if rng:
            val = max(rng[0], min(val, rng[1]))

        return val

    def _store_int(self, conf, section, name, val):
        conf.set(section, name, str(val))

    # ---- float

    def _load_float(self, conf, section, name, default, rng):
        val = default

        try:
            val = conf.getfloat(section, name)
        except (NoSectionError, NoOptionError):
            pass
        except Exception as e:
            print str(e)

        if rng:
            val = max(rng[0], min(val, rng[1]))

        return val

    def _store_float(self, conf, section, name, val):
        conf.set(section, name, str(val))

    # ---- bool

    def _store_bool(self, conf, section, name, val):
        conf.set(section, name, str(val))

    def _load_bool(self, conf, section, name, default):
        val = default

        try:
            val = conf.getboolean(section, name)
        except (NoSectionError, NoOptionError):
            pass
        except Exception as e:
            print str(e)

        return val

    # ---- str

    def _load_str(self, conf, section, name, default):
        val = default

        try:
            val = conf.get(section, name)
        except (NoSectionError, NoOptionError):
            pass
        except Exception as e:
            print str(e)

        return val

    def _store_str(self, conf, section, name, val):
        if sys.platform == 'win32':
            val = val.encode('CP932')
        else:
            val = val.encode('utf8')

        conf.set(section, name, val)

    # ---- path

    def _load_path(self, conf, section, name, default):
        val = default

        try:
            val = conf.get(section, name)
        except (NoSectionError, NoOptionError):
            pass
        except Exception as e:
            print str(e)

        if not os.path.exists(val):
            val = ''

        return val

    def _store_path(self, conf, section, name, val):
        self._store_str(conf, section, name, val)

    # ---- colour

    def _load_colour(self, conf, section, name, default):
        colour = wx.Colour()
        colour.Set(default)

        try:
            val = conf.get(section, name)
            colour.Set(val)
        except (NoSectionError, NoOptionError):
            pass
        except Exception as e:
            print str(e)

        return colour

    def _store_colour(self, conf, section, name, val):
        conf.set(section, name, val.GetAsString(wx.C2S_HTML_SYNTAX))
