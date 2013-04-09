# -*- coding: utf-8 -*-

import unittest

from label import *


class LabelTests(unittest.TestCase):
    def test_init(self):
        # ラベル
        self._check_init(1, 2, 'p',        1, 2, 'p')
        self._check_init(1, 2, 'x',        1, 2, 'x')
        self._check_init(1, 2, None,       1, 2, 'p')
        self._check_init(1, 2, '',         1, 2, 'p')
        self._check_init(1, 2, 'unknown',  1, 2, 'p')
        self._check_init(1, 2, 's1.23134', 1, 2, 'p')

        # 小数
        start_s = 1.23456
        end_s   = 3.45678
        self._check_init(start_s, end_s, 'p', start_s, end_s, 'p')

        # 範囲
        self._check_init(0,  0,  'p', 0, MIN_DUR_S,     'p')
        self._check_init(-1, 0,  'p', 0, MIN_DUR_S,     'p')
        self._check_init(-1, -2, 'p', 0, MIN_DUR_S,     'p')
        self._check_init(-1, 2,  'p', 0, 2,             'p')
        self._check_init(3,  1,  'p', 3, 3 + MIN_DUR_S, 'p')


    def test_is_xxx(self):
        self._check_is_xxx('p',         True,  False)
        self._check_is_xxx('x',         False, True)
        self._check_is_xxx(None,        True,  False)
        self._check_is_xxx('',          True,  False)
        self._check_is_xxx('s2,32842',  True,  False)


    def test_contains(self):
        self._check_contains(0, 2, 0, True)
        self._check_contains(0, 2, 1, True)
        self._check_contains(0, 2, 2, True)
        self._check_contains(0, 2, 3, False)


    def test_shift(self):
        self._check_shift(0, 1, 5, 5, 6)
        self._check_shift(5, 6, -3, 2, 3)


    def test_dur_s(self):
        self._check_dur_s(1, 3, 2)


    #--------------------------------------------------------------------------
    # 補助メソッド

    def _check_init(self, start_s, end_s, label, exp_start_s, exp_end_s, exp_label):
        lbl = Label(start_s, end_s, label)

        self.assertEqual(lbl.start_s, exp_start_s)
        self.assertEqual(lbl.end_s,   exp_end_s)
        self.assertEqual(lbl.label,   exp_label)


    def _check_is_xxx(self, label, is_pause, is_cut):
        lbl = Label(0, 1, label)

        self.assertEqual(lbl.is_pause(), is_pause)
        self.assertEqual(lbl.is_cut(),   is_cut)


    def _check_contains(self, start_s, end_s, pos_s, contains):
        lbl = Label(start_s, end_s)

        self.assertEqual(lbl.contains(pos_s), contains)


    def _check_shift(self, start_s, end_s, val_s, exp_start_s, exp_end_s):
        lbl = Label(start_s, end_s)

        lbl.shift(val_s)

        self.assertEqual(lbl.start_s, exp_start_s)
        self.assertEqual(lbl.end_s,   exp_end_s)


    def _check_dur_s(self, start_s, end_s, dur_s):
        lbl = Label(start_s, end_s)

        self.assertEqual(lbl.dur_s, dur_s)


if __name__ == '__main__':
    unittest.main()


