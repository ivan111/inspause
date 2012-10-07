# -*- coding: utf-8 -*-

import audioop
import wave

from findsound import find_sound, rms_ratecv, MIN_DUR
from labels import Label, Labels

DEBUG = False

SIL_DUR = 0.7
SIL_LV = 15
RATE = 48
LABEL_BEFORE_DUR = 0.1
LABEL_AFTER_DUR = 0.1
WAV_SCALE = 10


def search_pattern(data, pattern):
    score_list = []
    for st in range(0, len(data) - len(pattern) + 1):
        score = 0
        for i, p in enumerate(pattern):
            score = score + abs(data[st + i] - p)
        score_list.append([st, score])

    return min(score_list, key=lambda x: x[1])


def rev_pause(normal, paused, kokubaru_mode=False):
    labels_p = find_sound(paused, SIL_LV, SIL_DUR, 0, 0, RATE)
    labels = Labels()

    if DEBUG:
        print labels_p

    data_n = get_data(normal)
    max_s = float(len(data_n)) / RATE
    data_p = get_data(paused)

    max_val = max(data_p) / WAV_SCALE
    thres = SIL_LV * max_val / 100

    for label in labels_p:
        st = int(label.start * RATE)
        ed = int(label.end * RATE)
        pattern = data_p[st: ed]
        score_l = search_pattern(data_n, pattern)
        start_f, score = score_l

        dur = label.end - label.start

        p_sil_s = get_sil_s(data_p, ed, thres)
        n_sil_s = get_sil_s(data_n, start_f + (ed - st) + 1, thres)
        sil_s = p_sil_s - n_sil_s

        if MIN_DUR <= sil_s:
            label_after_dur = min(LABEL_AFTER_DUR, n_sil_s)
            if kokubaru_mode:
                end = (float(start_f) / RATE) + (label.end - label.start)
                end = end + label_after_dur
                end = max(0, min(end, max_s))

                start = end - label_after_dur - sil_s - LABEL_BEFORE_DUR
                start = max(0, min(start, max_s))
            else:
                start = float(start_f) / RATE - LABEL_BEFORE_DUR
                start = max(0, min(start, max_s))
                end = start + (label.end - label.start) + \
                    LABEL_BEFORE_DUR + label_after_dur
                end = max(0, min(end, max_s))

            labels.append(Label(start, end))

            if DEBUG:
                score_p = float(score) / (ed - st)
                fmt = 'score: %4.0f, time: %6.2f - %6.2f, dur: %4.1f' + \
                    ', sil_p: %3.1f, sil_n: %3.1f'
                print fmt % (score_p, start, end, dur, p_sil_s, n_sil_s)

    if labels.is_sorted():
        err = False
    else:
        if DEBUG:
            print '[rev_pause] *** ERROR ***'
        err = True

    if not kokubaru_mode:
        labels.subtract()

    return (labels, err)


def get_data(name):
    wf = wave.open(name, 'r')
    buffer = wf.readframes(wf.getnframes())
    if wf.getnchannels() == 2:
        buffer = audioop.tomono(buffer, wf.getsampwidth(), 0.5, 0.5)
    data = rms_ratecv(buffer, 1, wf.getsampwidth(), wf.getframerate(), RATE)

    return data


def get_sil_s(data, start_f, thres):
    sil_c = 0
    for i in range(start_f, len(data)):
        if data[i] <= thres:
            sil_c = sil_c + 1
        else:
            break
    return float(sil_c) / RATE


if __name__ == '__main__':
    labels = rev_pause('n.wav', 'p.wav')[0]
    labels.write('labels.txt')
