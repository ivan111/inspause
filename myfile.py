# -*- coding: utf-8 -*-

'''
ファイル関連
'''

import os
import re
import shutil
import sys

import wx

from maplabels import Map_labels


# ファイル名
XRC_FILE = 'gui.xrc'  # GUI 設定ファイル
LOG_FILE = 'log.txt'
PERSIST_FILE = 'persist.txt'
MAP_FILE = 'map.txt'

# ディレクトリ
P_LABELS_DIR = 'labels'
PAUSE_DIR  = 'pause'
BACKUP_DIR = 'backup'

FILE_NAME_RE = re.compile(r'^(\d{3}\.txt)$')

app_data_dir = None
p_labels_dir = None
xrc_path = None
log_path = None
persist_path = None
map_path = None
sys_backup_dir = None
user_backup_dir = None

map_labels = None


#------------------------------------------------------------------------------
# 初期化

def init_dir(app_name):
    global xrc_path, log_path, persist_path, map_path, map_labels, sys_backup_dir

    init_app_data_dir(app_name)
    init_p_labels_dir()
    xrc_path = os.path.join('.', XRC_FILE)
    log_path = os.path.join(app_data_dir, LOG_FILE)
    persist_path = os.path.join(app_data_dir, PERSIST_FILE)
    map_path = os.path.join(p_labels_dir, MAP_FILE)
    sys_backup_dir = os.path.join('.', BACKUP_DIR)
    init_user_backup_dir()

    map_labels = Map_labels(map_path)


def init_app_data_dir(app_name):
    '''
    設定ファイルの保存場所を初期化
    なければ作成
    '''

    global app_data_dir

    app_data_dir = get_app_data_dir(app_name)


def get_my_documents():
    path = None

    try:
        from win32com.shell import shell, shellcon
        path = shell.SHGetFolderPath(0, shellcon.CSIDL_PERSONAL, None, 0)
    except:
        try:
            import ctypes
            from ctypes.wintypes import MAX_PATH

            dll = ctypes.windll.shell32
            buf = ctypes.create_unicode_buffer(MAX_PATH + 1)
            if dll.SHGetSpecialFolderPathW(None, buf, 0x0005, False):
                path = buf.value
        except:
            pass

    return path


def get_app_data_dir(app_name):
    if app_data_dir:
        return app_data_dir

    d = None

    if sys.platform == 'win32':
        my_doc_dir = get_my_documents()

        if my_doc_dir:
            d = os.path.join(my_doc_dir, app_name)
        else:
            d = os.path.expanduser(os.path.join('~', app_name))
    else:
        d = os.path.expanduser(os.path.join('~', '.' + app_name))

    if not os.path.exists(d):
        os.mkdir(d)

    return d


def init_p_labels_dir():
    '''
    ラベルファイルの保存場所を初期化
    なければ作成
    '''

    global p_labels_dir

    p_labels_dir = os.path.join(app_data_dir, P_LABELS_DIR)

    if not os.path.exists(p_labels_dir):
        os.mkdir(p_labels_dir)


def init_user_backup_dir():
    '''
    ユーザ用ポーズ情報ファイルの保存場所を初期化
    なければ作成
    '''

    global user_backup_dir

    user_backup_dir = os.path.join(app_data_dir, BACKUP_DIR)

    if not os.path.exists(user_backup_dir):
        os.mkdir(user_backup_dir)


#------------------------------------------------------------------------------

def store_map():
    if map_labels:
        map_labels.store()

# ---- 音声

def get_snd_files(snd_dir):
    '''
    音声ファイルの一覧を取得する
    '''

    from pausewave import extensions

    snd_files = []

    if not snd_dir or not os.path.exists(snd_dir):
        return snd_files

    for snd_file in os.listdir(snd_dir):
        if not os.path.isfile(os.path.join(snd_dir, snd_file)):
            continue

        ext = get_ext(snd_file)

        if ext in extensions:
            snd_files.append(snd_file)

    snd_files.sort()

    return snd_files

# ---- ラベル

def get_labels_dir(snd_dir):
    dir_name = map_labels.get_dir_name(snd_dir)
    if not dir_name:
        base_name = os.path.basename(snd_dir)
        old_snd_dir = map_labels.reverse_map(base_name)

        # 音声フォルダを移動したか確認
        if old_snd_dir and confirm_move_snd():
            map_labels.move_snd_dir(old_snd_dir, snd_dir)
            dir_name = base_name
        else:
            dir_name = map_labels.add_item(snd_dir)

    labels_dir = os.path.join(p_labels_dir, dir_name)

    if not os.path.exists(labels_dir):
        os.mkdir(labels_dir)

        copy_old_labels(snd_dir, labels_dir)

    return labels_dir


def confirm_move_snd():
    msg = u'もしかして音声フォルダを移動しましたか？'
    flg = wx.YES_NO | wx.ICON_QUESTION
    res = wx.MessageBox(msg, u'確認',  flg)

    if res == wx.YES:
        return True

    return False


def copy_old_labels(snd_dir, labels_dir):
    '''
    ver 2.10以前は、音声フォルダ以下にラベルフォルダを置いていた。
    もし音声フォルダにlabelsフォルダがあれば旧タイプで作ったファイルと
    みなして、新規ラベルフォルダにコピーする
    '''

    old_labels_dir = os.path.join(snd_dir, 'labels')
    if not os.path.exists(old_labels_dir):
        return

    try:
        for labels_file in os.listdir(old_labels_dir):
            old_labels_path = os.path.join(old_labels_dir, labels_file)
            if not os.path.isfile(old_labels_path):
                continue

            m = FILE_NAME_RE.search(labels_file)

            if m:
                new_labels_path = os.path.join(labels_dir, labels_file)
                shutil.copyfile(old_labels_path, new_labels_path)
    except:
        pass


def get_labels_file(index):
    return '%03d.txt' % index


def get_labels_path(snd_dir, index):
    labels_dir = get_labels_dir(snd_dir)
    labels_file = get_labels_file(index)
    return os.path.join(labels_dir, labels_file)


def get_labels_paths(snd_dir, is_sequential=True):
    '''
    ラベルファイルの一覧（ソート済み）を取得

    @param is_sequential Trueなら、001.txtからの連続したファイルのみ取得
                         Falseなら、すべてのファイルを取得
    '''

    labels_dir = get_labels_dir(snd_dir)

    labels_files = []

    for labels_file in os.listdir(labels_dir):
        if not os.path.isfile(os.path.join(labels_dir, labels_file)):
            continue

        m = FILE_NAME_RE.search(labels_file)

        if m:
            labels_files.append(labels_file)

    labels_files.sort()

    labels_paths = []

    for i, labels_file in enumerate(labels_files):
        if is_sequential:
            seq_file = '%03d.txt' % (i + 1)

            if labels_file != seq_file:
                break

        labels_path = os.path.join(labels_dir, labels_file)
        labels_paths.append(labels_path)

    return labels_paths


# ---- ポーズ音声

def get_default_pause_dir(snd_dir):
    return os.path.join(snd_dir, PAUSE_DIR)


#------------------------------------------------------------------------------
# 一般機能

def get_ext(name):
    '''
    拡張子を取得する。先頭のドットは含まない。
    '''

    root, ext = os.path.splitext(name)
    ext = ext.lower()

    if ext.startswith('.'):
        ext = ext[1:]

    return ext


def get_music_dir():
    '''
    ミュージックフォルダを取得する
    '''

    music_dir = ''

    if sys.platform == 'win32':
        try:
            import ctypes
            from ctypes.wintypes import MAX_PATH

            dll = ctypes.windll.shell32
            buf = ctypes.create_unicode_buffer(MAX_PATH + 1)

            if dll.SHGetSpecialFolderPathW(None, buf, 0x000d, False):  # MyMusic フォルダ
                music_dir = buf.value
        except:
            pass

    return music_dir

def exists(snd_dir, extensions):
    '''
    snd_dirフォルダにextensionsに含まれる拡張子のファイルが存在するか？
    '''

    snd_files = []

    if not snd_dir or not os.path.exists(snd_dir):
        return False

    for snd_file in os.listdir(snd_dir):
        if not os.path.isfile(os.path.join(snd_dir, snd_file)):
            continue

        ext = get_ext(snd_file)

        if ext in extensions:
            return True

    return False
