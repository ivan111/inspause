# -*- coding: utf-8 -*-

import audioop
import wave

from labels import Label, Labels
import mp3

WAV_SCALE = 10
SIL_LV = 50
SIL_DUR = 0.3
SND_DUR = 0.2
LABEL_BEFORE_DUR = 0.1
LABEL_AFTER_DUR = 0.1
RATE = 48


# based on the Sound Finder Audacity script
# by Jeremy R. Brown (http://www.jeremy-brown.com/)
# Sound Finder based on the Silence Finder Audacity script
# by Alex S. Brown, PMP (http://www.alexsbrown.com)
def find_sound(in_fname, sil_lv=SIL_LV, sil_dur=SIL_DUR,
               label_before_dur=LABEL_BEFORE_DUR,
               label_after_dur=LABEL_AFTER_DUR, rate=RATE, snd_dur=SND_DUR,
               wav_scale=WAV_SCALE):

    if (sil_lv < 0) or (100 < sil_lv):
        raise Exception('[find_sound] Error: sil_lv < 0 or 100 < sil_lv')

    if in_fname.lower().endswith('mp3'):
        buffer, src_rate = mp3.readframesmono(in_fname)
        width = 2
        nframes = len(buffer) / 2
    else:
        wf = wave.open(in_fname, 'r')

        buffer = wf.readframes(wf.getnframes())
        src_rate = wf.getframerate()
        width = wf.getsampwidth()
        nframes = wf.getnframes()

        if wf.getnchannels() == 2:
            buffer = audioop.tomono(buffer, wf.getsampwidth(), 0.5, 0.5)

        wf.close()

    data = rms_ratecv(buffer, 1, width, src_rate, rate)
    max_s = float(nframes) / src_rate

    max_val = max(data) / wav_scale
    # silence threshold level
    thres = sil_lv * max_val / 100
    # Convert the silence duration in seconds to a length in samples
    sil_length = sil_dur * rate
    snd_length = snd_dur * rate
    sil_c = 0  # silence counter
    snd_c = 0
    sil_start = -1
    snd_start = -1
    snd_search = True  # True if we're looking for the start of a sound
    labels = Labels()

    for n, v in enumerate(data):
        if v <= thres:
            sil_c = sil_c + 1
            if sil_start == -1:
                sil_start = n
            elif (not snd_search) and (snd_start != -1) and \
                    (sil_c > sil_length) and (snd_c > snd_length):

                sil_f = get_sil_f(data, sil_start, thres,
                        sil_start + int(label_after_dur * rate))
                start_time = (float(snd_start) / rate) - label_before_dur
                start_time = max(0, min(start_time, max_s))
                end_time = float(sil_start + sil_f) / rate
                end_time = max(0, min(end_time, max_s))
                try:
                    labels.append(Label(start_time, end_time))
                except Exception as e:
                    print e.message

                snd_search = True
                sil_c = 0
                snd_c = 0
                sil_start = -1
        else:
            snd_c = snd_c + 1
            if snd_search:
                snd_search = False
                snd_start = n
            sil_c = 0
            sil_start = -1

    if not snd_search:
        start_time = float(snd_start) / rate - label_before_dur
        start_time = max(0, min(start_time, max_s))
        end_time = float(sil_start) / rate + label_after_dur
        end_time = max(0, min(end_time, max_s))
        if end_time < start_time:
            end_time = max_s
        try:
            labels.append(Label(start_time, end_time))
        except Exception as e:
            print e.message

    labels.subtract()

    return labels


def rms_ratecv(fragment, nchannels, width, src_rate, dst_rate):
    res = []

    src_nframes = len(fragment) / (nchannels * width)
    dst_nframes = src_nframes * dst_rate / src_rate

    step = len(fragment) / dst_nframes
    step = step + (step % width)

    for i in range(0, dst_nframes):
        res.append(audioop.rms(fragment[i * step: (i + 1) * step], width))

    return res


def get_sil_f(data, start_f, thres, max_f=None):
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
    labels = find_sound('in.wav')
    labels.write('labels.txt')
