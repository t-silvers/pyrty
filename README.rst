.. image:: https://img.shields.io/badge/-PyScaffold-005CA0?logo=pyscaffold
    :alt: Project generated with PyScaffold
    :target: https://pyscaffold.org/

=====
pyrty
=====


    Use R snippets as python functions. Manage R dependencies separately.


Use simple R snippets or scripts in python as functions with pythonic signatures. Let :code:`conda` , :code:`mamba` , :code:`renv` , or :code:`packrat` manage R dependencies outside of your current environment. Most powerful when R code returns a conformable dataframe object.

For a more powerful alternative, consider using `rpy2`_. Use `basilisk`_ to go the other way around (python in R).

.. _rpy2: https://rpy2.github.io/doc/latest/html/index.html
.. _basilisk: https://www.bioconductor.org/packages/release/bioc/html/basilisk.html


=================
Installation
=================

.. code-block:: bash

    git clone https://github.com/t-silvers/pyrty.git
    cd pyrty
    pip install .

==========
Examples
==========

Wrap a simple R snippet in a python function:
================================================

Here we port the `“Sum of Single Effects” (SuSiE) model`_ to python and use :code:`mamba` to manage R dependencies. We assume that the user has a valid environment file, :code:`/path/to/susie-env.yaml` (for more info on environment files, see `conda's docs`_).

.. code-block:: python

    import numpy as np
    import pandas as pd
    from pyrty import PyRFunc
    from sklearn.datasets import make_regression

    # (1) Create a python susie function
    # ----------------------------------
    # Can write code here as list or in a separate file.
    # If you write the code as in here, `pyrty` will manage
    # R script creation (and deletion) for you.
    susie_code = """set.seed(1)
    X <- as.matrix(readr::read_csv(opt$X, show_col_types = FALSE))
    y <- as.matrix(readr::read_csv(opt$y, show_col_types = FALSE))
    fit <- susieR::susie(X, y)
    ix <- c(1, unlist(fit$sets$cs, use.names = F) + 1)
    sel <- coef(fit)[ix]
    names(sel)[1] <- 'intercept'
    res <- tibble::tibble(
      name = names(sel),
      coef = sel,
      .name_repair = janitor::make_clean_names
    )
    res <- dplyr::filter(tibble::as_tibble(res), coef != 0)"""
    susie_opts = dict(X = {}, y = {})
    susie_envfile = '/path/to/susie-env.yaml'
    susie_pkgs = ['dplyr', 'janitor', 'optparse', 'readr', 'susieR', 'tibble']
    susie = PyRFunc.from_scratch('susie', susie_code, opts=susie_opts, libs=susie_pkgs,
                                 manager='mamba', env_kwargs=dict(envfile=susie_envfile),
                                 capture_output=True, capture_obj_name='res')

    print(susie)
    # susie(X, y)

    # (2) Make some data and run susie
    # --------------------------------
    X, y, true_weights = make_regression(noise=8, coef=True)
    X, y = pd.DataFrame(X), pd.DataFrame(y)
    data = {'X': X, 'y': y}

    susie_nonzero = susie(data)
    susie_nonzero = susie_nonzero[1:].sort_values("name").name.to_numpy()
    susie_nonzero = np.sort([int(snz) for snz in susie_nonzero if not pd.isna(snz)])
    print(f'True indices of nonzero weights:\n{np.nonzero(true_weights != 0)[0]}\n\n'
          f'Indices of nonzero weights from SuSiE:\n{susie_nonzero}')
    # True indices of nonzero weights:
    # [ 2 13 44 57 59 74 76 80 85 97]

    # Indices of nonzero weights from SuSiE:
    # [ 2 13 57 59 74 76 80 85 97]

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
            res = susie({'X': X, 'y': y})
            
            # Update fitted attributes
            self.intercept_ = res.query("name == 'intercept'").coef.values[0]
            self.intercept_ = float(self.intercept_)
            self.coef_ = np.zeros(X.shape[1])
            for row in res[1:].itertuples():
                self.coef_[int(row.name)] = float(row.coef)
            
        def predict(self, X, y=None) -> np.ndarray:
            check_is_fitted(self)
            return np.dot(X, self.coef_.T) + self.intercept_

        def __repr__(self) -> str:
            return super().__repr__()

    susie_reg = SuSiERegression()
    susie_reg.fit(X, y)

    # Explore using mixin built-ins
    susie_reg.predict(X)
    susie_reg.score(X, y)


Deploy an R snippet in an existing environment:
=====================================================

Environment creation can be costly. Here we demonstrate how to simulate scRNA-seq data using :code:`splatter` with an existing environment. For more info on :code:`splatter`, see the `splatter tutorial`_.

.. code-block:: python

    # (1) Create a python splatter::splatSimulate function
    # ----------------------------------------------------
    splatter_code = """# Params
    set.seed(1)
    usr.nGenes <- opt$n_genes
    usr.mean.shape <- opt$mean_shape
    usr.de.prob <- opt$de_prob
    params <- splatter::newSplatParams()
    params <- splatter::setParams(
      params,
      nGenes = usr.nGenes,
      mean.shape = usr.mean.shape,
      de.prob = usr.de.prob
    )

    # Simulate data using estimated parameters
    sim <- splatter::splatSimulate(params)

    # Parse data
    sim.res <- tibble::as_tibble(
      SummarizedExperiment::assay(sim, "counts"),
      validate = NULL,
      rownames = "gene_id",
      .name_repair = janitor::make_clean_names
    )
    sim.res$gene_id <- janitor::make_clean_names(sim.res$gene_id)"""

    splatter_opts = dict(
        n_genes = dict(type="'integer'", default=1000),
        mean_shape = dict(type="'double'", default=0.6),
        de_prob = dict(type="'double'", default=0.1),
    )
    splatter_env_prefix = '/path/to/envs/splatter-env'
    splatter_env = PyREnv.from_existing('splatter-env', splatter_env_prefix, 'mamba')
    splatter_pkgs = ['dplyr', 'janitor', 'optparse', 'readr', 'splatter', 'tibble']
    splatter_rscript_kwargs = dict()
    splatter = PyRFunc.from_env('splatter', splatter_env, code=splatter_code, opts=splatter_opts,
                                libs=splatter_pkgs, capture_output=True, capture_obj_name='sim.res',
                                register=True, overwrite=True)

    # (2) Make some data and run splatSimulate
    # ----------------------------------------
    splatter_params = {'n_genes': 100, 'mean_shape': 0.5, 'de_prob': 0.5}
    splatter_sim_data = (
        splatter(splatter_params)
        .set_index('gene_id')
        .dropna()
    )
    splatter_sim_data
    # A 100 x 100 gene by cell pandas df of simulated counts


With any :code:`pyrty` function, we can save it using :code:`register=True`. After registering a function, it can be re-loaded in a new session without having to re-create it or the requisite scripts and environment--even across multiple users and machines simultaneously.

.. code-block:: python

    splatter_registered = PyRFunc.from_registry('splatter')

    # Check that the function is the same
    assert str(splatter_registered.rscript) == str(splatter.rscript)
    assert splatter_registered.env.prefix == splatter.env.prefix

    # Run the function as usual
    splatter_sim_data = splatter_registered(splatter_params)
    splatter_sim_data
    # A 100 x 100 gene by cell pandas df of simulated counts


Run an R script from python:
===================================

The utility function :code:`run_rscript()` is a very lightweight wrapper for running an R script and (optionally) capturing its output:

.. code-block:: python

    from pathlib import Path
    from tempfile import NamedTemporaryFile

    from pyrty.utils import run_rscript

    # Create a temporary R script or use an existing one
    rscript_code = """# Keep stdout clean
    options(warn=-1)
    suppressPackageStartupMessages(library(optparse))
    suppressPackageStartupMessages(library(tidyverse))
    option_list <- list(make_option('--c', type = 'double'))
    opt <- parse_args(OptionParser(option_list=option_list))

    # Create a dataframe and write to stdout
    a <- 1:5
    df <- tibble::tibble(a, b = a * 2, c = opt$c)
    try(writeLines(readr::format_csv(df), stdout()), silent=TRUE)"""

    with NamedTemporaryFile('w+') as rscript:
        rscript_path = Path(rscript.name)
        rscript_path.write_text(rscript_code)
        df = run_rscript(f'mamba run -n sandbox Rscript {str(rscript_path)} --c 1',
                         capture_output=True, capture_type='df')
        
    print(df)
    # 0  a   b  c
    # 1  1   2  1
    # 2  2   4  1
    # 3  3   6  1
    # 4  4   8  1
    # 5  5  10  1

=====
Notes
=====

:code:`pyrty` was developed for personal use in a single-user environment. This is a pre-alpha release and many limitations aren't documented. The API is subject to change. Feel free to report any issues on the issue tracker. :code:`pyrty` is only tested on Linux and MacOS.

Note that :code:`pyrty` utilizes :code:`conda` /:code:`mamba` /:code:`packrat` /:code:`renv` environment creation, and it will create environments and files liberally, without much warning. This behavior is not desirable for most users.

Source was packaged using :code:`PyScaffold`. Lots of boilerplate code was generated by :code:`PyScaffold` and is not documented or relevant here.


.. _“Sum of Single Effects” (SuSiE) model: https://stephenslab.github.io/susieR/index.html
.. _conda's docs: https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#creating-an-environment-from-an-environment-yml-file
.. _splatter tutorial: https://bioconductor.org/packages/release/bioc/vignettes/splatter/inst/doc/splatter.html#4_The_SplatParams_object