#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

import pausewave
from labels import Label, Labels
from volume import Volume


SIL_LV = 5  # 無音認識レベル(%)。低いほど無音判定がきびしくなる
SIL_DUR_S = 0.3  # この秒数だけ無音が続くと無音と判定
SND_DUR_S = 0.2  # この秒数だけ音が続くと音があると判定
BEFORE_DUR_S = 0.2  # ラベルの前に余裕をもたせる秒数
AFTER_DUR_S = 0.2  # ラベルの後に余裕をもたせる秒数
FIND_RATE = 384


def usage(app):
    sys.stderr.write('Usage: %s sound [labels]\n' % app)


def main():
    argc = len(sys.argv)
    if argc < 2 or argc > 3:
        usage(sys.argv[0])
        sys.exit(1)

    src_file = sys.argv[1]
    if argc == 2:
        labels_file = None
    else:
        labels_file = sys.argv[2]

    snd = pausewave.open(src_file, 'r')
    vol = Volume(snd, FIND_RATE)
    labels = find_sound(vol)

    if labels_file:
        labels.write(labels_file)
    else:
        print labels


def find_sound(vol, sil_lv=SIL_LV, sil_dur_s=SIL_DUR_S,
               before_dur_s=BEFORE_DUR_S, after_dur_s=AFTER_DUR_S):
    '''
    音がある部分にポーズラベルをつける

    based on the Sound Finder Audacity script
    by Jeremy R. Brown
    Sound Finder based on the Silence Finder Audacity script
    by Alex S. Brown

    @param sil_lv 無音認識レベル(%)。最大音に対して何％以下を無音と判定するか
    @param sil_dur_s 無音認識時間（秒）
    @param before_dur_s ラベルの前に余裕をもたせる秒数
    @param after_dur_s ラベルの後に余裕をもたせる秒数

    @return ラベル
    '''

    dur_s = vol.dur_s

    sil_lv = max(0, min(sil_lv, 100))

    max_val = max(vol)
    thres = sil_lv * max_val / 100  # 無音判定レベル
    sil_f = sil_dur_s * vol.rate  # 無音判定フレーム数
    snd_f = SND_DUR_S * vol.rate  # 音あり判定フレーム数
    sil_c = 0  # 無音カウンタ
    snd_c = 0  # 音ありカウンタ
    sil_start = -1  # 無音開始位置
    snd_start = -1  # 音あり開始位置
    is_first_snd = True  # 音が見つかった最初の時のみTrue
    labels = Labels()

    for n, v in enumerate(vol):
        if v <= thres:  # 無音
            sil_c = sil_c + 1
            if sil_start == -1:
                sil_start = n
            elif (not is_first_snd) and (snd_start != -1) and \
                    (sil_c > sil_f) and (snd_c > snd_f):

                max_f = sil_start + int(after_dur_s * vol.rate)
                sil_f = _get_sil_f(vol, sil_start, thres, max_f)
                start_time = (float(snd_start) / vol.rate) - before_dur_s
                start_time = max(0, min(start_time, dur_s))
                end_time = float(sil_start + sil_f) / vol.rate
                end_time = max(0, min(end_time, dur_s))

                try:
                    labels.append(Label(start_time, end_time))
                except Exception as e:
                    print str(e)

                is_first_snd = True
                sil_c = 0
                snd_c = 0
                sil_start = -1
        else:  # 音あり
            snd_c = snd_c + 1
            if is_first_snd:
                is_first_snd = False
                snd_start = n
            sil_c = 0
            sil_start = -1

    if not is_first_snd:
        start_time = float(snd_start) / vol.rate - before_dur_s
        start_time = max(0, min(start_time, dur_s))
        end_time = float(sil_start) / vol.rate + after_dur_s
        end_time = max(0, min(end_time, dur_s))

        if end_time < start_time:
            end_time = dur_s

        try:
            labels.append(Label(start_time, end_time))
        except Exception as e:
            print str(e)

    labels.subtract()

    return labels


def _get_sil_f(data, start_f, thres, max_f=None):
    if (max_f is None) or (len(data) < max_f):
        max_f = len(data)

    sil_c = 0
    for i in range(start_f, max_f):
        if data[i] <= thres:
            sil_c = sil_c + 1
        else:
            break

    return sil_c


if __name__ == '__main__':
    main()
