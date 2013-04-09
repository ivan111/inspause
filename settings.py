# -*- coding: utf-8 -*-

'''
設定関連
'''

import codecs
from ConfigParser import SafeConfigParser, NoSectionError, NoOptionError
import os
import sys

from mywave import SIL_LV, SIL_DUR_S, BEFORE_DUR_S, AFTER_DUR_S
from volumewindow import SCALE, MIN_SCALE, VIEW_FACTOR, MAX_VIEW_FACTOR


CONFIG_FILE = 'settings.ini'

# ---- pause
FACTOR = 1.0
ADD = 0.4

SIL_DUR_MIN_S = 0.01
SIL_DUR_MAX_S = 0.6
FACTOR_MIN = 0.0
FACTOR_MAX = 3.00
ADD_MIN = 0.0
ADD_MAX = 9.99


class Settings(dict):
    #--------------------------------------------------------------------------
    # 公開メソッド
    #--------------------------------------------------------------------------

    def read_conf(self):
        conf = MyConfigParser()

        try:
            if sys.platform == 'win32':
                f = codecs.open(CONFIG_FILE, 'r', 'CP932')
            else:
                f = codecs.open(CONFIG_FILE, 'r', 'utf8')

            conf.readfp(f)
        except IOError:
            pass

        self._load_dir(conf)
        self._load_find(conf)
        self._load_color(conf)
        self._load_pause(conf)
        self._load_view(conf)


    def write_conf(self):
        conf = SafeConfigParser()

        self._store_dir(conf)
        self._store_find(conf)
        self._store_color(conf)
        self._store_pause(conf)
        self._store_view(conf)

        f = open(CONFIG_FILE, 'w')
        conf.write(f)

    #--------------------------------------------------------------------------
    # 非公開メソッド
    #--------------------------------------------------------------------------

    #--------------------------------------------------------------------------
    # 読み込み関連

    def _load_dir(self, conf):
        self['dir_snd'] = conf.myget('dir', 'wav_dir', '')

        if os.path.exists(self['dir_snd']) is False:
            self['dir_snd'] = ''

        self['list_index'] = conf.mygetint('dir', 'index', 0)


    def _load_color(self, conf):
        self['bg_r'] = conf.mygetint('color', 'bg_r', 255, 0, 255)
        self['bg_g'] = conf.mygetint('color', 'bg_g', 255, 0, 255)
        self['bg_b'] = conf.mygetint('color', 'bg_b', 255, 0, 255)

        self['fg_r'] = conf.mygetint('color', 'fg_r', 64, 0, 255)
        self['fg_g'] = conf.mygetint('color', 'fg_g', 133, 0, 255)
        self['fg_b'] = conf.mygetint('color', 'fg_b', 255, 0, 255)


    def _load_find(self, conf):
        self['sil_lv']       = conf.mygetint  ('find', 'sil_lv',       SIL_LV, 0, 100)
        self['sil_dur_s']    = conf.mygetfloat('find', 'sil_dur_s',    SIL_DUR_S, SIL_DUR_MIN_S, SIL_DUR_MAX_S)
        self['before_dur_s'] = conf.mygetfloat('find', 'before_dur_s', BEFORE_DUR_S)
        self['after_dur_s']  = conf.mygetfloat('find', 'after_dur_s',  AFTER_DUR_S)


    def _load_pause(self, conf):
        self['factor'] = conf.mygetfloat('pause', 'factor', FACTOR, FACTOR_MIN, FACTOR_MAX)
        self['add']    = conf.mygetfloat('pause', 'add',    ADD, ADD_MIN, ADD_MAX)


    def _load_view(self, conf):
        self['scale']       = conf.mygetint('view', 'scale',       SCALE, MIN_SCALE, 100)
        self['view_factor'] = conf.mygetint('view', 'view_factor', VIEW_FACTOR, 0, MAX_VIEW_FACTOR)


    #--------------------------------------------------------------------------
    # 書き込み関連

    def _store_dir(self, conf):
        conf.add_section('dir')
        if self['dir_snd'] is None:
            self['dir_snd'] = ''
        if sys.platform == 'win32':
            conf.set('dir', 'wav_dir', self['dir_snd'].encode('CP932'))
        else:
            conf.set('dir', 'wav_dir', self['dir_snd'].encode('utf8'))

        conf.set('dir', 'index', str(self['list_index']))


    def _store_color(self, conf):
        conf.add_section('color')
        conf.set('color', 'bg_r', str(self['bg_r']))
        conf.set('color', 'bg_g', str(self['bg_g']))
        conf.set('color', 'bg_b', str(self['bg_b']))

        conf.set('color', 'fg_r', str(self['fg_r']))
        conf.set('color', 'fg_g', str(self['fg_g']))
        conf.set('color', 'fg_b', str(self['fg_b']))


    def _store_find(self, conf):
        conf.add_section('find')
        conf.set('find', 'sil_lv',       str(self['sil_lv']))
        conf.set('find', 'sil_dur_s',    str(self['sil_dur_s']))
        conf.set('find', 'before_dur_s', str(self['before_dur_s']))
        conf.set('find', 'after_dur_s',  str(self['after_dur_s']))


    def _store_pause(self, conf):
        conf.add_section('pause')
        conf.set('pause', 'factor', str(self['factor']))
        conf.set('pause', 'add',    str(self['add']))


    def _store_view(self, conf):
        conf.add_section('view')
        conf.set('view', 'scale',       str(self['scale']))
        conf.set('view', 'view_factor', str(self['view_factor']))


    def _to_onoff(self, val):
        if val:
            return "on"
        else:
            return "off"


class MyConfigParser(SafeConfigParser):
    '''
    最大値と最小値を設定できるように SafeConfigParser を拡張したクラス
    '''

    def myget(self, section, option, default):
        '''
        文字列取得
        '''

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


    def mygetbool(self, section, option, default):
        try:
            return SafeConfigParser.getboolean(self, section, option)
        except (NoSectionError, NoOptionError):
            return default
        except Exception as e:
            print e.message
            return default
