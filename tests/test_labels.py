#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import unittest

sys.path.append('..')

from labels import *


LABELS_FILE = 'data/labels_test.txt'


class LabelsTestCase(unittest.TestCase):

    def setUp(self):
        self.lines = open(LABELS_FILE, 'r').readlines()
        self.lbls = Labels(self.lines)

    def tearDown(self):
        pass

    def test_init(self):
        self.assertEqual(3, len(self.lbls))
        self.assertEqual(self.lbls.dist_s, 1.0)
        self.assertEqual(self.lbls[0].end_s, 1.0)
        self.assertEqual(self.lbls[1].end_s, 3.0)
        self.assertEqual(self.lbls[2].end_s, 7.950521)

    def test_get_insertable_range(self):
        res = self.lbls._get_insertable_range(2.5, 0.5, 100.0)
        self.assertIsNone(res)

        res = self.lbls._get_insertable_range(1.5, 1.0, 100.0)
        self.assertEqual(res[0], 1.0)
        self.assertEqual(res[1], 2.0)

        res = self.lbls._get_insertable_range(1.5, 1.00001, 100.0)
        self.assertIsNone(res)

        res = self.lbls._get_insertable_range(100.5, 1.0, 100.0)
        self.assertIsNone(res)

        res = self.lbls._get_insertable_range(1.5, 100.5, 100.0)
        self.assertIsNone(res)

        res = self.lbls._get_insertable_range(1.5, -1.0, 100.0)
        self.assertIsNone(res)

        res = self.lbls._get_insertable_range(0.4, 0.4, 100.0)
        self.assertEqual(res[0], 0.0)
        self.assertEqual(res[1], 0.5)

        res = self.lbls._get_insertable_range(10, 1.0, 100.0)
        self.assertEqual(res[0], 7.950521)
        self.assertEqual(res[1], 100.0)

    def test_insert_label(self):
        self.lbls.insert_label(0.4, 0.4, 10.0)
        self.assertAlmostEqual(self.lbls[0].start_s, 0.1)
        self.assertEqual(self.lbls[0].end_s, 0.5)
        self.assertEqual(self.lbls[0].label, 'p')

        self.lbls.insert_label(3.5, 0.5, 10.0)
        self.assertEqual(self.lbls[3].start_s, 3.5 - 0.25)
        self.assertEqual(self.lbls[3].end_s, 3.5 + 0.25)

    def test_can_cut(self):
        res = self.lbls.can_cut(2.5)
        self.assertTrue(res)

        res = self.lbls.can_cut(2.01)
        self.assertFalse(res)

        res = self.lbls.can_cut(2.99)
        self.assertFalse(res)

    def test_cut(self):
        self.lbls.cut(2.5)
        self.assertEqual(self.lbls[1].start_s, 2.0)
        self.assertEqual(self.lbls[1].end_s, 2.5)
        self.assertEqual(self.lbls[2].start_s, 2.5)
        self.assertEqual(self.lbls[2].end_s, 3.0)


if __name__ == '__main__':
    unittest.main()
