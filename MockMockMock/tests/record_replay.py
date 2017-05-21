# coding: utf8

# Copyright 2013-2015 Vincent Jacques <vincent@vincent-jacques.net>

import unittest

import MockMockMock


# This could be replaced by a mock :-D. But hum, keep it simple.
class TestDependency:
    the_exception = Exception("ga", "bu")

    def __init__(self):
        self.instance_property = 49

    class_property = 48

    @property
    def property_from_getter(self):
        return 50

    @property
    def raising_property(self):
        raise self.the_exception

    def instance_method(self, x, y, *args, **kwds):
        return str((x, y, args, sorted(kwds.items())))

    @classmethod
    def class_method(cls, x, y):
        return (y, x, "foo")

    @staticmethod
    def static_method(x, y):
        return (y, x, "bar")

    def __call__(self, x, y):
        return (y, x, "baz")

    def raise_exception(self, *args, **kwds):
        raise self.the_exception


class RecordTestCase(unittest.TestCase):
    def setUp(self):
        super(RecordTestCase, self).setUp()
        self.mocks = MockMockMock.Engine()
        mock = self.mocks.create("dependency")
        self.recorded = mock.record(TestDependency())

    def test_instance_method(self):
        self.assertEqual(
            self.recorded.instance_method(42, 43, 44, 45, toto=46, tutu=47),
            "(42, 43, (44, 45), [('toto', 46), ('tutu', 47)])"
        )
        self.assertEqual(
            self.mocks.records,
            [
                {
                    "object": "dependency",
                    "attribute": "instance_method",
                    "arguments": (42, 43, 44, 45),
                    "keywords": dict(toto=46, tutu=47),
                    "return": "(42, 43, (44, 45), [('toto', 46), ('tutu', 47)])",
                }
            ]
        )

    def test_class_method(self):
        self.assertEqual(self.recorded.class_method(42, y=43), (43, 42, "foo"))
        self.assertEqual(
            self.mocks.records,
            [
                {
                    "object": "dependency",
                    "attribute": "class_method",
                    "arguments": (42, ),
                    "keywords": dict(y=43),
                    "return": (43, 42, "foo"),
                }
            ]
        )

    def test_static_method(self):
        self.assertEqual(self.recorded.static_method(42, y=43), (43, 42, "bar"))
        self.assertEqual(
            self.mocks.records,
            [
                {
                    "object": "dependency",
                    "attribute": "static_method",
                    "arguments": (42, ),
                    "keywords": dict(y=43),
                    "return": (43, 42, "bar"),
                }
            ]
        )

    def test_call_object(self):
        self.assertEqual(self.recorded(42, y=43), (43, 42, "baz"))
        self.assertEqual(
            self.mocks.records,
            [
                {
                    "object": "dependency",
                    "attribute": "__call__",
                    "arguments": (42, ),
                    "keywords": dict(y=43),
                    "return": (43, 42, "baz"),
                }
            ]
        )

    def test_class_property(self):
        self.assertEqual(self.recorded.class_property, 48)
        self.assertEqual(
            self.mocks.records,
            [
                {
                    "object": "dependency",
                    "attribute": "class_property",
                    "return": 48,
                }
            ]
        )

    def test_instance_property(self):
        self.assertEqual(self.recorded.instance_property, 49)
        self.assertEqual(
            self.mocks.records,
            [
                {
                    "object": "dependency",
                    "attribute": "instance_property",
                    "return": 49,
                }
            ]
        )

    def test_property_from_getter(self):
        self.assertEqual(self.recorded.property_from_getter, 50)
        self.assertEqual(
            self.mocks.records,
            [
                {
                    "object": "dependency",
                    "attribute": "property_from_getter",
                    "return": 50,
                }
            ]
        )

    def test_exception_in_method(self):
        with self.assertRaises(Exception) as cm:
            self.recorded.raise_exception(42, 43, z=45)
        self.assertIs(cm.exception, TestDependency.the_exception)
        self.assertEqual(
            self.mocks.records,
            [
                {
                    "object": "dependency",
                    "attribute": "raise_exception",
                    "arguments": (42, 43),
                    "keywords": {"z": 45},
                    "exception": TestDependency.the_exception,
                }
            ]
        )

    def test_exception_in_property(self):
        with self.assertRaises(Exception) as cm:
            self.recorded.raising_property
        self.assertIs(cm.exception, TestDependency.the_exception)
        self.assertEqual(
            self.mocks.records,
            [
                {
                    "object": "dependency",
                    "attribute": "raising_property",
                    "exception": TestDependency.the_exception,
                }
            ]
        )

    def test_several_records(self):
        self.recorded.instance_property
        self.recorded.instance_method(1, 2, 3)
        self.assertEqual(
            self.mocks.records,
            [
                {
                    "object": "dependency",
                    "attribute": "instance_property",
                    "return": 49,
                },
                {
                    "object": "dependency",
                    "attribute": "instance_method",
                    "arguments": (1, 2, 3),
                    "keywords": {},
                    "return": "(1, 2, (3,), [])",
                },
            ]
        )
