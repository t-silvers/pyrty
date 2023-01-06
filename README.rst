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


Use simple R snippets or scripts in your python code. Works best when the code returns a dataframe or nothing. Let conda/mamba manage your R dependencies outside of your current environment.

For a more powerful alternative, consider using rpy2.


=====
Examples
=====

Porting `susie`_ to python

.. code-block:: python

    import numpy as np
    import pandas as pd
    from pyrty import pyrty
    from sklearn.datasets import make_regression

    # (1) Create a python susie function
    # ----------------------------------
    # Can write code here as list or in a separate file.
    # If you want to use a separate file, use instead e.g., `code="susie.R"`
    # and pyrty will look for a file called `susie.R` in the current directory.
    # User is responsible for making sure the file exists and
    # contains valid R code for `pyrty.PyRFunc`.
    susie_code = [
        "set.seed(1)",
        "X <- read.csv(opt$X)",
        "y <- read.csv(opt$y)",
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

    print(susie_nonzero.name.to_numpy()[1:])
    # compare with np.nonzero(true_weights)[0]


.. _rpy2: https://rpy2.github.io/index.html
.. _susie: https://stephenslab.github.io/susieR/index.html