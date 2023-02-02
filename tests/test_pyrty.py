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

def test_susie():
    susie_code = [
        "set.seed(1)",
        "n <- 1000",
        "p <- 1000",
        "beta <- rep(0, p)",
        "beta[c(1, 2, 300, 400)] <- 1",
        "X <- matrix(rnorm(n*p), nrow=n, ncol=p)",
        "y <- X %*% beta + rnorm(n)",
        "res <- susie(X, y, L=10)",
        "res <- coef(res)[-1]",
    ]
    test_susie = PyRFunc("test_susie",
                         code=susie_code,
                         ret="res",
                         libraries=["susieR", "janitor"],
                         pkgs=["r-susier", "r-janitor"]
                         )
    res_df = test_susie()
    assert res_df is not None
    
def test_tcgabiolinks():
    tcgabiolinks_code = ["subtypes <- PanCancerAtlas_subtypes()"]
    test_tcgabiolinks = PyRFunc("test_tcgabiolinks",
                                code=tcgabiolinks_code,
                                ret="subtypes",
                                libraries=["TCGAbiolinks"],
                                pkgs=["bioconductor-tcgabiolinks"]
                                )
    subtypes_df = test_tcgabiolinks()
    assert subtypes_df is not None