#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = ['insert_pause', 'FACTOR', 'MIN_FACTOR', 'MAX_FACTOR',
           'ADD_S', 'MIN_ADD_S', 'MAX_ADD_S']

import sys

from convtable import Conv_table
import pausewave
from labels import Labels


FACTOR = 1.0
MIN_FACTOR = 0.0
MAX_FACTOR = 3.00

ADD_S = 0.4
MIN_ADD_S = 0.0
MAX_ADD_S = 9.99

CHUNK_F = 4096


def usage(app):
    sys.stderr.write('Usage: %s source labels dest [factor] [add]\n\n' % app)
    sys.stderr.write(u'%.2f <= factor <= %.2f (default=%.2f)\n' %
                     (MIN_FACTOR, MAX_FACTOR, FACTOR))
    sys.stderr.write(u'%.2f <= add <= %.2f (default=%.2f)\n' %
                     (MIN_ADD_S, MAX_ADD_S, ADD_S))


def main():
    argc = len(sys.argv)

    if argc < 4 or 6 < argc:
        usage(sys.argv[0])
        sys.exit(1)

    factor = FACTOR
    add_s = ADD_S

    if argc >= 5:
        factor = float(sys.argv[4])

    if argc >= 6:
        add_s = float(sys.argv[5])

    src_file = sys.argv[1]
    labels_file = sys.argv[2]
    dst_file = sys.argv[3]

    insert_pause(src_file, dst_file, labels_file, factor, add_s)


def insert_pause(src_file, dst_file, labels_file, factor, add_s):
    in_snd = pausewave.open(src_file, 'rb')
    labels = Labels(labels_file)
    rate = in_snd.getframerate()
    nframes = in_snd.getnframes()
    tbl = Conv_table(labels, rate, nframes, factor, add_s)
    in_snd.settable(tbl)
    if src_file.endswith('.wav'):
        out_snd = pausewave.open(dst_file, 'wb', params=in_snd.getparams())
    else:
        out_snd = pausewave.open(dst_file, 'wb')

    data = in_snd.readframes(CHUNK_F)
    while len(data) > 0:
        out_snd.writeframes(data)
        data = in_snd.readframes(CHUNK_F)


if __name__ == '__main__':
    main()
