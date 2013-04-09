# -*- coding: utf-8 -*-
'''
ラベル情報
１つの音声に対するポーズ情報を表す。
'''

import re

from label import Label, MIN_DUR_S


NEAR_S  = 0.4  # 近い隣接範囲を同時に動かすときに使用

ST_DISTINCTION = '-1'
NO_DISTINCTION = -1  # 特徴位置がない


# "1.234567    3.456789    p" などの文字列を分割するための正規表現
label_re = re.compile(r'^(\d+(\.\d{0,6})?)\s+(\d+(\.\d{0,6})?)\s+(.*)')


class Labels(list):
    '''
    常に終了位置順でソートされている
    '''

    def __init__(self, lines=None):
        self.selected = None
        self.distinction_s = NO_DISTINCTION  # 特徴位置。ずれ補正に使う

        if lines is None:
            lines = []

        self._load_from_list(lines)


    def __str__(self):
        return '\n'.join([str(label) for label in self])


    def write(self, file_name):
        self._sort()

        f = open(file_name, 'w')

        if self.distinction_s != NO_DISTINCTION:
            s = '%s\t%d\t%.6f\n' % (ST_DISTINCTION, 0, self.distinction_s)
            f.write(s)

        f.write(str(self))

        f.close()


    #--------------------------------------------------------------------------
    # コマンド

    # ---- ラベル挿入

    def insert_label(self, pos_s, dur_s, max_s):
        rng = self._get_insertable_range(pos_s, dur_s, max_s)

        if rng is None:
            return

        if pos_s - rng[0] < dur_s / 2:
            start = rng[0]
            end = start + dur_s
        elif rng[1] - pos_s < dur_s / 2:
            end = rng[1]
            start = end - dur_s
        else:
            start = pos_s - (dur_s / 2)
            end = start + dur_s

        label = Label(start, end)
        self.append(label)
        self.select_by_index(len(self) - 1)

        self._sort()


    def can_insert_label(self, pos_s, dur_s, max_s):
        rng = self._get_insertable_range(pos_s, dur_s, max_s)

        if rng is None:
            return False
        else:
            return True


    # ---- ラベルカット

    def cut(self, pos_s):
        cut_i = -1
        new_label = None

        for i, label in enumerate(self):
            if label.contains(pos_s):
                cut_i = i
                new_label = Label(pos_s, label.end_s)
                label.end_s = pos_s
                break

        if cut_i != -1:
            self.insert(cut_i + 1, new_label)


    def can_cut(self, pos_s):
        for label in self:
            if label.contains(pos_s):
                # カット結果が狭い場合はカットできないようにする
                if pos_s < label.start_s + 0.1 or label.end_s - 0.1 < pos_s:
                    continue

                return True

        return False


    # ---- ラベル結合

    def merge_left(self):
        prev_sel = self._get_prev_selected()

        if prev_sel:
            prev_sel.end_s = self.selected.end_s
            self.remove(self.selected)
            self.selected = prev_sel


    def can_merge_left(self):
        if self._get_prev_selected():
            return True
        else:
            return False


    def merge_right(self):
        next_sel = self._get_next_selected()

        if next_sel:
            self.selected.end_s = next_sel.end_s
            self.remove(next_sel)


    def can_merge_right(self):
        if self._get_next_selected():
            return True
        else:
            return False


    # ----

    def shift(self, val_s):
        for label in self:
            label.shift(val_s)


    def subtract(self):
        '''
        重なりをなくす
        '''

        if len(self) == 0:
            return

        prev = self[0]

        for label in self[1:]:
            if prev.end_s > label.start_s:
                label.start_s = prev.end_s
            elif (label.start_s < prev.start_s) and (prev.end_s < label.end_s):
                label.start_s = prev.end_s

            prev = label


    def clean_data(self):
        '''
        カットラベルが他と重ならないように修正する
        '''

        if 1 <= len(self):
            prev_label = self[0]

        for label in self[1:]:
            if label.start_s < prev_label.end_s:
                if label.is_cut():
                    label.start_s = prev_label.end_s

            prev_label = label


    #--------------------------------------------------------------------------
    # 選択関連

    def select(self, pos_s):
        '''
        指定した位置（秒）のラベルを選択する。
        重なっている場合はサイクリックに選択する。
        '''

        found_labels = []

        for label in self:
            if label.contains(pos_s):
                found_labels.append(label)

        if len(found_labels) == 0:
            self.selected = None
        elif len(found_labels) == 1:
            self.selected = found_labels[0]
        elif len(found_labels) > 1:  # 重なりがある
            if self.selected is None:
                self.selected = found_labels[0]
            elif self.selected not in found_labels:
                self.selected = found_labels[0]
            else:
                i = found_labels.index(self.selected) + 1
                if i == len(found_labels):
                    i = 0
                self.selected = found_labels[i]


    def select_by_index(self, pos_i):
        if pos_i < 0 or len(self) <= pos_i:
            return

        self.selected = self[pos_i]


    def get_selected_index(self):
        if self.selected is None:
            return 0

        return self.index(self.selected)


    def remove_selected(self):
        if self.selected is None:
            return

        sel = self.selected
        self.selected = None
        self.remove(sel)


    def save_selected(self):
        if self.selected is None:
            return

        sel = self.selected
        sel.backup_start_s = sel.start_s
        sel.backup_end_s   = sel.end_s


    def restore_selected(self):
        if self.selected is None:
            return

        sel = self.selected
        sel.start_s = sel.backup_start_s
        sel.end_s   = sel.backup_end_s


    def change_selected(self, start_s=None, end_s=None, is_fit=False, is_near=False):
        '''
        選択されているラベルの範囲を変更する。
        変更できる範囲：(１つ前のラベルの開始位置, １つ後のラベルの終了位置)
        カットラベルは他のラベルの終了位置とは重ならない

        @param is_fit  True なら隣接するラベルと重ならないように調整する。隣接するラベル範囲は変わらない。
        @param is_near True なら隣接するラベルと重ならないように調整する。隣接するラベル範囲も変わる可能性がある。
        '''

        if self.selected is None:
            return

        sel = self.selected

        if is_fit and is_near:
            is_near = False

        if start_s:
            prev_sel = self._get_prev_selected()

            if is_fit or sel.is_cut():
                # 前のラベルと重ならないようにする
                if prev_sel:
                    start_s = max(prev_sel.end_s, start_s)

            sel.start_s = max(0, min(start_s, sel.end_s - MIN_DUR_S))

            if is_near:
                # 前のラベルも重ならないように範囲を変更する
                if prev_sel and (abs(prev_sel.end_s - sel.start_s) < NEAR_S):
                    prev_sel.end_s = max(prev_sel.start_s + MIN_DUR_S, sel.start_s)

        if end_s:
            next_sel = self._get_next_selected()

            if next_sel:
                if is_fit or next_sel.is_cut():
                    # 後ろのラベルと重ならないようにする
                    end_s = min(end_s, next_sel.start_s)
                else:
                    # 後ろのラベルの終了位置と重ならないようにする
                    end_s = min(end_s, next_sel.end_s - 0.01)

            sel.end_s = max(end_s, sel.start_s + MIN_DUR_S)

            if is_near:
                # 後ろのラベルも重ならないように範囲を変更する
                if next_sel and (abs(sel.end_s - next_sel.start_s) < NEAR_S):
                    next_sel.start_s = min(next_sel.end_s - MIN_DUR_S, sel.end_s)


    #--------------------------------------------------------------------------
    # 内部メソッド

    def _load_from_list(self, lines):

        for line in lines:
            if line.startswith(ST_DISTINCTION):  # 特徴位置
                arr = line.split()
                if len(arr) == 3:
                    try:
                        self.distinction_s = float(arr[-1])
                    except:
                        pass
                continue

            m = label_re.search(line)

            if m is None:
                continue

            st = float(m.group(1))
            ed = float(m.group(3))
            lbl = m.group(5).strip()

            try:
                label = Label(st, ed, lbl)
            except:
                continue

            self.append(label)

        self._sort()

        self.clean_data()


    def _sort(self):
        '''
        終了位置順で並べ替え
        '''

        self.sort(key=lambda label: label.end_s)


    def _get_insertable_range(self, pos_s, dur_s, max_s):
        '''
        ラベルを挿入可能な範囲を取得する
        挿入できないなら None を返す
        '''

        if (pos_s < 0) or (max_s < pos_s) or (dur_s <= 0) or (max_s < dur_s):
            return None

        rng = [0, max_s]

        for label in self:
            if label.contains(pos_s):
                return None

            if label.end_s < pos_s:
                rng[0] = label.end_s

            if pos_s < label.start_s:
                rng[1] = label.start_s
                break

        if dur_s < rng[1] - rng[0]:
            return rng
        else:
            return None


    def _get_prev_selected(self):
        '''
        選択されているラベルの１つ前のラベルを返す
        '''

        if not self.selected:
            return None

        sel_i = self.index(self.selected)

        if 1 <= sel_i:
            prev_sel = self[sel_i - 1]
            return prev_sel

        return None

    def _get_next_selected(self):
        '''
        選択されているラベルの１つ後のラベルを返す
        '''

        if not self.selected:
            return None

        sel_i = self.index(self.selected)

        if sel_i < len(self) - 1:
            next_sel = self[sel_i + 1]
            return next_sel

        return None

