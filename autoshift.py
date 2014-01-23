# -*- coding: utf-8 -*-

import os

from findsnd import find_sound
from volume import Volume

from labels import Labels
import pausewave


NO_DISTINCTION = -1  # 特徴位置がない
MAX_DIFF = 0.2
MIN_DIFF = 0.0001
DISTINCTION_RATE = 384


def auto_shift(snd_path, labels_path):
    '''
    自動ずれ補正
    '''

    snd = pausewave.open(snd_path, 'rb')
    labels = Labels(labels_path)

    if labels.dist_s == NO_DISTINCTION:
        return

    d = find_dist_s(snd)
    auto_shift_s = auto_shift_diff_s(d, labels.dist_s)

    if auto_shift_s != 0:
        labels.dist_s = d
        labels.shift(auto_shift_s)
        labels.write(labels_path)
        base_name = os.path.basename(snd_path)
        print 'auto shift: %.6fs %s' % (auto_shift_s, base_name)


def find_dist_s(snd):
    '''
    特徴となる位置の最初の１つを返す。
    見つからなければ NO_DISTINCTION
    '''

    vol = Volume(snd, DISTINCTION_RATE)
    labels = find_sound(vol, 5, 0.3, 0, 0)

    if len(labels) == 1:
        avg0 = (labels[0].start_s + labels[0].end_s) / 2
        return avg0
    elif len(labels) > 1:
        avg0 = (labels[0].start_s + labels[0].end_s) / 2
        avg1 = (labels[1].start_s + labels[1].end_s) / 2
        avg  = (avg0 + avg1) / 2
        return avg
    else:
        return NO_DISTINCTION


def auto_shift_diff_s(dist_s, another_s):
    '''
    自動ずれ調整の調整秒数

    @return 自動ずれ調整できなければ 0
    '''

    if dist_s == NO_DISTINCTION or another_s == NO_DISTINCTION:
        return 0

    diff_s = dist_s - another_s

    if MIN_DIFF < abs(diff_s) < MAX_DIFF:
        return diff_s

    return 0
