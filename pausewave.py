#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
waveやffmpegの音声読み込みをラップする。
Python標準ライブラリのwaveのように振る舞うが、
wave形式以外のファイルも扱える。
Conv_tableオブジェクトを設定することでポーズが入った音声や
一部がカットされた音声のデータを返せる。
'''

__all__ = ['open', 'Pause_wave_read']

import os
import wave

import ffmpeg

extensions = ['wav']

if ffmpeg.has_ffmpeg:
    extensions += ffmpeg.EXTENSIONS


def open(f, mode='rb', prg=None):
    '''
    音声ファイルを開く。

    @param mode 'r', 'rb'なら読み込み。'w', 'wb'なら書き込み
    '''

    if f.lower().endswith('.wav'):
        wav = wave.open(f, mode)

        if mode in ('w', 'wb'):
            wav.setparams((2, 2, 44100, 0, 'NONE', 'not compressed'))
    elif ffmpeg.has_ffmpeg:
        wav = ffmpeg.open(f, mode, prg)
    else:
        # ここには来ないはず
        raise Exception('Not Found ffmpeg')

    if mode in ('r', 'rb'):
        return Pause_wave_read(wav)
    elif mode in ('w', 'wb'):
        return wav
    else:
        raise Exception("mode must be 'r', 'rb', 'w', or 'wb'")


class Pause_wave_read(object):
    '''
    waveやffmpegの音声読み込みをラップしたクラス。
    Conv_tableオブジェクトを設定することでポーズが入った音声や
    一部がカットされた音声のデータを返せる。
    '''

    def __init__(self, wav):
        self.wav = wav
        self.tbl = None

        self.frame_size = wav.getnchannels() * wav.getsampwidth()

        # ポーズやカットを考慮した属性
        self.p_pos_f = self.wav.tell()
        self.p_nframes = wav.getnframes()

        #assert self._assert_pos(), self._assert_pos_msg()

    # Labels_readに存在しないメソッドはwavに委譲する
    def __getattr__(self, attr):
        # プロパティのため
        if attr in type(self).__dict__:
            return type(self).__dict__[attr].__get__(self, type(self))

        return getattr(self.wav, attr)

    def rewind(self):
        self.p_pos_f = 0
        self.wav.rewind()

        if self.tbl:
            self.tbl.search_cur(0)

        #assert self._assert_pos(), self._assert_pos_msg()

    def setpos(self, pos_f, is_wav_f=False):
        pos_f = int(pos_f)

        if self.tbl:
            if is_wav_f:
                wav_f = pos_f
                self.wav.setpos(wav_f)
                self.p_pos_f = self.tbl.conv_to_pos_f(wav_f)

                self.tbl.search_cur(wav_f)

                # カットの途中ならカットの終わりへ移動する
                prev = self.tbl.get_prev()
                if prev and prev.is_cut() and prev.wav_st_f <= wav_f < prev.wav_ed_f:
                    self.wav.setpos(prev.wav_ed_f)
            else:
                wav_f = self.tbl.conv_to_wav_f(pos_f)
                self.wav.setpos(wav_f)
                self.p_pos_f = pos_f

                self.tbl.search_cur(wav_f)
        else:
            self.p_pos_f = pos_f
            self.wav.setpos(pos_f)

        #assert self._assert_pos(), self._assert_pos_msg()

    def tell(self, is_wav_f=False):
        if is_wav_f:
            return self.wav.tell()

        if self.tbl:
            return self.p_pos_f
        else:
            return self.wav.tell()

    def tell_s(self, is_wav_f=False):
        return float(self.tell(is_wav_f)) / self.getframerate()

    def getnframes(self, is_wav_f=False):
        if is_wav_f:
            return self.wav.getnframes()

        if self.tbl:
            return self.p_nframes
        else:
            return self.wav.getnframes()

    def readframes(self, nframes):
        if self.tbl is None:
            return self.wav.readframes(nframes)

        if self.p_pos_f >= self.p_nframes:
            return ''

        #assert self._assert_pos(), self._assert_pos_msg()

        rest_f = nframes
        frames = []

        cur = self.tbl.get_cur()
        while cur:
            if cur.is_cut():
                self.wav.setpos(cur.wav_ed_f)
                cur = self.tbl.next()
                continue

            n_f = cur.pos_ed_f - self.p_pos_f
            n_f = min(n_f, rest_f)

            if cur.is_pause():
                data = '\0' * (n_f * self.frame_size)  # silence
            else:
                data = self.wav.readframes(n_f)

            frames.append(data)
            data_f = len(data) / self.frame_size
            self.p_pos_f += data_f
            rest_f -= data_f

            if cur.pos_ed_f <= self.p_pos_f:
                cur = self.tbl.next()
            else:
                cur = None

            if rest_f <= 0:
                break

        #if self.p_pos_f < self.p_nframes:
        #    assert self._assert_pos(), self._assert_pos_msg()

        return ''.join(frames)

    def settable(self, tbl):
        '''
        ポーズ情報が入ったテーブルを設定する。
        これによりポーズが入った音声データが取得されるようになる。
        '''

        self.tbl = tbl

        if tbl:
            wav_f = self.wav.tell()
            self.tbl.search_cur(wav_f)
            self.p_pos_f = self.tbl.conv_to_pos_f(wav_f)
            self.p_nframes = self.tbl.getnframes()
        else:
            self.p_pos_f = self.wav.tell()

        #assert self._assert_pos(), self._assert_pos_msg()

    #--------------------------------------------------------------------------
    # プロパティ

    #--------------------------------------------------------------------------
    # 内部メソッド

    # assert

    def _assert_pos(self):
        if self.tbl:
            return self.wav.tell() == self.tbl.conv_to_wav_f(self.p_pos_f)
        else:
            return self.wav.tell() == self.p_pos_f

    def _assert_pos_msg(self):
        if self.tbl:
            return '%d [wav.tell()] != %d [conv_wav_f(pos_f)], pos_f: %d\n%s' % (
                    self.wav.tell(), self.tbl.conv_to_wav_f(self.p_pos_f), self.p_pos_f, self.tbl)
        else:
            return '%d [wav.tell()] != %d [wav_f]' % (self.wav.tell(), self.p_pos_f)
