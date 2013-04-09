# -*- coding: utf-8 -*-
'''
用意されたラベル情報
'''

from ConfigParser import SafeConfigParser
import cStringIO
import os
import zipfile

from labels import Labels
from mywave import is_near_distinction, NO_DISTINCTION
from myfile import get_labels_file_list, file_name_re, DIR_LABELS


DIR_AUTO  = 'auto'
INFO_FILE = 'info.txt'


class AutoLabels(object):
    def __init__(self):
        self.info_list = self._load()


    def _load(self):
        '''
        用意されたラベル情報を読み込む
        '''

        info_list = []

        try:
            for f in os.listdir(DIR_AUTO):
                path = os.path.join(DIR_AUTO, f)

                if os.path.isdir(path):
                    info = self.load_labels_info_from_dir(path)
                elif f.lower().endswith('.zip'):
                    info = self.load_labels_info_from_zip(path)
                else:
                    info = None

                if info:
                    if not info.name:
                        info.name = f

                    info_list.append(info)
        except Exception as e:
            print e.message

        return info_list


    def load_labels_info_from_dir(self, dir_name):
        labels_list = []
        name = None

        try:
            # ---- info.txt の読み込み

            info_file = os.path.join(dir_name, INFO_FILE)

            if os.path.exists(info_file):
                try:
                    f = open(info_file, 'r')
                    name = self.load_info_file(f)
                except Exception as e:
                    print e.message

            # ---- ラベルファイルの読み込み

            labels_files = get_labels_file_list(dir_name)

            for labels_file in labels_files:
                lines = open(labels_file, 'r').readlines()
                labels_list.append(Labels(lines))
        except Exception as e:
            print e.message

        info = None

        if labels_list:
            info = LabelsInfo(name, labels_list)

        return info


    def load_labels_info_from_zip(self, zip_path):
        labels_list = []
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
                    sf = cStringIO.StringIO(zf.read(f))
                    name = self.load_info_file(sf)
                    continue

                # ---- ラベルファイルの読み込み

                m = file_name_re.search(basename)

                if m and basename not in check_unique:
                    check_unique.add(basename)

                    sf = cStringIO.StringIO(zf.read(f))
                    lines = [line for line in sf]
                    labels_files.append([basename, Labels(lines)])

            labels_files.sort()  # basename でソート

            i = 0
            for labels_file, labels in labels_files:
                check_name = '%03d.txt' % (i + 1)

                if labels_file != check_name:
                    break

                labels_list.append(labels)

                i += 1
 
            zf.close()
        except Exception as e:
            print e.message

        info = None

        if labels_list:
            info = LabelsInfo(name, labels_list)

        return info


    def load_info_file(self, fp):
        name = None
        conf = SafeConfigParser()

        try:
            conf.readfp(fp)

            name = conf.get('info', 'name')
            name = name.decode('CP932')
        except Exception as e:
            print e.message

        return name


    def auto_detect(self, num_waves, distinction_s, index):
        '''
        使えそうなラベルはあるか？

        @param index 何番目の distinction_s か
        @return 使えそうなラベル情報のリスト
        '''

        result = []

        for info in self.info_list:
            if self.match_info(info, num_waves, distinction_s, index):
                result.append(info)

        return result


    def match_info(self, info, num_waves, distinction_s=NO_DISTINCTION, index=0, loose=False):
        '''
        この用意されたポーズ情報は使えるか？

        @param index 何番目の distinction_s か
        @param loose True なら音声ファイル数のみチェック
        '''

        if info.num_labels != num_waves:
            return False

        if loose:
            return True

        info_d = info.distinction_s(index)

        if info_d == NO_DISTINCTION or distinction_s == NO_DISTINCTION:
            pass
        elif not is_near_distinction(info_d, distinction_s):
            return False

        return True


    def setup_labels(self, dir_name, info):
        '''
        用意されたポーズ情報を配置する
        '''

        try:
            for i, labels in enumerate(info.labels_list):
                file_name = '%03d.txt' % (i + 1)
                labels_file = os.path.join(dir_name, file_name)

                labels.write(labels_file)
        except Exception as e:
            print e.message


    def create_labels_info(self, zip_path, name, labels_dir, labels_files):
        '''
        用意されたポーズの作成
        '''

        conf = SafeConfigParser()

        try:
            zf = zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED)

            # ---- info.txt の作成

            conf.add_section('info')
            conf.set('info', 'name', name.encode('CP932'))
            sf = cStringIO.StringIO()
            conf.write(sf)

            zf.writestr(os.path.join(DIR_LABELS, INFO_FILE), sf.getvalue())

            # ---- ラベルファイルの作成

            for labels_file in labels_files:
                zf.write(os.path.join(labels_dir, labels_file), os.path.join(DIR_LABELS, labels_file))

            zf.close()
        except Exception as e:
            print e.message


class LabelsInfo(object):
    '''
    １タイトルのラベル情報を表す
    '''

    def __init__(self, name, labels_list):
        self.name = name
        self.labels_list = labels_list
        self.num_labels = len(labels_list)


    def distinction_s(self, index):
        if 0 <= index < len(self.labels_list):
            return self.labels_list[index].distinction_s

        return NO_DISTINCTION

