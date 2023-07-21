.. image:: https://img.shields.io/badge/-PyScaffold-005CA0?logo=pyscaffold
    :alt: Project generated with PyScaffold
    :target: https://pyscaffold.org/

=====
PyRty
=====


    Use R snippets as Python functions. Manage R dependencies separately.


Use simple R snippets or complex scripts in Python as functions with pythonic 
signatures. Let :code:`conda` , :code:`mamba` , :code:`renv` , or 
:code:`packrat` manage dependencies outside of your current environment. 
Most powerful when R code returns a conformable dataframe object. Extensible
to languages beyond R, including Python and Bash/shell scripts.

Use `basilisk`_ or `reticulate`_ to go the other way around (Python in R). For 
a more powerful alternative for using R in Python, consider `rpy2`_. Depending 
on the use case, it may be more appropriate to use a workflow management system 
like Snakemake, Nextflow, or Airflow.

Contents
=========

.. contents:: Table of Contents
   :local:
   :depth: 2

- `Installation`_
- `Examples`_
    - `Simple R snippet`_
    - `Complex R snippet`_
    - `With an existing env`_
    - `Utility functions`_
- `Support for other languages`_
- `Debugging`_
- `Notes`_
    - `pyrty vs rpy2`_

.. _Installation:

Installation
=================

.. code-block:: bash

    git clone https://github.com/t-silvers/pyrty.git
    cd pyrty
    pip install .

.. _Examples:

Examples
==========

.. _Simple R snippet:

Wrap a simple R snippet in a python function:
----------------------------------------------------

To create a Python function from an R snippet, we need to specify an
environment manager (:code:`conda` , :code:`mamba` , or :code:`renv`),
a language (R or Python), code, and a set of dependencies.
Here, we also specify a set of arguments (:code:`args`) and an output to
collect (:code:`output_type`).

.. code-block:: python

    from pyrty import PyRFunc

    make_df_code = 'a <- 1:5; res <- tibble::tibble(a, b = a * 2, c = opt$c)'
    make_df = PyRFunc.from_scratch('make_df', manager='mamba', lang='R', args=dict(c={'type': "'double'"}),
                                   deps=dict(cran=['tibble']), code=make_df_code, output_type='df')
    df = make_df({'c': 3})
    print(df)
    #   a  b c
    #   1  2 3
    #   2  4 3
    #   3  6 3
    #   4  8 3
    #   5 10 3

.. _Complex R snippet:

Wrap a more complex R snippet:
----------------------------------------------------

Here we port the `“Sum of Single Effects” (SuSiE) model`_ to Python and use 
:code:`mamba` to manage R dependencies. We assume that the user has a valid 
environment file, :code:`/path/to/susie-env.yaml` (for more info on 
environment files, see `conda's docs`_).

.. code-block:: python

    from pyrty import PyRFunc

    # (1) Create a Python susie function
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
    susie_envf = Path('/path/to/susie-env.yaml')
    susie_pkgs = ['dplyr', 'janitor', 'readr', 'susieR', 'tibble']
    susie = PyRFunc.from_scratch('susie', manager='mamba', lang='R', args=susie_opts,
                                 deps=susie_pkgs, code=susie_code, envfile=susie_envf,
                                 output_type='df')

    print(susie)
    # susie(X, y)

    # (2) Make some data and run susie
    # --------------------------------
    import numpy as np
    import pandas as pd
    from sklearn.datasets import make_regression

    X, y, true_weights = make_regression(noise=8, coef=True, random_state=10023)
    X, y = pd.DataFrame(X), pd.DataFrame(y)
    data = {'X': X, 'y': y}

    susie_nonzero = susie(data)
    susie_nonzero = susie_nonzero[1:].sort_values("name").name.to_numpy()
    susie_nonzero = np.sort([int(snz) for snz in susie_nonzero if not pd.isna(snz)])
    print(f'True indices of nonzero weights:\n{np.nonzero(true_weights != 0)[0]}\n\n'
            f'Indices of nonzero weights from SuSiE:\n{susie_nonzero}')
    # True indices of nonzero weights:
    # [11 12 18 20 25 38 49 50 55 68]

    # Indices of nonzero weights from SuSiE:
    # [11 12 18 20 25 38 49 50 55 68]

The resulting function, :code:`susie`, can be wrapped in a custom 
:code:`scikit-learn` estimator.

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
            self.intercept_ = float(res.query("name == 'intercept'").coef.values[0])
            self.coef_ = np.zeros(X.shape[1])
            for row in res[1:].itertuples():
                self.coef_[int(row.name)] = float(row.coef)
            
        def predict(self, X, y=None) -> np.ndarray:
            check_is_fitted(self)
            return np.dot(X, self.coef_.T) + self.intercept_


    susie_reg = SuSiERegression()
    susie_reg.fit(X, y)

    # Explore using mixin built-ins
    susie_reg.predict(X)
    susie_reg.score(X, y)

.. _With an existing env:

Deploy a function in an existing environment:
----------------------------------------------------

Environment creation can be costly. Here we demonstrate how to use the R package
:code:`splatter` within an existing environment to simulate 
scRNA-seq data. For more info on :code:`splatter`, see the `splatter tutorial`_.

.. code-block:: python

    from pathlib import Path
    from pyrty import PyRFunc

    # (1) Create a Python splatSimulate() function
    # --------------------------------------------
    splat_code = """# Params
    set.seed(1)
    params <- splatter::setParams(
        splatter::newSplatParams(),
        nGenes = opt$n_genes,
        mean.shape = opt$mean_shape,
        de.prob = opt$de_prob
    )
    sim <- splatter::splatSimulate(params)
    sim.res <- tibble::as_tibble(
        SummarizedExperiment::assay(sim, "counts"),
        validate = NULL,
        rownames = "gene_id",
        .name_repair = janitor::make_clean_names
    )
    sim.res$gene_id <- janitor::make_clean_names(sim.res$gene_id)"""

    splat_opts = dict(
        n_genes = dict(type="'integer'", default=1000),
        mean_shape = dict(type="'double'", default=0.6),
        de_prob = dict(type="'double'", default=0.1),
    )
    splat_pkgs = ['janitor', 'splatter', 'tibble']
    splat_env = Path('/path/to/envs/splatter-env')
    splat_sim = PyRFunc.from_scratch('splat_sim', manager='mamba', lang='R', args=splat_opts,
                                     deps=splat_pkgs, code=splat_code, prefix=splat_env,
                                     ret_name='sim.res', output_type='df', register=True)

    # (2) Make some data and run splatSimulate()
    # ------------------------------------------
    splat_params = {'n_genes': 100, 'mean_shape': 0.5, 'de_prob': 0.5}
    sim_data = splat_sim(splat_params).set_index('gene_id')
    sim_data
    # A 100 x 100 gene by cell pandas df of simulated counts

With any :code:`pyrty` function, we can save it using :code:`register=True`. 
After registering a function, it can be re-loaded in a new session without 
having to re-create it or the requisite scripts and environment--even across 
multiple users and machines simultaneously.

.. code-block:: python

    splat_sim_registered = PyRFunc.from_registry('splat_sim')

    # Check that the function is the same
    assert str(splat_sim_registered.script) == str(splat_sim_registered.script)
    assert splat_sim_registered.env.prefix == splat_sim.env.prefix

    # Run the function as before
    sim_data = splat_sim_registered(splat_params).set_index('gene_id')
    sim_data
    # A 100 x 100 gene by cell pandas df of simulated counts


:code:`pyrty` internally tracks which files it has created. Unregistering
:code:`'splat_sim'` will not delete the :code:`splatter` environment if the
environment existed when the function was created.

.. code-block:: python

    splat_sim.unregister()
    splat_sim.env.env_exists
    # True

.. _Utility functions:

Run a script and capture DF output:
-------------------------------------

The utility function :code:`run_capture()` is a very lightweight wrapper for 
running a script and capturing its output. It is used internally by :code:`pyrty`'s
run manager to run scripts in a subprocess and capture their stdout. Below we 
demonstrate its usage with a simple R script that takes a single argument 
:code:`--c` and writes a dataframe to stdout in some existing :code:`mamba` 
environment, :code:`sandbox`.

.. code-block:: python

    from pathlib import Path
    from tempfile import NamedTemporaryFile

    from pyrty.utils import run_capture

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
        df = run_capture(f'mamba run -n sandbox Rscript {str(rscript_path)} --c 1')
        
    print(df)
    # 0  a   b  c
    # 1  1   2  1
    # 2  2   4  1
    # 3  3   6  1
    # 4  4   8  1
    # 5  5  10  1

.. _Support for other languages:

Support for other languages
==============================

:code:`pyrty` was designed to be language agnostic and explicitly supports
R, Python, and Bash/shell scripts via the :code:`PyRScript` module. Support
for other languages can be added by subclassing :code:`BaseScriptWriter`.
For some languages, e.g. Julia and Java, environment managers for :code:`conda`
or :code:`mamba` may be used straightforwardly with custom post-deployment
commands (see :code:`postdeploy_cmds` arg); however for other languages, 
it may be necessary to subclass the :code:`BaseEnvManager` class for
environment management.

.. _Debugging:

Debugging
==========

Debugging :code:`pyrty` functions can be tricky. Here are some tips, using the :code:`susie` example from above.

#. Explicitly create the environment (outside of :code:`pyrty`) and validate that the environment can be created and that the provided code can be run.

#. Inspect the function's R script.

    .. code-block:: python

      susie.script.print()

#. Access the function's run manager and perform a dry run (:code:`dry_run=True`) to inspect the run command.

    .. code-block:: python

      susie.run_manager.run(data, dry_run=True)

.. _Notes:

Notes
=====

:code:`pyrty` was developed for personal use in a single-user environment.
This is a pre-alpha release and many limitations aren't documented. The API 
is subject to change. 

since sgkit is still a 0.x release, its API is still subject to non-backwards compatible changes.

Feel free to report any issues on the issue tracker. 
:code:`pyrty` is only tested on Linux and MacOS.

Note that :code:`pyrty` utilizes :code:`conda` /:code:`mamba` /:code:`packrat` 
/:code:`renv` environment creation, and it will create environments and files 
liberally, without much warning. This behavior is not desirable for most users.

Source was packaged using :code:`PyScaffold`. Lots of boilerplate code was 
generated by :code:`PyScaffold` and is not documented or relevant here.

.. _pyrty vs rpy2:

:code:`pyrty` vs :code:`rpy2`:
-------------------------------------

:code:`rpy2` developers `write`_ : 

    The :code:`r` instance

    We mentioned earlier that :code:`rpy2` is running an embedded R. This is may 
    be a little abstract, so there is an object :code:`rpy2.robjects.r` to make 
    it tangible.

    This object can be used as rudimentary communication channel between
    Python and R, similar to the way one would interact with a subprocess yet
    more efficient, better integrated with Python, and easier to use.

To be sure, :code:`pyrty`'s reliance on subprocesses is likely less "efficient" 
than the approach used by :code:`rpy2`. However, :code:`pyrty` strives to be
even better integrated, easier to use, and produce cleaner code than :code:`rpy2`. 
While no benchmarks are provided, :code:`rpy2` will almost always be more 
performant, with some caveats for memory-bound functions and based on 
distribution and processing details.

In summary, :code:`pyrty` is useful for quickly implementing readable, reusable, 
and shareable Python code when its underlying dependencies are more easily managed 
independently of the working environment. These situations arise both in quick 
prototyping and in shipped code that is not performance critical.

.. External references:
.. _basilisk: https://www.bioconductor.org/packages/release/bioc/html/basilisk.html
.. _conda's docs: https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#creating-an-environment-from-an-environment-yml-file
.. _reticulate: https://rstudio.github.io/reticulate/
.. _rpy2: https://rpy2.github.io/doc/latest/html/index.html
.. _splatter tutorial: https://bioconductor.org/packages/release/bioc/vignettes/splatter/inst/doc/splatter.html#4_The_SplatParams_object
.. _“Sum of Single Effects” (SuSiE) model: https://stephenslab.github.io/susieR/index.html
.. _write: https://rpy2.github.io/doc/latest/html/introduction.html#the-r-instance