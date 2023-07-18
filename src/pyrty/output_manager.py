from enum import Enum


class RawOutput(Enum):
    CSV = 'csv'
    NONE = None

    
class Output(Enum):
    DF = 'df'
    NONE = None

    
class StdOut: ...