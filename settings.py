import codecs
from ConfigParser import SafeConfigParser, NoSectionError, NoOptionError
import os
import sys

import findsound
from findsound import SIL_LV, SIL_DUR, RATE, SND_DUR
from findsound import LABEL_BEFORE_DUR, LABEL_AFTER_DUR, WAV_SCALE
from insertpause import FACTOR, ADD
import labels
from labels import MIN_DUR as LBL_MIN_DUR
import revpause
from revpause import SIL_LV as REV_SIL_LV, SIL_DUR as REV_SIL_DUR
from revpause import RATE as REV_RATE, TOLERABLE_SCORE
from revpause import WAV_SCALE as REV_WAV_SCALE
import waveview
from waveview import SEEK, SEEK_CTRL, SEEK_SHIFT, RATE as WV_RATE
from waveview import MIN_RATE as WV_MIN_RATE, MAX_RATE as WV_MAX_RATE

CONFIG_FILE = 'settings.ini'

SIL_DUR_MIN = 0.01
SIL_DUR_MAX = 9.99
FACTOR_MIN = 0.0
FACTOR_MAX = 9.99
ADD_MIN = 0.0
ADD_MAX = 9.99


class Settings(dict):
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

        self['debug'] = conf.mygetboolean('DEFAULT', 'debug', False)

        self['dir_name'] = conf.myget('dir', 'wav', '')
        if os.path.exists(self['dir_name']) == False:
            self['dir_name'] = ''

        self['list_index'] = conf.mygetint('dir', 'index', 0)

        self['lbl_min_dur'] = conf.mygetfloat('label', 'min_dur', LBL_MIN_DUR)
        labels.MIN_DUR = self['lbl_min_dur']

        self['sil_lv'] = conf.mygetint('find', 'sil_lv', SIL_LV, 0, 100)
        self['sil_dur'] = conf.mygetfloat('find', 'sil_dur', SIL_DUR,
            SIL_DUR_MIN, SIL_DUR_MAX)
        self['label_before_dur'] = conf.mygetfloat('find', 'label_before_dur',
            LABEL_BEFORE_DUR)
        self['label_after_dur'] = conf.mygetfloat('find', 'label_after_dur',
            LABEL_AFTER_DUR)
        self['rate'] = conf.mygetint('find', 'rate', RATE)
        self['snd_dur'] = conf.mygetfloat('find', 'snd_dur', SND_DUR)

        self['factor'] = conf.mygetfloat('pause', 'factor', FACTOR,
            FACTOR_MIN, FACTOR_MAX)
        self['add'] = conf.mygetfloat('pause', 'add', ADD, ADD_MIN, ADD_MAX)

        self['seek'] = conf.mygetint('view', 'seek', SEEK)
        waveview.SEEK = self['seek']
        self['seek_ctrl'] = conf.mygetint('view', 'seek_ctrl', SEEK_CTRL)
        waveview.SEEK_CTRL = self['seek_ctrl']
        self['seek_shift'] = conf.mygetint('view', 'seek_shift', SEEK_SHIFT)
        waveview.SEEK_SHIFT = self['seek_shift']
        self['wv_rate'] = conf.mygetint('view', 'default_rate', WV_RATE)
        waveview.RATE = self['wv_rate']
        self['wv_min_rate'] = conf.mygetint('view', 'min_rate', WV_MIN_RATE)
        waveview.MIN_RATE = self['wv_min_rate']
        self['wv_max_rate'] = conf.mygetint('view', 'max_rate', WV_MAX_RATE)
        waveview.MAX_RATE = self['wv_max_rate']
        self['wav_scale'] = conf.mygetint('view', 'wav_scale', WAV_SCALE, 1, 100)
        findsound.WAV_SCALE = self['wav_scale']
        waveview.WAV_SCALE = self['wav_scale']

        self['rev_sil_lv'] = conf.mygetint('reverse', 'sil_lv', REV_SIL_LV)
        self['rev_sil_dur'] = conf.mygetfloat('reverse', 'sil_dur', REV_SIL_DUR)
        self['rev_rate'] = conf.mygetint('reverse', 'rate', REV_RATE)
        self['tolerable_score'] = conf.mygetint('reverse', 'tolerable_score',
                TOLERABLE_SCORE)
        revpause.TOLERABLE_SCORE = self['tolerable_score']
        self['rev_wav_scale'] = conf.mygetint('reverse', 'wav_scale',
                REV_WAV_SCALE, 1, 100)
        revpause.WAV_SCALE = self['rev_wav_scale']
        self['rev_spec'] = conf.mygetboolean('reverse', 'spec', True)

        self['dsp_toolbar'] = conf.mygetboolean('button', 'toolbar', True)
        self['dsp_head'] = conf.mygetboolean('button', 'head', True)
        self['dsp_play'] = conf.mygetboolean('button', 'play', True)
        self['dsp_playpause'] = conf.mygetboolean('button', 'pause_mode_play',
                True)
        self['dsp_playborder'] = conf.mygetboolean('button', 'play_near_cursor',
                True)
        self['dsp_pause'] = conf.mygetboolean('button', 'pause', True)
        self['dsp_tail'] = conf.mygetboolean('button', 'tail', True)
        self['dsp_zoomin'] = conf.mygetboolean('button', 'zoomin', True)
        self['dsp_zoomout'] = conf.mygetboolean('button', 'zoomout', True)
        self['dsp_cut'] = conf.mygetboolean('button', 'cut', True)
        self['dsp_mergeleft'] = conf.mygetboolean('button', 'merge_left', True)
        self['dsp_mergeright'] = conf.mygetboolean('button', 'merge_right', True)
        self['dsp_undo'] = conf.mygetboolean('button', 'undo', True)
        self['dsp_redo'] = conf.mygetboolean('button', 'redo', True)
        self['dsp_save'] = conf.mygetboolean('button', 'save', True)
        self['dsp_insert'] = conf.mygetboolean('button', 'insert', True)
        self['dsp_remove'] = conf.mygetboolean('button', 'remove', True)

    def write_conf(self):
        conf = SafeConfigParser()

        conf.set('DEFAULT', 'debug', self.to_onoff(self['debug']))

        conf.add_section('dir')
        if self['dir_name'] is None:
            self['dir_name'] = ''
        if sys.platform == 'win32':
            conf.set('dir', 'wav', self['dir_name'].encode('CP932'))
        else:
            conf.set('dir', 'wav', self['dir_name'].encode('utf8'))

        conf.set('dir', 'index', str(self['list_index']))

        conf.add_section('label')
        conf.set('label', 'min_dur', str(self['lbl_min_dur']))

        conf.add_section('find')
        conf.set('find', 'sil_lv', str(self['sil_lv']))
        conf.set('find', 'sil_dur', str(self['sil_dur']))
        conf.set('find', 'label_before_dur', str(self['label_before_dur']))
        conf.set('find', 'label_after_dur', str(self['label_after_dur']))
        conf.set('find', 'rate', str(self['rate']))
        conf.set('find', 'snd_dur', str(self['snd_dur']))

        conf.add_section('pause')
        conf.set('pause', 'factor', str(self['factor']))
        conf.set('pause', 'add', str(self['add']))

        conf.add_section('view')
        conf.set('view', 'seek', str(self['seek']))
        conf.set('view', 'seek_ctrl', str(self['seek_ctrl']))
        conf.set('view', 'seek_shift', str(self['seek_shift']))
        conf.set('view', 'default_rate', str(self['wv_rate']))
        conf.set('view', 'min_rate', str(self['wv_min_rate']))
        conf.set('view', 'max_rate', str(self['wv_max_rate']))
        conf.set('view', 'wav_scale', str(self['wav_scale']))

        conf.add_section('reverse')
        conf.set('reverse', 'sil_lv', str(self['rev_sil_lv']))
        conf.set('reverse', 'sil_dur', str(self['rev_sil_dur']))
        conf.set('reverse', 'rate', str(self['rev_rate']))
        conf.set('reverse', 'tolerable_score', str(self['tolerable_score']))
        conf.set('reverse', 'wav_scale', str(self['rev_wav_scale']))
        conf.set('reverse', 'spec', self.to_onoff(self['rev_spec']))

        conf.add_section('button')
        conf.set('button', 'toolbar', self.to_onoff(self['dsp_toolbar']))
        conf.set('button', 'head', self.to_onoff(self['dsp_head']))
        conf.set('button', 'play', self.to_onoff(self['dsp_play']))
        conf.set('button', 'pause_mode_play',
                self.to_onoff(self['dsp_playpause']))
        conf.set('button', 'play_near_cursor',
                self.to_onoff(self['dsp_playborder']))
        conf.set('button', 'pause', self.to_onoff(self['dsp_pause']))
        conf.set('button', 'tail', self.to_onoff(self['dsp_tail']))
        conf.set('button', 'zoomin', self.to_onoff(self['dsp_zoomin']))
        conf.set('button', 'zoomout', self.to_onoff(self['dsp_zoomout']))
        conf.set('button', 'cut', self.to_onoff(self['dsp_cut']))
        conf.set('button', 'merge_left', self.to_onoff(self['dsp_mergeleft']))
        conf.set('button', 'merge_right', self.to_onoff(self['dsp_mergeright']))
        conf.set('button', 'undo', self.to_onoff(self['dsp_undo']))
        conf.set('button', 'redo', self.to_onoff(self['dsp_redo']))
        conf.set('button', 'save', self.to_onoff(self['dsp_save']))
        conf.set('button', 'insert', self.to_onoff(self['dsp_insert']))
        conf.set('button', 'remove', self.to_onoff(self['dsp_remove']))

        f = open(CONFIG_FILE, 'w')
        conf.write(f)

    def to_onoff(self, val):
        if val:
            return "on"
        else:
            return "off"


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
