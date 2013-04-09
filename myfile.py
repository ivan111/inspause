# -*- coding: utf-8 -*-
'''
ファイル関連
'''

import os
import re

from mywave import extensions


# ディレクトリ
DIR_LABELS = 'labels'
DIR_PAUSE  = 'pause'


file_name_re = re.compile(r'^(\d{3}\.txt)$')


def get_wav_file_list(dir_name):
    '''
    音声ファイルの一覧を取得する
    '''

    wav_files = []

    if dir_name is None or not os.path.exists(dir_name):
        return wav_files

    for name in os.listdir(dir_name):
        if not os.path.isfile(os.path.join(dir_name, name)):
            continue

        ext = get_ext(name)

        if ext in extensions:
            wav_files.append(name)

    return wav_files


def get_labels_file_list(dir_name, is_all=True):
    '''
    ラベルファイルの一覧を取得する。ソート済み

    @param is_all ファイル名の数字が連続したすべてのファイルが必要か？
    '''

    labels_files = []

    if dir_name is None or not os.path.exists(dir_name):
        return labels_files

    name_list = []

    for name in os.listdir(dir_name):
        if not os.path.isfile(os.path.join(dir_name, name)):
            continue

        m = file_name_re.search(name)

        if m:
            name_list.append(name)

    name_list.sort()

    if is_all:
        for i, name in enumerate(name_list):
            check_name = '%03d.txt' % (i + 1)

            if name != check_name:
                break

            labels_file = os.path.join(dir_name, name)
            labels_files.append(labels_file)
    else:
        return name_list

    return labels_files


def get_ext(name):
    '''
    拡張子を取得する。先頭のドットは含まない。
    '''

    root, ext = os.path.splitext(name)
    ext = ext.lower()

    if ext.startswith('.'):
        ext = ext[1:]

    return ext


def get_sub_dir_d(dir_name, sub_dir_name):
    if not os.path.exists(dir_name):
        return None

    sub_dir = os.path.join(dir_name, sub_dir_name)

    if not os.path.exists(sub_dir):
        os.mkdir(sub_dir)

    return sub_dir


def get_sub_dir_f(wav_file, sub_dir_name):
    dir_name = os.path.dirname(wav_file)

    if dir_name == '':
        return None

    sub_dir = os.path.join(dir_name, sub_dir_name)

    if not os.path.exists(sub_dir):
        os.mkdir(sub_dir)

    return sub_dir



def get_labels_dir_d(wav_dir):
    return get_sub_dir_d(wav_dir, DIR_LABELS)


def get_labels_dir_f(wav_file):
    return get_sub_dir_f(wav_file, DIR_LABELS)


def get_labels_file_name(index):
    return '%03d.txt' % index


def get_labels_file_d(wav_dir, index):
    labels_dir = get_labels_dir_d(wav_dir)

    if labels_dir is None:
        return None

    file_name = get_labels_file_name(index)

    return os.path.join(labels_dir, file_name)


def get_labels_file_f(wav_file, index):
    labels_dir = get_labels_dir_f(wav_file)

    if labels_dir is None:
        return None

    file_name = get_labels_file_name(index)

    return os.path.join(labels_dir, file_name)


def get_pause_dir_d(wav_dir):
    return get_sub_dir_d(wav_dir, DIR_PAUSE)


def get_pause_dir_f(wav_file):
    return get_sub_dir_f(wav_file, DIR_PAUSE)


def get_pause_file(wav_file):
    pause_dir = get_pause_dir_f(wav_file)

    if pause_dir is None:
        return None

    dir_name, file_name = os.path.split(wav_file)

    return os.path.join(pause_dir, file_name)
