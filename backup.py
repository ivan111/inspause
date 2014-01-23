# -*- coding: utf-8 -*-

'''
ラベル情報バックアップ
'''

from ConfigParser import SafeConfigParser
from cStringIO import StringIO
from datetime import datetime as dt
import os
import zipfile

from labels import Labels
import myfile as mf


INFO_FILE = 'info.txt'


class Backup(list):

    def __init__(self):
        self._load(mf.user_backup_dir, False)
        self._load(mf.sys_backup_dir, True)

    def backup(self, snd_dir, prefix=''):
        '''
        バックアップの作成

        @param prefix 保存名の頭につける文字列
        '''

        try:
            zip_path, name = self._get_backup_path(snd_dir, prefix)
            zf = zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED)

            # ---- info.txt の作成
            conf = SafeConfigParser()
            conf.add_section('info')
            conf.set('info', 'name', name.encode('CP932'))
            sf = StringIO()
            conf.write(sf)

            LABELS_DIR = 'labels'
            info_path = os.path.join(LABELS_DIR, INFO_FILE)
            zf.writestr(info_path, sf.getvalue())

            labels_paths = mf.get_labels_paths(snd_dir, False)
            snd_files = mf.get_snd_files(snd_dir)
            num_snds = len(snd_files)
            max_labels_file = mf.get_labels_file(num_snds)

            # ---- ラベルファイルの作成
            for labels_path in labels_paths:
                labels_file = os.path.basename(labels_path)
                if labels_file > max_labels_file:
                    break

                dst = os.path.join(LABELS_DIR, labels_file)
                zf.write(labels_path, dst)

            zf.close()
        except Exception as e:
            print str(e)
            return None

        info = self._load_labels_info_from_zip(zip_path)
        self.append(info)
        return info

    def restore(self, snd_dir, info):
        '''
        バックアップの復元
        '''

        try:
            labels_dir = mf.get_labels_dir(snd_dir)
            self._remove_all_files(labels_dir)

            snd_files = mf.get_snd_files(snd_dir)
            num_snds = len(snd_files)

            max_labels_file = mf.get_labels_file(num_snds)

            for i, (labels_file, labels) in enumerate(info.labels_list):
                if labels_file <= max_labels_file:
                    labels_path = os.path.join(labels_dir, labels_file)
                    labels.write(labels_path)
        except Exception as e:
            print str(e)

    def _remove_all_files(self, labels_dir):
        for labels_file in os.listdir(labels_dir):
            m = mf.FILE_NAME_RE.search(labels_file)

            if m:
                labels_path = os.path.join(labels_dir, labels_file)
                try:
                    os.remove(labels_path)
                except:
                    pass

    def delete(self, info):
        '''
        バックアップを削除
        '''

        if info.is_sys:
            return False

        if info not in self:
            return False

        if os.path.exists(info.path):
            try:
                os.remove(info.path)
            except:
                pass

        self.remove(info)

        return True

    def _get_backup_path(self, snd_dir, prefix=''):
        '''
        バックアップパスとバックアップ名のタプルを返す
        '''

        now_str = dt.now().strftime('%y-%m-%d_%H-%M-%S')
        base_name = os.path.basename(snd_dir)
        name = '%s_%s%s' % (now_str, prefix, base_name)
        return os.path.join(mf.user_backup_dir, name + '.zip'), name

    def _load(self, backup_dir, is_sys):
        '''
        バックアップを読み込む
        '''

        try:
            for f in os.listdir(backup_dir):
                path = os.path.join(backup_dir, f)

                if f.lower().endswith('.zip'):
                    info = self._load_labels_info_from_zip(path)
                else:
                    info = None

                if info:
                    if not info.name:
                        info.name = f

                    info.is_sys = is_sys

                    self.append(info)
        except Exception as e:
            print str(e)

    def _load_labels_info_from_zip(self, zip_path):
        name = None

        try:
            zf = zipfile.ZipFile(zip_path, 'r')

            check_unique = set()
            labels_files = []

            for f in zf.namelist():
                basename = os.path.basename(f)

                if not basename:  # ディレクトリは無視
                    continue

                # ---- info.txt の読み込み

                if basename == INFO_FILE and not name:
                    sf = StringIO(zf.read(f))
                    name = self._load_info_file(sf)
                    continue

                # ---- ラベルファイルの読み込み

                m = mf.FILE_NAME_RE.search(basename)

                if m and basename not in check_unique:
                    check_unique.add(basename)

                    sf = StringIO(zf.read(f))
                    lines = [line for line in sf]
                    labels_files.append([basename, Labels(lines)])

            zf.close()
        except Exception as e:
            print str(e)

        info = None

        if labels_files:
            info = LabelsInfo(name, labels_files, zip_path)

        return info

    def _load_info_file(self, fp):
        name = None
        conf = SafeConfigParser()

        try:
            conf.readfp(fp)

            name = conf.get('info', 'name')
            name = name.decode('CP932')
        except Exception as e:
            print str(e)

        return name


class LabelsInfo(object):
    '''
    １タイトルのラベル情報を表す
    '''

    def __init__(self, name, labels_list, path):
        '''
        @param labels_list [labels_file, labels]
        '''

        self.name = name
        self.labels_list = labels_list
        self.num_labels = len(labels_list)
        self.path = path
        self.is_sys = False
