# -*- coding: utf-8 -*-

import re

MIN_DUR = 0.1  # ラベルの最小長さ
LBL_PAUSE = 'p'  # ポーズ挿入ラベル
LBL_CUT = 'x'  # 選択範囲カットラベル

NEAR_SEC = 0.1  # 近い隣接範囲を同時に動かすときに使用


class Label(object):
    def __init__(self, start, end, label=LBL_PAUSE):
        self.validate_time(start, end)
        self.validate_label(label)

        self._start = start
        self._end = end
        self._label = label

    def __str__(self):
        return '%.6f\t%.6f\t%s' % (self._start, self._end, self._label)

    def validate_time(self, start, end):
        if start > end:
            raise Exception('[Label] Error: start(%d) > end(%d)' %
                            (start, end))
        #elif end - start < MIN_DUR:
        #    raise Exception('[Label] Error: start(%d) - end(%d) < MIN_DUR(%d)'
        #                    % (start, end, MIN_DUR))

    def validate_label(self, label):
        if (label != LBL_PAUSE) and (label != LBL_CUT):
            raise Exception('[Label] Error: "%s" is not support label' %
                            label)

    def get_start(self):
        return self._start

    def set_start(self, start):
        self._start = max(0, min(start, self._end - MIN_DUR))

    start = property(get_start, set_start)

    def get_end(self):
        return self._end

    def set_end(self, end):
        self._end = max(self._start + MIN_DUR, end)

    end = property(get_end, set_end)

    def get_label(self):
        return self._label

    def set_label(self, label):
        self.validate_label(label)
        self._label = label

    label = property(get_label, set_label)


class Labels(list):
    def __init__(self, lines=None):
        if not lines:
            lines = []

        self.selected = None
        r = re.compile(r'^(\d+(\.\d{0,6})?)\s+(\d+(\.\d{0,6})?)\s+(.*)')

        for line in lines:
            m = r.search(line)
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

        self.sort(key=lambda label: label.end)

        self.clean_data()

    # LBL_CUTのラベルが他のラベルと重ならないように修正する
    def clean_data(self):
        if 1 <= len(self):
            prev_label = self[0]

        for label in self[1:]:
            if label.start < prev_label.end:
                if label.label == LBL_CUT:
                    label.start = prev_label.end

            prev_label = label

    def __str__(self):
        return '\n'.join([str(label) for label in self])

    def write(self, file_name):
        self.sort(key=lambda label: label.end)

        f = open(file_name, 'w')
        f.write(str(self))
        f.close()

    # 指定した位置（秒）のラベルを選択する
    # 重なっている場合はサイクリックに選択する
    def select(self, sec):
        found_labels = []
        for label in self:
            if (label.start <= sec) and (sec <= label.end):
                found_labels.append(label)

        if 1 == len(found_labels):
            self.selected = found_labels[0]
        elif 1 < len(found_labels):
            if self.selected is None:
                self.selected = found_labels[0]
            elif self.selected not in found_labels:
                self.selected = found_labels[0]
            else:
                i = found_labels.index(self.selected) + 1
                if i == len(found_labels):
                    i = 0
                self.selected = found_labels[i]

    def insert_label(self, pos, dur, max_s):
        if (pos < 0) or (max_s < pos):
            return

        prev_s = 0
        next_s = max_s

        for label in self:
            if (label.start <= pos) and (pos <= label.end):
                return

            if label.end < pos:
                prev_s = label.end

            if (pos < label.start) and (label.start < next_s):
                next_s = label.start

        if dur < next_s - prev_s:
            if pos - prev_s < dur / 2:
                start = prev_s
                end = start + dur
            elif next_s - pos < dur / 2:
                end = next_s
                start = end - dur
            else:
                start = pos - (dur / 2)
                end = start + dur

            self.append(Label(start, end))
            self.sort(key=lambda label: label.end)

    def can_insert_label(self, pos, dur, max_s):
        if (pos < 0) or (max_s < pos):
            return False

        prev_s = 0
        next_s = max_s

        for label in self:
            if (label.start <= pos) and (pos <= label.end):
                return False

            if label.end < pos:
                prev_s = label.end

            if (pos < label.start) and (label.start < next_s):
                next_s = label.start

        if dur < next_s - prev_s:
            return True
        else:
            return False

    def remove_sel(self):
        if not self.selected:
            return

        sel = self.selected
        self.selected = None
        self.remove(sel)

    def save_sel(self):
        if not self.selected:
            return

        sel = self.selected
        sel.prev_start = sel.start
        sel.prev_end = sel.end

    def restore_sel(self):
        if not self.selected:
            return

        sel = self.selected
        sel.start = sel.prev_start
        sel.end = sel.prev_end

    def change_sel(self, start, end=None, fit=False, near=False):
        if not self.selected:
            return

        sel = self.selected

        if fit and near:
            near = False

        if start:
            prev_sel = self.get_prev_sel()

            if fit or (sel.label == LBL_CUT):
                start = max(start, min(prev_sel.end, sel.end))
            sel.start = min(start, sel.end - MIN_DUR)

            if near and (abs(prev_sel.end - sel.start) < NEAR_SEC):
                prev_sel.end = max(prev_sel.start + MIN_DUR, sel.start)

        if end:
            next_sel = self.get_next_sel()

            if next_sel and (fit or (next_sel.label == LBL_CUT)):
                end = max(sel.start, min(end, next_sel.start))
            elif next_sel:
                end = max(sel.start, min(end, next_sel.end - 0.01))
            sel.end = max(end, sel.start + MIN_DUR)

            if next_sel and near and \
                    (abs(sel.end - next_sel.start) < NEAR_SEC):
                next_sel.start = min(next_sel.end - MIN_DUR, sel.end)

    def can_cut(self, sec):
        for label in self:
            if (label.start < sec) and (sec < label.end):
                return True
        return False

    def cut(self, sec):
        cut_i = -1
        new_label = None

        for i, label in enumerate(self):
            if (label.start < sec) and (sec < label.end):
                cut_i = i
                new_label = Label(sec, label.end)
                label.end = sec
                break

        if cut_i != -1:
            self.insert(cut_i + 1, new_label)

    def can_merge_left(self):
        if self.get_prev_sel():
            return True
        else:
            return False

    def merge_left(self):
        prev_sel = self.get_prev_sel()
        if prev_sel:
            prev_sel.end = self.selected.end
            self.remove(self.selected)
            self.selected = prev_sel

    def can_merge_right(self):
        if self.get_next_sel():
            return True
        else:
            return False

    def merge_right(self):
        next_sel = self.get_next_sel()
        if next_sel:
            self.selected.end = next_sel.end
            self.remove(next_sel)

    def get_prev_sel(self):
        if not self.selected:
            return None

        sel_i = self.index(self.selected)

        if 1 <= sel_i:
            prev_sel = self[sel_i - 1]
            return prev_sel

        return None

    def get_next_sel(self):
        if not self.selected:
            return None

        sel_i = self.index(self.selected)

        if sel_i < len(self) - 1:
            next_sel = self[sel_i + 1]
            return next_sel

        return None

    def get_overlapped(self, label):
        overlapped = []

        for lbl in self:
            if (label is not lbl):
                if (label.start < lbl.start and lbl.start < label.end) or \
                        (label.start < lbl.end and lbl.end < label.end) or \
                        (lbl.start < label.start and label.end < lbl.end):
                    overlapped.append(lbl)

        return overlapped

    def subtract(self):
        if len(self) == 0:
            return

        prev = self[0]

        for label in self[1:]:
            if (prev.start < label.start) and (label.start < prev.end):
                label.start = prev.end
            elif (label.start < prev.start) and (prev.end < label.end):
                label.start = prev.end

            prev = label

    def is_sorted(self):
        if len(self) == 0:
            return True

        prev = self[0]

        for label in self[1:]:
            if prev.end > label.end:
                return False
            prev = label

        return True
