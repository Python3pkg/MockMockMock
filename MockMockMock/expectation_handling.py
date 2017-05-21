# coding: utf8

# Copyright 2013-2015 Vincent Jacques <vincent@vincent-jacques.net>

import MockMockMock
from . import arguments_checking
import collections


class Expectation(object):
    def __init__(self, name):
        self.name = name
        self.__checker = None
        self.__action = lambda: None

    # expect
    def expect_call(self, checker):
        self.__checker = checker

    def set_action(self, action):
        self.__action = action

    # check
    def checkName(self, name):
        return self.name == name

    def expectsCall(self):
        return self.__checker is not None

    def checkCall(self, args, kwds):
        return self.__checker(args, kwds)

    # call
    def call(self):
        return self.__action()


class AnyAttribute:
    def __init__(self, apply):
        self.__apply = apply

    def __getattr__(self, name):
        # @todo Fix this hack
        # Hack to allow m.expect._call_.with_arguments,
        # because m.expect.__call__.with_arguments fails,
        # because function doesn't have attribute "with_arguments"
        if name == "_call_":
            name = "__call__"
        # End of hack
        if name == "__dir__":
            raise AttributeError()
        return self.__apply(name)

    def __call__(self, *args, **kwds):  # Needed to make isinstance(mock.expect, collections.Callable) return True
        return self.__getattr__("__call__")(*args, **kwds)


class CallChecker:
    def __init__(self, handler, expectations):
        self.__handler = handler
        self.__expectations = expectations

    def __call__(self, *args, **kwds):
        return self.__handler.checkExpectationCall(self.__expectations, args, kwds)


class BasicExpectationProxy:
    def __init__(self, expectation):
        self.__expectation = expectation

    def and_return(self, value):
        self.__expectation.set_action(lambda: value)

    def and_raise(self, exception):
        def Raise():
            raise exception
        self.__expectation.set_action(Raise)

    def and_execute(self, action):
        self.__expectation.set_action(action)


class CallableExpectationProxy(BasicExpectationProxy):
    def __init__(self, expectation):
        BasicExpectationProxy.__init__(self, expectation)
        self.__expectation = expectation

    def __call__(self, *args, **kwds):
        return self.with_arguments(arguments_checking.Equality(args, kwds))

    def with_arguments(self, checker):
        self.__expectation.expect_call(checker)
        return BasicExpectationProxy(self.__expectation)


class CallRecorder:
    def __init__(self, handler, mockName, attrName, realObject):
        self.__handler = handler
        self.__mockName = mockName
        self.__attrName = attrName
        self.__realObject = realObject

    def __call__(self, *args, **kwds):
        try:
            ret = self.__realObject(*args, **kwds)
            self.__handler.addRecordedCall({
                "object": self.__mockName,
                "attribute": self.__attrName,
                "arguments": args,
                "keywords": kwds,
                "return": ret,
            })
            return ret
        except Exception as e:
            self.__handler.addRecordedCall({
                "object": self.__mockName,
                "attribute": self.__attrName,
                "arguments": args,
                "keywords": kwds,
                "exception": e,
            })
            raise


class ExpectationHandler(object):
    def __init__(self, initialGroup):
        self.__currentGroup = initialGroup
        self.__recordedCalls = []
        self.__objects = {}

    # expect
    def expect(self, mockName):
        return AnyAttribute(lambda attrName: self.addExpectation(mockName + "." + attrName))

    def addExpectation(self, name):
        # Note that accepting name == "__call__" allows the mock object to be callable with no specific code
        expectation = Expectation(name)
        self.__currentGroup.addExpectation(expectation)
        return CallableExpectationProxy(expectation)

    def push_group(self, group):
        self.__currentGroup.addGroup(group)
        self.__currentGroup = group
        return self.StackPoper(self)

    class StackPoper:
        def __init__(self, handler):
            self.__handler = handler

        def __enter__(self):
            pass

        def __exit__(self, *ignored):
            self.__handler.popGroup()

    def popGroup(self):
        self.__currentGroup = self.__currentGroup.parent

    # call
    def object(self, mockName):
        # @todo Test this objects cache. It's important because it gives the same *identity* to all calls to mock.object
        # @todo Detect if client tries to create several mocks with same name
        # @todo Handle use case where mock.expect(another_mock.object) ends up with another_mock being printed as hint of what was not called (currently another_mock.__repr__ called instead of...)
        o = self.__objects.get(mockName)
        if o is None:
            o = AnyAttribute(lambda attrName: self.checkExpectation(mockName + "." + attrName))
            self.__objects[mockName] = o
        return o

    def checkExpectation(self, calledName):
        possibleExpectations = self.__currentGroup.getCurrentPossibleExpectations()
        goodNamedExpectations = [expectation for expectation in possibleExpectations if expectation.checkName(calledName)]

        if len(goodNamedExpectations) == 0:
            # @todo if possibleExpectations is empty, adapt message
            # @todo display arguments
            raise MockMockMock.MockException(calledName + " called instead of " + " or ".join(e.name for e in possibleExpectations))

        allGoodNamedExpectationsExpectNoCall = not any(expectation.expectsCall() for expectation in goodNamedExpectations)
        allGoodNamedExpectationsExpectCall = all(expectation.expectsCall() for expectation in goodNamedExpectations)

        if allGoodNamedExpectationsExpectCall:
            return CallChecker(self, goodNamedExpectations)
        elif allGoodNamedExpectationsExpectNoCall:
            return self.__callExpectation(goodNamedExpectations[0])
        else:
            raise MockMockMock.MockException(calledName + " is expected as a property and as a method call in an unordered group")

    def checkExpectationCall(self, expectations, args, kwds):
        for expectation in expectations:
            if expectation.checkCall(args, kwds):
                return self.__callExpectation(expectation)
        raise MockMockMock.MockException(expectations[0].name + " called with bad arguments " + str(args) + " " + str(kwds))

    def __callExpectation(self, expectation):
        returnValue, self.__currentGroup = expectation.call()
        return returnValue

    def tearDown(self):
        if self.__currentGroup.requiresMoreCalls():
            raise MockMockMock.MockException(" or ".join(self.__currentGroup.getRequiredCallsExamples()) + " not called")

    # record / replay
    def record(self, mockName, realObject):
        return AnyAttribute(lambda attrName: self.recordCall(realObject, mockName, attrName))

    def recordCall(self, realObject, mockName, attrName):
        try:
            attr = getattr(realObject, attrName)
            if isinstance(attr, collections.Callable):
                return CallRecorder(self, mockName, attrName, attr)
            else:
                self.addRecordedCall({
                    "object": mockName,
                    "attribute": attrName,
                    "return": attr,
                })
                return attr
        except Exception as e:
            self.addRecordedCall({
                "object": mockName,
                "attribute": attrName,
                "exception": e,
            })
            raise

    def addRecordedCall(self, call):
        self.__recordedCalls.append(call)

    def get_recorded_calls(self):
        return self.__recordedCalls
