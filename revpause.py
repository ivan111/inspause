# -*- coding: utf-8 -*-

import audioop
import wave

from findsound import find_sound, rms_ratecv, get_sil_f
from findsound import SND_DUR, LABEL_BEFORE_DUR, LABEL_AFTER_DUR
from labels import Label, Labels
import mp3

DEBUG = False

SIL_LV = 15
SIL_DUR = 0.7
RATE = 48
WAV_SCALE = 10
TOLERABLE_SCORE = RATE * 50
OK_SCORE = RATE * 5


def rev_pause(normal, paused, sil_lv=SIL_LV, sil_dur=SIL_DUR, rate=RATE,
        label_before_dur=LABEL_BEFORE_DUR,
        label_after_dur=LABEL_AFTER_DUR, fit_mode=True):

    if DEBUG:
        print
        print '[rev_pause]'
        print 'SIL_LV:', sil_lv
        print 'SIL_DUR:', sil_dur
        print 'RATE:', rate

    labels_p = find_sound(paused, sil_lv, sil_dur, 0, 0, rate,
            wav_scale=WAV_SCALE)
    labels = Labels()

    if DEBUG:
        print labels_p

    data_n = get_data(normal, rate)
    max_s = float(len(data_n)) / rate
    data_p = get_data(paused, rate)

    max_val = max(data_p) / WAV_SCALE
    thres = sil_lv * max_val / 100

    start_f = 0
    for label in labels_p:
        st = int(label.start * rate)
        ed = int(label.end * rate)
        pattern = data_p[st: ed]
        score_l = search_pattern(data_n, pattern, rate, thres, start_f)
        start_f, score = score_l

        if score > TOLERABLE_SCORE:
            if DEBUG:
                print 'UNTOLERABLE SCORE'
            return (labels, True)

        dur = label.end - label.start

        p_sil_f = get_sil_f(data_p, ed, thres)
        p_sil_s = float(p_sil_f) / rate
        n_sil_f = get_sil_f(data_n, start_f + (ed - st) + 1, thres)
        n_sil_s = float(n_sil_f) / rate
        sil_s = p_sil_s - n_sil_s

        if SND_DUR <= sil_s:
            new_label_after_dur = min(label_after_dur, n_sil_s)
            if fit_mode:
                start = (float(start_f) / rate) - label_before_dur
                start = max(0, min(start, max_s))
                end = start + (label.end - label.start) + \
                    label_before_dur + new_label_after_dur
                end = max(0, min(end, max_s))
                lbl = 'p'
            else:
                start = (float(start_f) / rate) - label_before_dur
                start = max(0, min(start, max_s))

                end = (float(start_f) / rate) + (label.end - label.start)
                end = max(0, min(end, max_s))

                lbl = 's' + str(sil_s)

            labels.append(Label(start, end, lbl))

            if DEBUG:
                fmt = 'score: %4.0f, time: %6.2f - %6.2f, dur: %4.1f' + \
                    ', sil_p: %3.1f, sil_n: %3.1f'
                print fmt % (score, start, end, dur, p_sil_s, n_sil_s)

        start_f = start_f + (ed - st)

    if labels.is_sorted():
        err = False
    else:
        if DEBUG:
            print '[rev_pause] *** ERROR ***'
        err = True

    labels.subtract()

    return (labels, err)


def get_data(name, rate):
    if name.lower().endswith('mp3'):
        buffer, src_rate = mp3.readframesmono(name)
        width = 2
    else:
        wf = wave.open(name, 'r')
        buffer = wf.readframes(wf.getnframes())
        width = wf.getsampwidth()
        src_rate = wf.getframerate()
        if wf.getnchannels() == 2:
            buffer = audioop.tomono(buffer, wf.getsampwidth(), 0.5, 0.5)

    data = rms_ratecv(buffer, 1, width, src_rate, rate)

    return data


def search_pattern(data, pattern, rate, thres, start_f=0):
    score_list = []
    is_prev_sil = True
    weight = 0
    for st in range(start_f, len(data) - len(pattern) + 1):
        if data[st] <= thres:
            is_prev_sil = True
            continue

        if is_prev_sil:
            is_prev_sil = False
            weight = weight + rate

        score = 0
        for i, p in enumerate(pattern):
            score = score + abs(data[st + i] - p)

        score = (score / len(pattern)) + weight

        if score < OK_SCORE:
            return [st, score]
        elif score < TOLERABLE_SCORE:
            score_list.append([st, score])

    if len(score_list) == 0:
        return [[len(data) - len(pattern) + 1], TOLERABLE_SCORE + 1]
    else:
        return min(score_list, key=lambda x: x[1])


if __name__ == '__main__':
    labels = rev_pause('n.wav', 'p.wav')[0]
    labels.write('labels.txt')
