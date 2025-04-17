RELEASE_TYPE: patch

The pub-sub change listening interface of the :ref:`Hypothesis database <database>` now correctly fires events for |DirectoryBasedExampleDatabase| if the directory was created after the listener was added.

Also disables on emscripten the constants-extraction feature introduced in :ref:`v6.131.1`, where it caused substantial slowdown.
