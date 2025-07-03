RELEASE_TYPE: minor

This version adds support for generating numpy.ndarray and pandas.Series with any python object as an element.
Effectively, hypothesis can now generate ``np.array([MyObject()], dtype=object)``.
Pandas and Pandera support dataframe columns which themselves contain python datatypes
but Pandera cannot yet use hypothesis strategies like it uses other numpy dtype strategies to generate synthetic data for them.
With this change Pandera can support ``PythonDict and PythonNamedTuple`` etc in data generation.

---

There are two changes here.
The first is to support the generation of columns that contain arbitrary objects in `.extra.pandas.data_frames`.
This is done by using `.iat` instead of `.iloc` to insert objects without pandas' implicit interpretation.
Now that `.iat` is being used, it is possible to pass any strategy as `elements` in `.extra.pandas.column`.
The second is to support generation of any comparable (i.e. one that defines __eq__ and __ne__) object in `from_dtype`
when `dtype=np.dtype('O')` is passed. `from_dtype` uses `st.from_type(type).flatmap(st.from_type)` pattern in this scenario.


Thanks to Shaun Read for identifying and fixing these issues!
