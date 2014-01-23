# -*- coding: utf-8 -*-

'''
コンブ食べる
ポーズ付き位置からポーズなし位置への変換するためのテーブル
'''

from label import LBL_PAUSE, LBL_CUT


LBL_SOUND = 's'


class Conv_table_item(object):

    def __init__(self, pos_st_f, pos_ed_f, wav_st_f, wav_ed_f, label):
        self.pos_st_f = pos_st_f
        self.pos_ed_f = pos_ed_f
        self.wav_st_f = wav_st_f
        self.wav_ed_f = wav_ed_f
        self.label = label

    def __str__(self):
        if self.label == LBL_PAUSE:
            typ = 'pause'
        elif self.label == LBL_CUT:
            typ = 'cut'
        else:
            typ = 'sound'

        return 'pos_st_f: %8d, pos_ed_f: %8d, wav_st_f: %8d, wav_ed_f: %8d, type: %s' % (
                self.pos_st_f, self.pos_ed_f, self.wav_st_f, self.wav_ed_f, typ)

    def is_pause(self):
        return self.label == LBL_PAUSE

    def is_cut(self):
        return self.label == LBL_CUT

    def is_sound(self):
        return self.label == LBL_SOUND


class Conv_table(list):
    '''
    ポーズ入りの位置からポーズなしの位置への変換テーブル
    '''

    def __init__(self, labels, rate, nframes, factor, add_s):
        list.__init__(self)
        self._create_table(labels, rate, nframes, factor, add_s)
        self.cur_i = 0

    def __str__(self):
        cur_i_str = 'cur_i: %d [%s]' % (self.cur_i, self.get_cur())
        items_str = '\n'.join([str(x) for x in self])

        return '%s\n%s\n' % (cur_i_str, items_str)

    def getnframes(self):
        if len(self) > 0:
            return self[-1].pos_ed_f
        else:
            return 0

    def search_cur(self, wav_f):
        for i in range(len(self)):
            if self[i].wav_ed_f > wav_f:
                self.cur_i = i
                return

        self.cur_i = len(self)

    def get_prev(self):
        if self.cur_i - 1 >= 0:
            return self[self.cur_i - 1]
        else:
            return None

    def get_cur(self):
        if self.cur_i < len(self):
            return self[self.cur_i]
        else:
            return None

    def next(self):
        self.cur_i += 1
        return self.get_cur()

    def conv_to_wav_f(self, pos_f):
        for item in self:
            if item.pos_ed_f > pos_f:
                if item.is_pause():
                    return item.wav_ed_f
                else:
                    return item.wav_st_f + (pos_f - item.pos_st_f)

        return 0

    def conv_to_pos_f(self, wav_f):
        for item in self:
            if item.wav_ed_f > wav_f:
                if item.is_cut():
                    return item.pos_ed_f
                else:
                    return item.pos_st_f + (wav_f - item.wav_st_f)

        return 0

    #--------------------------------------------------------------------------
    # 内部メソッド

    def _create_table(self, labels, rate, nframes, factor, add_s):
        add_f = int(add_s * rate)

        pos_f = 0  # ポーズやカットも考慮した位置
        wav_f = 0  # 対応するwavの位置
        rest_f = nframes  # 残りフレーム
        prev_ed_f = 0

        for label in labels:
            st_f = int(label.start_s * rate)
            ed_f = int(label.end_s * rate)

            if label.is_cut():
                # ---- カット範囲の前までの音声
                snd_f = st_f - prev_ed_f
                snd_f = max(0, min(snd_f, rest_f))

                if snd_f > 0:
                    pos_f += snd_f
                    wav_f += snd_f
                    prev_ed_f += snd_f
                    rest_f -= snd_f

                    self._add_item(pos_f, wav_f, LBL_SOUND)

                # ---- カット範囲
                cut_f = ed_f - st_f
                cut_f = max(0, min(cut_f, rest_f))

                wav_f = min(ed_f, nframes)

                if cut_f > 0:
                    rest_f -= cut_f

                    self._add_item(pos_f, wav_f, LBL_CUT)
            else:
                # ---- ポーズの前までの音声
                snd_f = ed_f - prev_ed_f
                snd_f = max(0, min(snd_f, rest_f))

                if snd_f > 0:
                    pos_f += snd_f
                    wav_f += snd_f
                    prev_ed_f += snd_f
                    rest_f -= snd_f

                    self._add_item(pos_f, wav_f, LBL_SOUND)

                # ---- ポーズ
                pause_f = ed_f - st_f
                pause_f = int(pause_f * factor)
                pause_f = pause_f + add_f

                if pause_f > 0:
                    pos_f += pause_f

                    self._add_item(pos_f, wav_f, LBL_PAUSE)

            prev_ed_f = ed_f

        if rest_f > 0:
            pos_f += rest_f
            wav_f += rest_f

            self._add_item(pos_f, wav_f, LBL_SOUND)

    def _add_item(self, pos_ed_f, wav_ed_f, label):
        pos_st_f = 0
        wav_st_f = 0
        if len(self) > 0:
            pos_st_f = self[-1].pos_ed_f
            wav_st_f = self[-1].wav_ed_f

        item = Conv_table_item(pos_st_f, pos_ed_f, wav_st_f, wav_ed_f, label)
        self.append(item)
