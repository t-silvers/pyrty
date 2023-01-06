.. These are examples of badges you might want to add to your README:
   please update the URLs accordingly

    .. image:: https://api.cirrus-ci.com/github/<USER>/pyrty.svg?branch=main
        :alt: Built Status
        :target: https://cirrus-ci.com/github/<USER>/pyrty
    .. image:: https://readthedocs.org/projects/pyrty/badge/?version=latest
        :alt: ReadTheDocs
        :target: https://pyrty.readthedocs.io/en/stable/
    .. image:: https://img.shields.io/coveralls/github/<USER>/pyrty/main.svg
        :alt: Coveralls
        :target: https://coveralls.io/r/<USER>/pyrty
    .. image:: https://img.shields.io/pypi/v/pyrty.svg
        :alt: PyPI-Server
        :target: https://pypi.org/project/pyrty/
    .. image:: https://img.shields.io/conda/vn/conda-forge/pyrty.svg
        :alt: Conda-Forge
        :target: https://anaconda.org/conda-forge/pyrty
    .. image:: https://pepy.tech/badge/pyrty/month
        :alt: Monthly Downloads
        :target: https://pepy.tech/project/pyrty
    .. image:: https://img.shields.io/twitter/url/http/shields.io.svg?style=social&label=Twitter
        :alt: Twitter
        :target: https://twitter.com/pyrty

.. image:: https://img.shields.io/badge/-PyScaffold-005CA0?logo=pyscaffold
    :alt: Project generated with PyScaffold
    :target: https://pyscaffold.org/

|

=====
pyrty
=====


    Use R snippets in python code. Let conda manage your R dependencies.


Use simple R snippets or scripts in your python code. Works best when R code accepts a dataframe and returns a dataframe or nothing. Let conda/mamba manage R dependencies outside of your current environment.

For a more powerful alternative, consider using `rpy2`_.


=====
Examples
=====

Porting the `“Sum of Single Effects” (SuSiE) model`_ to python

.. code-block:: python

    import numpy as np
    import pandas as pd
    import pyrty
    from sklearn.datasets import make_regression

    # (1) Create a python susie function
    # ----------------------------------
    # Can write code here as list or in a separate file.
    # If you want to use a separate file, use instead e.g.,
    # `pyrty.PyRFunc("susie.R", code=None, ...)` and pyrty 
    # will look for a file called `susie.R` in the current directory.
    # User is responsible for making sure the file exists and
    # contains valid R code for `pyrty.PyRFunc`.
    susie_code = [
        "set.seed(1)",
        "X <- as.matrix(read_csv(opt$X))",
        "y <- as.matrix(read_csv(opt$y))",
        "fit <- susieR::susie(X, y)",
        "ix <- c(1, unlist(fit$sets$cs, use.names = F) + 1)",
        "sel <- coef(fit)[ix]",
        "names(sel)[1] <- 'intercept'",
        "res <- tibble::tibble(",
        "  name = names(sel),",
        "  coef = sel,",
        "  .name_repair = janitor::make_clean_names",
        ")",
        "res <- dplyr::filter(res, coef != 0)",
    ]

    susie = pyrty.PyRFunc("susie",
                          code=susie_code,
                          ret="res",
                          r_args=["X", "y"],
                          libs=["susieR", "janitor", "dplyr"],
                          )
    print(susie)
    # susie(X, y)

    # (2) Make some data and run susie
    # --------------------------------
    X, y, true_weights = make_regression(noise=8, coef=True)

    data = {"X": pd.DataFrame(X), "y": pd.DataFrame(y)}
    susie_nonzero = susie(data)

    print(susie_nonzero[1:].sort_values("name").name.to_numpy())
    # compare with print(np.nonzero(true_weights)[0])


The resulting function, :code:`susie`, can be wrapped in a custom :code:`scikit-learn` estimator.

.. code-block:: python

    from sklearn.base import BaseEstimator, RegressorMixin
    from sklearn.utils.validation import check_is_fitted


    class SuSiERegression(BaseEstimator, RegressorMixin):
        def __init__(self, fit_intercept=True):
            self.fit_intercept = fit_intercept

        def fit(self, X, y) -> None:
            self._fit(X, y)
            return self

        def _fit(self, X, y):
            res = susie({"X": X, "y": y})
            
            # Update fitted attributes
            self.intercept_ = res.query("name == 'intercept'").coef.values[0]
            self.coef_ = np.zeros(X.shape[1])
            for row in res[1:].itertuples():
                self.coef_[int(row.name)] = float(row.coef)
            
        def predict(self, X, y=None) -> np.ndarray:
            check_is_fitted(self)
            return np.dot(X, self.coef_.T)

        def __repr__(self) -> str:
            return super().__repr__()

    susie_reg = SuSiERegression()
    susie_reg.fit(pd.DataFrame(X), pd.DataFrame(y))

    # Explore using mixin built-ins
    susie_reg.predict(X)
    susie_reg.score(X, y)


=====
Notes
=====

:code:`pyrty` was mainly designed for personal use. This is a pre-alpha release without a functioning setup, and many limitations aren't documented. The API is subject to change. Feel free to report any issues on the issue tracker. :code:`pyrty` is only tested on Linux and MacOS.

Note that :code:`pyrty` utilizes conda extensively for environment creation, and creates environment and files liberally without warning. This behavior is of course not desirable for most users.

Source was packaged using :code:`PyScaffold`. Lots of boilerplate code was generated by :code:`PyScaffold` and is not documented or relevant here.


.. _rpy2: https://rpy2.github.io/index.html
.. _“Sum of Single Effects” (SuSiE) model: https://stephenslab.github.io/susieR/index.html