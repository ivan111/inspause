# -*- coding: utf-8 -*-
'''
ラベル管理

ラベルの変更を元に戻せるように管理する
'''

import copy


class LabelsManager(object):
    def __init__(self, labels):
        self.i = 0
        self.labels_list = [labels]

    def __str__(self):
        result = 'Current Index : %d\n\n' % self.i

        for i, labels in enumerate(self.labels_list):
            result = result + 'Item : %d\n' % i
            result = result + labels.__str__()
            result = result + '\n'

        return result

    def __call__(self):
        return self.labels

    #--------------------------------------------------------------------------
    # コマンド

    def save(self):
        if self.i + 1 < len(self.labels_list):
            del self.labels_list[self.i + 1:]
        labels = copy.deepcopy(self.labels)
        self.labels_list.append(labels)
        self.i = self.i + 1

    def clear_history(self):
        labels = self.labels
        self.i = 0
        self.labels_list = [labels]

    def restore(self):
        if 0 < self.i:
            self.labels_list.pop(self.i)
            self.i = self.i - 1

    def undo(self):
        self.i = max(0, self.i - 1)

    def can_undo(self):
        return self.i != 0

    def redo(self):
        self.i = min(self.i + 1, len(self.labels_list))

    def can_redo(self):
        return self.i != len(self.labels_list) - 1

    #--------------------------------------------------------------------------
    # プロパティ

    # ---- ラベル

    @property
    def labels(self):
        return self.labels_list[self.i]

    @labels.setter
    def labels(self, labels):
        self.labels_list[self.i] = labels
