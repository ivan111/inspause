# -*- coding: utf-8 -*-

import audioop
import wave

from labels import Label, Labels

DEBUG = False

WAV_SCALE = 10
DEFAULT_SIL_LV = 50
DEFAULT_SIL_DUR = 0.3
DEFAULT_LABEL_DUR = 0.1
#DEFAULT_RATE = 24
DEFAULT_RATE = 24


# based on the Sound Finder Audacity script
# by Jeremy R. Brown (http://www.jeremy-brown.com/)
# Sound Finder based on the Silence Finder Audacity script
# by Alex S. Brown, PMP (http://www.alexsbrown.com)
def find_sound(in_fname, sil_lv=DEFAULT_SIL_LV, sil_dur=DEFAULT_SIL_DUR,
               label_before_dur=DEFAULT_LABEL_DUR,
               label_after_dur=DEFAULT_LABEL_DUR, rate=DEFAULT_RATE):
    if (sil_lv < 0) or (100 < sil_lv):
        raise Exception('[find_sound] Error: sil_lv < 0 or 100 < sil_lv')

    wf = wave.open(in_fname, 'r')

    if DEBUG:
        print_wav_info(wf)

    buffer = wf.readframes(wf.getnframes())
    if wf.getnchannels() == 2:
        buffer = audioop.tomono(buffer, wf.getsampwidth(), 0.5, 0.5)
    data = rms_ratecv(buffer, 1, wf.getsampwidth(), wf.getframerate(), rate)
    width = wf.getsampwidth()
    max_s = float(wf.getnframes()) / wf.getframerate()
    wf.close()

    max_val = max(data) / WAV_SCALE
    # silence threshold level
    thres = sil_lv * max_val / 100
    # Convert the silence duration in seconds to a length in samples
    sil_length = sil_dur * rate
    sil_c = 0  # silence counter
    sil_start = -1
    snd_start = -1
    snd_search = True  # True if we're looking for the start of a sound
    labels = Labels()

    snd_c = 0

    for n, v in enumerate(data):
        if v <= thres:
            sil_c = sil_c + 1
            if sil_start == -1:
                sil_start = n
            elif (not snd_search) and (snd_start != -1) and \
                    (sil_c > sil_length):
                start_time = float(snd_start) / rate - label_before_dur
                start_time = max(0, min(start_time, max_s))
                end_time = float(sil_start) / rate + label_after_dur
                end_time = max(0, min(end_time, max_s))
                labels.append(Label(start_time, end_time))

                snd_search = True
                sil_c = 0
                sil_start = -1
        else:
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
        labels.append(Label(start_time, end_time))

    labels.subtract()

    return labels


def print_wav_info(wf):
    print "nchannels:", wf.getnchannels()
    print "sample width:", wf.getsampwidth()
    print "framerate:", wf.getframerate()
    print "nframes:", wf.getnframes()
    print "dur(sec):", float(wf.getnframes()) / wf.getframerate()


def rms_ratecv(fragment, nchannels, width, src_rate, dst_rate):
    res = []

    src_nframes = len(fragment) / (nchannels * width)
    dst_nframes = src_nframes * dst_rate / src_rate

    step = len(fragment) / dst_nframes
    step = step + (step % width)

    for i in range(0, dst_nframes):
        res.append(audioop.rms(fragment[i * step: (i + 1) * step], width))

    return res

if __name__ == '__main__':
    labels = find_sound('in.wav')
    labels.write('labels.txt')
