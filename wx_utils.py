# -*- coding: utf-8 -*-

# Module: wx_utils.py
# Author: Noboru Irieda(Handle Name NoboNobo)
# 必要ないのを削除やコードスタイルを少し変更: vanya

from wx.xrc import XRCID, XRCCTRL


class ImmutableDict(dict):
    '''A hashable dict.'''

    def __init__(self, *args, **kwds):
        dict.__init__(self, *args, **kwds)

    def __setitem__(self, key, value):
        raise NotImplementedError('dict is immutable')

    def __delitem__(self, key):
        raise NotImplementedError('dict is immutable')

    def clear(self):
        raise NotImplementedError('dict is immutable')

    def setdefault(self, k, default=None):
        raise NotImplementedError('dict is immutable')

    def popitem(self):
        raise NotImplementedError('dict is immutable')

    def update(self, other):
        raise NotImplementedError('dict is immutable')

    def __hash__(self):
        return hash(tuple(self.iteritems()))


class bind_manager:
    binds = {}
    parents = {}

    def __init__(self):
        self.bind = set()
        self.parent = None

    def __call__(self, *args, **keys):
        def deco(func):
            self.bind.add((func.func_name, args, ImmutableDict(keys)))
            return func

        return deco

    def bindall(self, obj):
        for func_name, args, keys in self.bind:
            keys = dict(keys)

            if 'event' in keys:
                event = keys['event']
                del keys['event']
            else:
                event = args[0]
                args = list(args[1:])

            parent = self.parent or obj
            control = parent

            if 'id' in keys:
                if isinstance(keys['id'], str):
                    keys['id'] = XRCID(keys['id'])

            if 'control' in keys:
                control = keys['control']
                if isinstance(control, str):
                    control = XRCCTRL(parent, control)
                del keys['control']

            control.Bind(event, getattr(obj, func_name), *args, **keys)

    @property
    def bind(self):
        return self.binds[hash(self)]

    @bind.setter
    def bind(self, bind):
        self.binds[hash(self)] = bind

    @property
    def parent(self):
        return self.parents[hash(self)]

    @parent.setter
    def parent(self, parent):
        print parent
        self.parents[hash(self)] = parent
