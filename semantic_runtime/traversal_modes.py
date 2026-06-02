from enum import Enum

class TraversalMode(Enum):

    RUNTIME_SPINE = "RUNTIME_SPINE"

    IMPLEMENTATION_DESCENT = (
        "IMPLEMENTATION_DESCENT"
    )

    FULL_BRANCH_EXPANSION = (
        "FULL_BRANCH_EXPANSION"
    )

    DISPATCH_ANALYSIS = (
        "DISPATCH_ANALYSIS"
    )