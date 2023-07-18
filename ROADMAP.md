# Roadmap

- Confirm env creation, teardowns, etc.
- Use `lmod` as another layer of (compiler/software) control (e.g., via a "`pyrty` module")
- Any speed-up from cloning conda envs? Trade-off of larger mem on disk when cloning
- Fix `optparse`-ing: Ensure `optparse` is installed, if args; `opt$<arg>` without explicitly adding to code
- Backend script and env registries?
- Add a `from_template` class method to `PyRFunc` for (1) returning dataframes, (2) saving dataframes, (3) building on tidyverse, and so on
- `pyrty`-specific envfile
- More informative error messages when R script errors. E.g., check if all libraries loaded in Rscript are installed
- Create a docstring for function in call signature
- Refactor env creation: different managers, different inputs (e.g. `mamba` using an envfile or using config or using list of packages)
- Clean up signatures for `PyRFunc` funcs that return instances. Tackle after refactoring env creation.
- Log env and script creation
- Use `Arrow` for big-data "`df"-capturing
- Reduce `subprocess` calls for apply-style functions
