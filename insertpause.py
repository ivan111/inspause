# -*- coding: utf-8 -*-

import struct
import wave

from labels import Labels
import mp3

FACTOR = 1.2
ADD = 0.5


def insert_pause(in_fname, out_fname, pause_fname,
                 factor=FACTOR, add=ADD):
    try:
        if in_fname.lower().endswith('mp3'):
            buffer, rate, ch = mp3.readframes(in_fname)
            width = 2
            nframes = len(buffer) / (ch * width)
        else:
            in_wf = wave.open(in_fname, 'r')

            buffer = in_wf.readframes(in_wf.getnframes())
            ch = in_wf.getnchannels()
            width = in_wf.getsampwidth()
            rate = in_wf.getframerate()
            nframes = in_wf.getnframes()

            in_wf.close()

        out_wf = wave.open(out_fname, 'w')
        out_wf.setnchannels(ch)
        out_wf.setsampwidth(width)
        out_wf.setframerate(rate)

        prev_ed_f = 0
        labels = Labels(open(pause_fname, 'r').readlines())
        rest_nframes = nframes

        pos = 0

        for label in labels:
            st_f = int(label.start * rate)
            ed_f = int(label.end * rate)

            if label.is_cut():
                # write sound
                s_nframes = st_f - prev_ed_f
                s_nframes = max(0, min(s_nframes, rest_nframes))
                data = readframes(pos, buffer, s_nframes, ch, width)
                out_wf.writeframes(data)

                s_nframes = ed_f - prev_ed_f
                s_nframes = max(0, min(s_nframes, rest_nframes))
                rest_nframes = rest_nframes - s_nframes

                pos = min(ed_f, nframes)
            else:
                # write sound
                s_nframes = ed_f - prev_ed_f
                s_nframes = max(0, min(s_nframes, rest_nframes))
                data = readframes(pos, buffer, s_nframes, ch, width)
                out_wf.writeframes(data)

                rest_nframes = rest_nframes - s_nframes
                pos = nframes - rest_nframes

                # insert pause
                if label.is_spec():
                    p_nframes = int(label.get_dur() * rate)
                else:
                    p_nframes = ed_f - st_f
                    p_nframes = p_nframes * factor
                    p_nframes = int(p_nframes + (add * rate))
                p_nframes = p_nframes * ch * width

                out_wf.writeframes(struct.pack('%ds' % p_nframes, ''))

            prev_ed_f = ed_f

        if rest_nframes > 0:
            data = readframes(pos, buffer, rest_nframes, ch, width)
            out_wf.writeframes(data)
    except Exception as e:
        print e.message

def readframes(pos, buf, nframes, ch, width):
    st = pos * ch * width
    ed = (pos + nframes) * ch * width
    return buf[st: ed]

if __name__ == '__main__':
    insert_pause('in.wav', 'out.wav', 'labels.txt')
