class TitanicException(Exception):
    """Base exception handler for titanic related errors"""

class TitanicConnectionException(TitanicException):
    """Exception to raise when failing to make http connect
    to external sources
    """

class TitanicInvalidArgumentException(TitanicException):
    """Exception to raise when given invalid arguments from user"""

class TitanicBuildnameException(TitanicInvalidArgumentException):
    """Exception to raise when given invalid build name"""

class TitanicRevisionException(TitanicInvalidArgumentException):
    """Exception to raise when given a build range that is invalid"""

class TitanicBuildException(TitanicInvalidArgumentException):
    """Exception to raise when given a build range that is invalid"""
