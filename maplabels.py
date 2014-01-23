# -*- coding: utf-8 -*-

'''
音声ディレクトリとラベルディレクトリの対応をとる
'''

import codecs
from ConfigParser import SafeConfigParser, NoSectionError, NoOptionError
import os
import sys


KEY_SND_DIR = 'snd_dir'
KEY_DIR_NAME = 'dir_name'


class Map_labels(dict):

    def __init__(self, map_path):
        conf = SafeConfigParser()

        try:
            if sys.platform == 'win32':
                f = codecs.open(map_path, 'r', 'CP932')
            else:
                f = codecs.open(map_path, 'r', 'utf8')

            conf.readfp(f)
        except IOError:
            pass

        self.map_path = map_path

        self._load(conf)

    def store(self):
        conf = SafeConfigParser()

        self._store(conf)

        f = open(self.map_path, 'w')
        conf.write(f)

    def add_item(self, snd_dir, dir_name=None):
        if self.has_key(snd_dir):
            return dir_name

        if not dir_name:
            dir_name = self._get_uniq_dir_name(snd_dir)

        self[snd_dir] = dir_name

        return dir_name

    def _get_uniq_dir_name(self, snd_dir):
        base_name = os.path.basename(snd_dir)
        name = base_name
        i = 0

        while True:
            for snd_dir, dir_name in self.iteritems():
                if name == dir_name:
                    i += 1
                    name = '%s_%d' % (base_name, i)
                    continue

            return name

    def get_dir_name(self, snd_dir):
        if self.has_key(snd_dir):
            return self[snd_dir]
        else:
            return ''

    def reverse_map(self, name):
        for snd_dir, dir_name in self.iteritems():
            if name == dir_name:
                return snd_dir

        return ''

    def move_snd_dir(self, src, dst):
        if not self.has_key(src) or self.has_key(dst):
            return

        dir_name = self[src]
        del self[src]
        self[dst] = dir_name

    def _load(self, conf):
        for section in conf.sections():
            snd_dir = self._load_str(conf, section, KEY_SND_DIR, '')
            dir_name = self._load_str(conf, section, KEY_DIR_NAME, '')
            self.add_item(snd_dir, dir_name)

    def _store(self, conf):
        for i, (snd_dir, dir_name) in enumerate(self.iteritems()):
            section = '%03d' % (i+1)
            conf.add_section(section)
            self._store_str(conf, section, KEY_SND_DIR, snd_dir)
            self._store_str(conf, section, KEY_DIR_NAME, dir_name)

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
