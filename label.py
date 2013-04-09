# -*- coding: utf-8 -*-
'''
ラベル

ポーズの位置を表す。
'''

MIN_DUR_S = 0.1  # ラベルの最小長さ（秒）
LBL_PAUSE = 'p'  # ポーズ挿入ラベル
LBL_CUT   = 'x'  # 選択範囲カットラベル
LBL_SPEC  = 's'  # 固定ポーズ挿入ラベル。******** 廃止 ********


class Label(object):
    def __init__(self, start_s, end_s, label=LBL_PAUSE):
        self._color = None
        self._init_pos(start_s, end_s)
        self.label = label


    def __str__(self):
        # （例）"3.134283    9.482720    p"
        return '%.6f\t%.6f\t%s' % (self._start_s, self._end_s, self._label)


    def is_pause(self):
        return self.label == LBL_PAUSE


    def is_cut(self):
        return self.label == LBL_CUT


    def set_pause(self):
        self.label = LBL_PAUSE


    def set_cut(self):
        self.label = LBL_CUT


    def contains(self, pos_s):
        '''
        指定した位置を含むか？
        '''

        if self.start_s <= pos_s <= self.end_s:
            return True
        else:
            return False


    def shift(self, val_s):
        '''
        ラベルをずらす
        '''

        self._start_s += val_s
        self._end_s   += val_s

        self._color = None


    def _init_pos(self, start_s, end_s):
        start_s = max(0, start_s)
        end_s   = max(0, end_s)

        if start_s + MIN_DUR_S > end_s:
            end_s = start_s + MIN_DUR_S

        self._start_s = start_s
        self._end_s   = end_s


    #--------------------------------------------------------------------------
    # プロパティ

    # ---- 開始位置（秒）

    @property
    def start_s(self):
        return self._start_s

    @start_s.setter
    def start_s(self, start_s):
        self._start_s = max(0, min(start_s, self._end_s - MIN_DUR_S))
        self._color = None


    # ---- 終了位置（秒）

    @property
    def end_s(self):
        return self._end_s

    @end_s.setter
    def end_s(self, end_s):
        self._end_s = max(self._start_s + MIN_DUR_S, end_s)
        self._color = None


    # ---- ラベル

    @property
    def label(self):
        return self._label

    @label.setter
    def label(self, label):
        if label == LBL_CUT:
            self._label = LBL_CUT
        else:
            self._label = LBL_PAUSE


    # ---- 長さ（秒）

    @property
    def dur_s(self):
        return self.end_s - self.start_s


    # ---- 色。長さに応じて色が変わる

    @property
    def color(self):
        if not self._color:
            wavelength = self.dur_s *  60 + 380  # 8 秒が 780 になるように調整する
            if wavelength > 780:
                self._color = [255, 0, 0]
            else:
                self._color = wav2RGB(wavelength)

        return self._color


# 波長からRGBを得る
# http://codingmess.blogspot.jp/2009/05/conversion-of-wavelength-in-nanometers.html
def wav2RGB(wavelength):
    w = int(wavelength)

    # colour
    if w >= 380 and w < 440:
        R = -(w - 440.) / (440. - 350.)
        G = 0.0
        B = 1.0
    elif w >= 440 and w < 490:
        R = 0.0
        G = (w - 440.) / (490. - 440.)
        B = 1.0
    elif w >= 490 and w < 510:
        R = 0.0
        G = 1.0
        B = -(w - 510.) / (510. - 490.)
    elif w >= 510 and w < 580:
        R = (w - 510.) / (580. - 510.)
        G = 1.0
        B = 0.0
    elif w >= 580 and w < 645:
        R = 1.0
        G = -(w - 645.) / (645. - 580.)
        B = 0.0
    elif w >= 645 and w <= 780:
        R = 1.0
        G = 0.0
        B = 0.0
    else:
        R = 0.0
        G = 0.0
        B = 0.0

    # intensity correction
    if w >= 380 and w < 420:
        SSS = 0.3 + 0.7*(w - 350) / (420 - 350)
    elif w >= 420 and w <= 700:
        SSS = 1.0
    elif w > 700 and w <= 780:
        SSS = 0.3 + 0.7*(780 - w) / (780 - 700)
    else:
        SSS = 0.0
    SSS *= 255

    return [int(SSS*R), int(SSS*G), int(SSS*B)]

