#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

from test_label import LabelTestCase
from test_labels import LabelsTestCase

test_cases = [
        LabelTestCase,
        LabelsTestCase,
        ]

def suite():
    suite = unittest.TestSuite()
    for test_case in test_cases:
        suite.addTests(unittest.makeSuite(test_case))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')

