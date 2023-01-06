import pytest

from pyrty.pyrty import PyRFunc

__author__ = "t-silvers"
__copyright__ = "t-silvers"
__license__ = "MIT"


def test_pyrty():
    test_code = [
        "", 
        "set.seed(1)",
        "n <- 1000",
        "p <- 1000",
        "beta <- rep(0, p)",
        "beta[c(1, 2, 300, 400)] <- 1",
        "X <- matrix(rnorm(n*p), nrow=n, ncol=p)",
    ]
    test_func = PyRFunc("test", code=test_code, ret="X")
    X_df = test_func()
    assert X_df.shape == (1000, 1000)