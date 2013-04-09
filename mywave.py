# -*- coding: utf-8 -*-

import audioop
from ctypes import *
import os
import struct
import sys
import wave

try:
    import eyed3
except:
    eyed3 = None

try:
    mad = cdll.LoadLibrary('libmad.dll')
except:
    mad = None

try:
    import pymedia.audio.acodec as acodec
    import pymedia.muxer as muxer

    extensions = muxer.extensions
except:
    extensions = ['wav']

from labels import Label, Labels
from myfile import get_ext, get_pause_file


SIL_LV       = 5    # 無音認識レベル(%)。低いほど無音判定がきびしくなる
SIL_DUR_S    = 0.3  # この秒数だけ無音が続くと無音と判定
SND_DUR_S    = 0.2  # この秒数だけ音が続くと音があると判定
BEFORE_DUR_S = 0.2  # ラベルの前に余裕をもたせる秒数
AFTER_DUR_S  = 0.2  # ラベルの後に余裕をもたせる秒数
FIND_RATE    = 384
CHUNK_F      = 1024
SMA_SAMPLE   = 64   # 単純移動平均の区間
NO_DISTINCTION = -1 # 特徴位置がない
MAX_DIFF     = 0.2
MIN_DIFF     = 0.0001


def auto_shift_diff_s(distinction_s, another_s):
    '''
    自動ずれ調整の調整秒数

    @return 自動ずれ調整できなければ 0
    '''

    if distinction_s == NO_DISTINCTION or another_s == NO_DISTINCTION:
        return 0

    diff_s =  distinction_s - another_s

    if MIN_DIFF < abs(diff_s) < MAX_DIFF:
        return diff_s

    return 0


def is_near_distinction(distinction_s, another_s):
    '''
    特徴位置が近いか？
    '''

    if distinction_s == NO_DISTINCTION or another_s == NO_DISTINCTION:
        return False

    diff_s =  distinction_s - another_s

    if abs(diff_s) < MAX_DIFF:
        return True

    return False



class MyWave(object):
    '''
    音を表すクラス
    '''

    def __init__(self, snd_file, labels_file, progress_dlg=None):
        self._init_instance_var()

        self.snd_file    = snd_file
        self.labels_file = labels_file

        ext = get_ext(snd_file)

        try:
            if ext == 'wav':
                self.snd = SoundWave(snd_file)
            elif ext in extensions:
                self.snd = SoundOther(snd_file, progress_dlg)
            else:
                self.err_msg = u'対応していないファイル形式です'
                return
        except Exception as e:
            self.err_msg = e.message
            return

        self.vol = self._calc_volume(FIND_RATE)
        self.distinction_s = self._find_distinction_s()


    def _init_instance_var(self):
        self.snd = None
        self.vol = []
        self.err_msg = None
        self.distinction_s = NO_DISTINCTION  # 特徴位置


    def read(self, max_read_f=None):
        return self.snd.read(max_read_f)


    def calc_volume(self, view_factor):
        # view_factor ごとに要素を間引く
        # a = [1, 2, 3, 4]; a[::2] ==> [1, 3]
        return self.vol[::1 << view_factor]


    def find_sound(self, sil_lv=SIL_LV, sil_dur_s=SIL_DUR_S,
            before_dur_s=BEFORE_DUR_S, after_dur_s=AFTER_DUR_S):
        '''
        音がある部分にポーズラベルをつける

        based on the Sound Finder Audacity script
        by Jeremy R. Brown (http://www.jeremy-brown.com/)
        Sound Finder based on the Silence Finder Audacity script
        by Alex S. Brown, PMP (http://www.alexsbrown.com)

        @param sil_lv       無音認識レベル（％）。最大音に対して何％以下を無音と判定するか
        @param sil_dur_s    無音認識時間（秒）
        @param before_dur_s ラベルの前に余裕をもたせる秒数
        @param after_dur_s  ラベルの後に余裕をもたせる秒数

        @return ラベル
        '''

        sil_lv = max(0, min(sil_lv, 100))

        max_val = max(self.vol)
        # silence threshold level
        thres = sil_lv * max_val / 100
        # Convert the silence duration in seconds to a length in samples
        sil_f = sil_dur_s * FIND_RATE
        snd_f = SND_DUR_S * FIND_RATE
        sil_c = 0  # silence counter
        snd_c = 0
        sil_start = -1
        snd_start = -1
        snd_search = True  # True if we're looking for the start of a sound
        labels = Labels()

        for n, v in enumerate(self.vol):
            if v <= thres:
                sil_c = sil_c + 1
                if sil_start == -1:
                    sil_start = n
                elif (not snd_search) and (snd_start != -1) and \
                        (sil_c > sil_f) and (snd_c > snd_f):

                    sil_f = self._get_sil_f(self.vol, sil_start, thres,
                            sil_start + int(after_dur_s * FIND_RATE))
                    start_time = (float(snd_start) / FIND_RATE) - before_dur_s
                    start_time = max(0, min(start_time, self.dur_s))
                    end_time   = float(sil_start + sil_f) / FIND_RATE
                    end_time   = max(0, min(end_time, self.dur_s))

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
            start_time = float(snd_start) / FIND_RATE - before_dur_s
            start_time = max(0, min(start_time, self.dur_s))
            end_time   = float(sil_start) / FIND_RATE + after_dur_s
            end_time   = max(0, min(end_time, self.dur_s))

            if end_time < start_time:
                end_time = self.dur_s

            try:
                labels.append(Label(start_time, end_time))
            except Exception as e:
                print e.message

        labels.subtract()

        labels.distinction_s = self.distinction_s

        return labels


    def _get_sil_f(self, data, start_f, thres, max_f=None):
        if (max_f is None) or (len(data) < max_f):
            max_f = len(data)

        sil_c = 0
        for i in range(start_f, max_f):
            if data[i] <= thres:
                sil_c = sil_c + 1
            else:
                break

        return sil_c


    def insert_pause(self, ext, labels, factor, add):
        self.snd.insert_pause(ext, labels, factor, add)


    def _calc_volume(self, rate):
        '''
        ボリュームデータを計算する。
        二乗平均平方根（Root Mean Square）を計算。
        '''

        buf = self.snd.buf

        # ステレオならモノラルに変換
        if self.snd.ch == 2:
            buf = audioop.tomono(buf, self.snd.w, 0.5, 0.5)

        nframes = self.snd.max_f * rate / self.snd.rate

        step = len(buf) / nframes
        step = step + (step % self.snd.w)

        vol = []

        for i in range(0, nframes):
            vol.append(audioop.rms(buf[i * step: (i + 1) * step], self.snd.w))

        return vol


    def _find_distinction_s(self):
        '''
        特徴となる位置の最初の１つを返す。
        見つからなければ NO_DISTINCTION
        '''

        labels = self.find_sound(5, 0.3, 0, 0)

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


    def f_to_s(self, f):
        return self.snd.f_to_s(f)


    def s_to_f(self, s):
        return self.snd.s_to_f(s)


    #--------------------------------------------------------------------------
    # プロパティ

    # ---- チャンネル数

    @property
    def ch(self):
        return self.snd.ch


    # ---- サンプル幅

    @property
    def w(self):
        return self.snd.w


    # ---- サンプリングレート

    @property
    def rate(self):
        return self.snd.rate


    # ---- 最大フレーム

    @property
    def max_f(self):
        return self.snd.max_f


    # ---- 現在位置（フレーム）

    @property
    def cur_f(self):
        return self.snd.cur_f

    @cur_f.setter
    def cur_f(self, cur_f):
        self.snd.cur_f = cur_f


    # ---- 現在位置（秒）

    @property
    def cur_s(self):
        return self.snd.cur_s

    @cur_s.setter
    def cur_s(self, cur_s):
        self.snd.cur_s = cur_s


    # ---- 長さ（秒）

    @property
    def dur_s(self):
        return self.snd.dur_s


    # ---- フレームサイズ

    @property
    def frame_size(self):
        return self.snd.frame_size


    # ---- mp3 タグ

    @property
    def tag(self):
        return self.snd.tag


class SoundWave(object):
    '''
    wave 形式の音を表すクラス
    '''

    def __init__(self, snd_file, dlg=None):
        self.snd_file = snd_file
        self._init_instance_var_wave()

        self.load_buf(snd_file, dlg)

        if self.w != 2:
            raise Exception()

        self.dur_s = float(self.max_f) / self.rate
        self.frame_size = self.ch * self.w


    def _init_instance_var_wave(self):
        self.buf     = ''  # 音データ
        self.ch      = 0   # チャンネル数。1:モノラル, 2:ステレオ
        self.w       = 0   # サンプル幅
        self.rate    = 0   # サンプリングレート
        self.bitrate = 0   # ビットレート
        self.max_f   = 0   # フレーム数
        self.dur_s   = 0   # 長さ（秒）
        self.frame_size = 0  # フレームサイズ

        self.tag = None

        # ---- プロパティ用
        self._cur_f = 0


    def load_buf(self, wav_file, dlg):
        wf = wave.open(wav_file, 'r')

        self.buf     = wf.readframes(wf.getnframes())
        self.ch      = wf.getnchannels()
        self.w       = wf.getsampwidth()
        self.rate    = wf.getframerate()
        self.max_f   = wf.getnframes()

        wf.close()


    def read(self, max_read_f=None):
        '''
        現在位置から音声データを読み込む。
        CHUNK_F に足りない分は無音を補う。

        @param num_f 最大読み込みフレーム数
        '''

        if max_read_f == None:
            data = self.read_frames(self.cur_f, CHUNK_F)
        else:
            max_read_f = min(max_read_f, CHUNK_F)
            data = self.read_frames(self.cur_f, max_read_f)

        data_f = len(data) / self.frame_size

        self.cur_f += data_f

        if data_f < CHUNK_F:
            # CHUNK_F に足りない分を無音で補う
            pause_fi = (CHUNK_F - data_f) * self.frame_size
            data += struct.pack('%ds' % pause_fi, '')

        return data


    def read_frames(self, st_f, nframes):
        '''
        @param st_f    開始フレーム
        @param nframes 読み込むフレーム数
        '''

        st = st_f * self.frame_size
        ed = st + (nframes * self.frame_size)
        ed = min(ed, len(self.buf))

        return self.buf[st: ed]


    def insert_pause(self, ext, labels, factor, add):
        '''
        ポーズを挿入した音声ファイルを作成する
        '''

        try:
            out_file = get_pause_file(self.snd_file)

            out_file = self.open_pause_file(out_file, ext)

            prev_ed_f = 0
            remain_f = self.max_f

            cur_f = 0

            for label in labels:
                st_f = self.s_to_f(label.start_s)
                ed_f = self.s_to_f(label.end_s)

                if label.is_cut():
                    # ---- カット範囲の前までの音声を書き込む
                    snd_f = st_f - prev_ed_f
                    snd_f = max(0, min(snd_f, remain_f))
                    data = self.read_frames(cur_f, snd_f)
                    self.write_pause_file(data)

                    # ----  残りフレーム数と現在値を更新
                    snd_f = ed_f - prev_ed_f
                    snd_f = max(0, min(snd_f, remain_f))
                    remain_f -= snd_f

                    cur_f = min(ed_f, self.max_f)
                else:
                    # ---- ポーズの前までの音声を書き込む
                    snd_f = ed_f - prev_ed_f
                    snd_f = max(0, min(snd_f, remain_f))
                    data = self.read_frames(cur_f, snd_f)
                    self.write_pause_file(data)

                    # ----  残りフレーム数と現在値を更新
                    remain_f -= snd_f
                    cur_f = self.max_f - remain_f

                    # ---- ポーズ挿入
                    pause_f = ed_f - st_f
                    pause_f = pause_f * factor
                    pause_f = int(pause_f + (add * self.rate))

                    pause_fi = pause_f * self.frame_size

                    data = struct.pack('%ds' % pause_fi, '')
                    self.write_pause_file(data)

                prev_ed_f = ed_f

            if remain_f > 0:
                data = self.read_frames(cur_f, remain_f)
                self.write_pause_file(data)

            self.close_pause_file()

            # ---- mp3 のタグを設定
            if self.ext == 'mp3' and self.tag:
                try:
                    f = eyed3.load(out_file)
                    f.tag = self.tag
                    f.tag.header.version = eyed3.id3.ID3_V2_3
                    f.tag.save(out_file)
                except Exception as e:
                    print e.message
        except Exception as e:
            print e.message


    def open_pause_file(self, out_file, ext):
        codecId = 0

        if ext != 'wav':
            ext = 'mp3'

            codecId = acodec.getCodecID(ext)

            # エンコードできないならwav形式で保存する
            if codecId == 0:
                ext = 'wav'

        out_file = os.path.splitext(out_file)[0] + '.' + ext

        self.ext = ext

        if ext == 'wav':
            self.wf = wave.open(out_file, 'w')

            self.wf.setnchannels(self.ch)
            self.wf.setsampwidth(self.w)
            self.wf.setframerate(self.rate)
        else:
            params = {
                'id':          codecId,
                'bitrate':     self.bitrate,
                'sample_rate': self.rate,
                'ext':         ext,
                'channels':    self.ch
            }

            self.enc = acodec.Encoder(params)

            self.wf = open(out_file, 'wb')

            self.mx = muxer.Muxer(ext)
            self.stId = self.mx.addStream(muxer.CODEC_TYPE_AUDIO, params)

            ss = self.mx.start()
            if ss:
                self.wf.write(ss)

        return out_file


    def write_pause_file(self, data):
        if self.ext == 'wav':
            self.wf.writeframes(data)
        else:
            frames = self.enc.encode(data)

            for fr in frames:
                ss = self.mx.write(self.stId, fr)
                if ss:
                    self.wf.write(ss)


    def close_pause_file(self):
        if self.ext == 'wav':
            self.wf.close()
            self.wf = None
        else:
            ss = self.mx.end()
            if ss:
                self.wf.write(ss)

            self.wf.close()

            self.stId = None
            self.mx   = None
            self.wf   = None
            self.enc  = None


    def f_to_s(self, f):
        return float(f) / self.rate


    def s_to_f(self, s):
        return int(s * self.rate)


    #--------------------------------------------------------------------------
    # プロパティ

    # ---- 現在位置（フレーム）

    @property
    def cur_f(self):
        return self._cur_f

    @cur_f.setter
    def cur_f(self, cur_f):
        self._cur_f = max(0, min(cur_f, self.max_f))


    # ---- 現在位置（秒）

    @property
    def cur_s(self):
        return self.f_to_s(self.cur_f)

    @cur_s.setter
    def cur_s(self, cur_s):
        self.cur_f = self.s_to_f(cur_s)
        self.cur_f = self.s_to_f(cur_s)


BUF_SIZE = 5 * 8192

class SoundOther(SoundWave):
    '''
    wave 形式以外の音を表すクラス
    '''

    def load_buf(self, snd_file, dlg=None):
        ext = get_ext(snd_file)

        if ext == 'mp3' and eyed3:
            try:
                self.tag = eyed3.load(snd_file).tag
            except:
                pass

        if ext == 'mp3' and sys.platform == 'win32' and mad:
            if self.mad_load_mp3(snd_file, dlg):
                return

        f = open(snd_file, 'rb')
        s = f.read()
        f.close()

        dm = muxer.Demuxer(ext)
        frames = dm.parse(s)

        ch = rate = bitrate = decoder = None

        progress = 0

        buf = []

        # フレーム数の計算と位置インデックスの作成
        for i, fr in enumerate(frames):
            if decoder is None:
                if dm.streams[fr[0]] is None:
                    raise Exception(u'対応してないファイル形式です')

                decoder = acodec.Decoder(dm.streams[fr[0]])

            r = decoder.decode(fr[1])

            if dlg:
                new_progress = i * 100 / len(frames)

                if progress != new_progress:
                    progress = new_progress
                    dlg.Update(progress)

            if r and r.data:
                if ch is None:
                    ch      = r.channels
                    rate    = r.sample_rate
                    bitrate = r.bitrate

                buf.append(str(r.data))

        if ch is None:
            raise Exception(u'音声ファイルの読み込みに失敗しました')

        self.buf     = ''.join(buf)
        self.ch      = ch
        self.w       = 2
        self.rate    = rate
        self.bitrate = bitrate
        self.max_f   = len(self.buf) / (self.ch * self.w)


    def mad_load_mp3(self, snd_file, dlg):
        '''
        pymedia で mp3 を読むとフレーム数が微妙に足りなくて、だんだんと時間がずれていく。
        最終的には、何十ミリ秒とか百何ミリ秒ぐらいずれる。
        俺の読み方が悪い？それともpymediaのバグ？
        回避策として、前のようにlibmadで読むことにした。
        '''

        if not mad:
            return False

        handle = mad.open(snd_file.encode('cp932'))
        if handle == -1:
            return False

        c_short_a = c_short * BUF_SIZE
        data = c_short_a()
        mad.readframes.argtypes = [c_int, POINTER(c_short), c_int]
        i = 0

        try:
            size = mad.readframes(handle, data, BUF_SIZE)

            buf = []
            while size != 0:
                buf.append(struct.pack('%dh' % size, *data))
                size = mad.readframes(handle, data, BUF_SIZE)

                if dlg:
                    progress = i * 100 / 200 # TODO: 適当な数字
                    progress = min(progress, 99)
                    dlg.Update(progress)
                    i += 1

            buf  = ''.join(buf)
            ch   = mad.getnchannels(handle)
            rate = mad.getframerate(handle)
        except Exception as e:
            print e.message

            return False

        mad.close(handle)

        self.buf     = buf
        self.ch      = ch
        self.w       = 2
        self.rate    = rate
        self.bitrate = 128000  # TODO: 本当は libmad から読んだほうがいい
        self.max_f   = len(self.buf) / (self.ch * self.w)

        return True


if __name__ == '__main__':
    wav = MyWave('in.wav')
    print wav.find_sound()
