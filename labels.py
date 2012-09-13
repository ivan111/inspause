import re

MIN_DUR = 0.2
LBL_PAUSE = 'p'
LBL_CUT = 'x'

class Label:
    def __init__(self, start, end, label=LBL_PAUSE):
        if start > end:
            raise Exception('[Label]error: start > end')
        self.start = start
        self.end = end
        self.label = label

class Labels(list):
    def __init__(self, lines=None):
        if not lines:
            lines = []

        self.selected = None
        r = re.compile(r'^(\d+\.?\d*)\s+(\d+\.?\d*)\s+(.*)')

        for line in lines:
            m = r.search(line)
            if m is None:
                continue
            st = float(m.group(1))
            ed = float(m.group(2))
            label = m.group(3)
            if label != LBL_PAUSE and label != LBL_CUT:
                label = LBL_PAUSE
            self.append(Label(st, ed, label))

        self.sort(key=lambda label: label.end)

        self.clean_data()

    def clean_data(self):
        if 1 <= len(self):
            prev_label = self[0]

        for label in self[1:]:
            if label.start < prev_label.end:
                if label.label == LBL_CUT:
                    label.start = prev_label.end

            prev_label = label

    def write(self, file_name):
        self.sort(key=lambda label: label.end)

        f = open(file_name, 'w')

        for label in self:
            f.write('%.6f\t%.6f\t%s\n' % (label.start, label.end, label.label))

        f.close()

    def __str__(self):
        result = ''

        for label in self:
            result = result + '%.6f\t%.6f\t%s\n' % (label.start, label.end, label.label)

        return result

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
                i = found_labels.index(self.selected)
                if i+1 == len(found_labels):
                    i = -1
                self.selected = found_labels[i+1]

    def insert_label(self, pos, dur, max_s):
        if (pos < 0) or (max_s < pos):
            return

        prev_s = 0
        next_s = max_s

        for label in  self:
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

        for label in  self:
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

    def change_sel(self, start, end=None):
        if not self.selected:
            return

        if start:
            prev_sel = self.get_prev_sel()
            if self.selected.label == LBL_CUT:
                start = max(start, min(prev_sel.end, self.selected.end))
            self.selected.start = min(start, self.selected.end - MIN_DUR)

        if end:
            next_sel = self.get_next_sel()
            if next_sel and next_sel.label == LBL_CUT:
                end = max(self.selected.start, min(end, next_sel.start))
            elif next_sel:
                end = max(self.selected.start, min(end, next_sel.end))
            self.selected.end = max(end, self.selected.start + MIN_DUR)

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
            self.insert(cut_i+1, new_label)

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



