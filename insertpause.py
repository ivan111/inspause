import struct
import wave

from labels import Labels, LBL_CUT

DEFAULT_FACTOR = 1.2
DEFAULT_ADD = 0.5

def insert_pause(in_fname, out_fname, pause_fname, factor=DEFAULT_FACTOR, add=DEFAULT_ADD):
    in_wf = wave.open(in_fname, 'r')
    out_wf = wave.open(out_fname, 'w')
    out_wf.setnchannels(in_wf.getnchannels())
    out_wf.setsampwidth(in_wf.getsampwidth())
    out_wf.setframerate(in_wf.getframerate())

    prev_ed_f = 0
    labels = Labels(open(pause_fname, 'r').readlines())
    rest_nframes = in_wf.getnframes()

    for label in labels:
        st_f = int(label.start * in_wf.getframerate())
        ed_f = int(label.end * in_wf.getframerate())

        if label.label == LBL_CUT:
            # write sound
            s_nframes = st_f - prev_ed_f
            s_nframes = max(0, min(s_nframes, rest_nframes))
            out_wf.writeframes(in_wf.readframes(s_nframes))

            s_nframes = ed_f - prev_ed_f
            s_nframes = max(0, min(s_nframes, rest_nframes))
            rest_nframes = rest_nframes - s_nframes

            pos = min(ed_f, in_wf.getnframes())
            in_wf.setpos(pos)
        else:
            # write sound
            s_nframes = ed_f - prev_ed_f
            s_nframes = max(0, min(s_nframes, rest_nframes))
            out_wf.writeframes(in_wf.readframes(s_nframes))

            rest_nframes = rest_nframes - s_nframes

            # insert pause
            p_nframes = ed_f - st_f
            p_nframes = int((p_nframes * factor) + (add * in_wf.getframerate()))
            p_nframes = p_nframes * in_wf.getnchannels() * in_wf.getsampwidth()

            out_wf.writeframes(struct.pack('%ds' % p_nframes, ''))

        prev_ed_f = ed_f

    if rest_nframes > 0:
        out_wf.writeframes(in_wf.readframes(rest_nframes))

if __name__ == '__main__':
    insert_pause('in.wav', 'out.wav', 'labels.txt')

