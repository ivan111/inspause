# -*- coding: utf-8 -*-

import audioop


DEFAULT_VOL_RATE = 768


class Volume(object):

    def __init__(self, wav, base_rate=DEFAULT_VOL_RATE):
        self.base_vol = calc_volume(wav, base_rate)
        self.base_rate = base_rate

        wav.rewind()

        self.wav_rate = wav.getframerate()
        self.max_f = wav.getnframes() - 1
        self.dur_s = float(wav.getnframes()) / wav.getframerate()

        self.change_rate(self.base_rate)

    def change_rate(self, rate):
        if rate > self.base_rate:
            raise Exception()

        self.rate = rate

        skip = self.base_rate / self.rate

        # skip ごとに要素を間引く
        # a = [1, 2, 3, 4]; a[::2] ==> [1, 3]
        self.vol = self.base_vol[::skip]

        if self.vol:
            self.max_val = max(self.vol)
        else:
            self.max_val = 0

    def __len__(self):
        return len(self.vol)

    def __getitem__(self, i):
        return self.vol[i]


def calc_volume(wav, vol_rate=DEFAULT_VOL_RATE):
    '''
    ボリュームデータを計算する。
    二乗平均平方根（Root Mean Square）を計算。
    '''

    w = wav.getsampwidth()
    rate = wav.getframerate()
    buf = wav.readframes(wav.getnframes())

    if wav.getnchannels() == 2:
        buf = audioop.tomono(buf, w, 0.5, 0.5)

    vol_nframes = wav.getnframes() * vol_rate / rate

    step = len(buf) / vol_nframes
    step = step + (step % w)

    vol = []

    for i in range(vol_nframes):
        sec = float(i) / vol_rate
        wav_f = int(sec * rate)
        st = wav_f * w
        ed = st + step

        rms = audioop.rms(buf[st: ed], w)
        vol.append(rms)

    return vol
