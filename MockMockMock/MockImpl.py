from MockException import MockException
from SimpleExpectation import *
from ExpectationGrouping import *

class Expecter:
    def __init__( self, mock ):
        self.__mock = mock

    def __getattr__( self, name ):
        # Note that accepting name == "__call__" allows the mock object to be callable with no specific code
        if name == "__dir__":
            raise AttributeError()
        expectation = Expectation( self.__mock.name + "." + name )
        self.__mock.addExpectation( expectation )
        return ExpectationProxy( expectation )

class CallChecker:
    def __init__( self, mock, expectations ):
        self.__expectations = expectations
        self.__mock = mock

    def __call__( self, *args, **kwds ):
        for expectation in self.__expectations:
            if expectation.callPolicy.checkCall( args, kwds ):
                self.__mock.removeExpectation( expectation )
                return expectation.action()
        else:
            raise MockException( self.__expectations[ 0 ].name + " called with bad arguments" )

class Checker:
    def __init__( self, mock ):
        self.__mock = mock

    def __getattr__( self, name ):
        if name == "__dir__":
            raise AttributeError()
        calledName = self.__mock.name + "." + name
        expectations = self.__mock.getCurrentPossibleExpectations()

        goodNamedExpectations = []
        allGoodNamedExpectationsExpectCall = True
        allGoodNamedExpectationsExpectNoCall = True

        for expectation in expectations:
            if expectation.name == calledName:
                goodNamedExpectations.append( expectation )
                if expectation.callPolicy.expectsCall:
                    allGoodNamedExpectationsExpectNoCall = False
                else:
                    allGoodNamedExpectationsExpectCall = False

        if len( goodNamedExpectations ) == 0:
            raise MockException( calledName + " called instead of " + " or ".join( e.name for e in expectations ) )

        if allGoodNamedExpectationsExpectCall:
            return CallChecker( self.__mock, goodNamedExpectations )
        elif allGoodNamedExpectationsExpectNoCall:
            expectation = goodNamedExpectations[ 0 ]
            self.__mock.removeExpectation( expectation )
            return expectation.action()
        else:
            raise MockException( calledName + " is expected as a property and as a method call in an unordered group" )

class MockEngine( object ):
    def __init__( self ):
        self.__expectationGroups = [ OrderedExpectationGroup() ]

    def addExpectation( self, expectation ):
        self.__expectationGroups[ -1 ].addExpectation( expectation )

    def getCurrentPossibleExpectations( self ):
        return self.__singleGroup.getCurrentPossibleExpectations()

    def removeExpectation( self, expectation ):
        self.__singleGroup.removeExpectation( expectation )

    @property
    def __singleGroup( self ):
        assert( len( self.__expectationGroups ) == 1 )
        return self.__expectationGroups[ 0 ]
            
    def tearDown( self ):
        requiredCalls = self.__singleGroup.requiredCalls()
        if len( requiredCalls ) > 0:
            raise MockException( ", ".join( e.name for e in requiredCalls ) + " not called" )

    def startUnorderedGroup( self ):
        group = UnorderedExpectationGroup()
        self.addExpectation( group )
        self.__expectationGroups.append( group )

    def startOrderedGroup( self ):
        group = OrderedExpectationGroup()
        self.addExpectation( group )
        self.__expectationGroups.append( group )

    def startFacultativeGroup( self ):
        group = FacultativeExpectationGroup()
        self.addExpectation( group )
        self.__expectationGroups.append( group )

    def popGroup( self ):
        self.__expectationGroups.pop()

class StackPoper:
    def __init__( self, mock ):
        self.__mock = mock

    def __enter__( self ):
        pass
        
    def __exit__( self, a, b, c ):
        self.__mock.popExpectationStack()

class MockImpl( object ):
    def __init__( self, name, brotherMock ):
        if brotherMock is None:
            self.__engine = MockEngine()
        else:
            self.__engine = brotherMock.__engine
        self.name = name

    def addExpectation( self, expectation ):
        self.__engine.addExpectation( expectation )

    def getCurrentPossibleExpectations( self ):
        return self.__engine.getCurrentPossibleExpectations()

    def removeExpectation( self, expectation ):
        self.__engine.removeExpectation( expectation )

    def expect( self ):
        return Expecter( self )

    def object( self ):
        return Checker( self )

    def unordered( self ):
        self.__engine.startUnorderedGroup()
        return StackPoper( self )

    def ordered( self ):
        self.__engine.startOrderedGroup()
        return StackPoper( self )

    def atomic( self ):
        self.__engine.startOrderedGroup()
        return StackPoper( self )

    def facultative( self ):
        self.__engine.startFacultativeGroup()
        return StackPoper( self )

    def popExpectationStack( self ):
        self.__engine.popGroup()
        pass

    def tearDown( self ):
        self.__engine.tearDown()
