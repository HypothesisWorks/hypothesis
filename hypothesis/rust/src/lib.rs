// This file is part of Hypothesis, which may be found at
// https://github.com/HypothesisWorks/hypothesis/
//
// Copyright the Hypothesis Authors.
// Individual contributors are listed in AUTHORS.rst and the git log.
//
// This Source Code Form is subject to the terms of the Mozilla Public License,
// v. 2.0. If a copy of the MPL was not distributed with this file, You can
// obtain one at https://mozilla.org/MPL/2.0/.

mod internal;

#[pyo3::pymodule]
mod _native {
    use pyo3::prelude::*;
    use pyo3::types::PyDict;

    #[pymodule_export]
    use super::internal::internal;

    #[pymodule_init]
    fn init(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add("__version__", env!("CARGO_PKG_VERSION"))?;

        /// After PyO3's declarative-module machinery has assembled the
        /// submodule tree, walk it and register every node in `sys.modules`
        /// under its dotted qualified path, and overwrite each submodule's
        /// `__name__` with that path. Two things would otherwise go wrong:
        ///
        ///   * `from hypothesis._native.x.y import z` fails, because Python's
        ///     import machinery resolves the parent via `sys.modules['…x.y']`
        ///     and neither PyO3 nor CPython populates that for native
        ///     submodules (PyO3 issue #759).
        ///   * The declarative `#[pymodule] mod` macro stores each submodule's
        ///     `__name__` as just the basename, so `inspect.getmodule`,
        ///     traceback frames, and pickle's module lookup all see a bare
        ///     name like "cathetus" instead of the full dotted path.
        fn walk(m: &Bound<'_, PyModule>, qualname: &str) -> PyResult<()> {
            let py = m.py();
            let sys_modules = py.import("sys")?.getattr("modules")?;
            let dict: Bound<'_, PyDict> = m.dict();
            for (name, value) in dict.iter() {
                let Ok(submod) = value.cast::<PyModule>() else {
                    continue;
                };
                let basename: String = name.extract()?;
                let child_qualname = format!("{qualname}.{basename}");
                submod.setattr("__name__", &child_qualname)?;
                sys_modules.set_item(&child_qualname, submod)?;
                walk(submod, &child_qualname)?;
            }
            Ok(())
        }
        walk(m, "hypothesis._native")
    }
}
