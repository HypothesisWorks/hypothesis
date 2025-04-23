RELEASE_TYPE: patch

|DirectoryBasedExampleDatabase| will now fall back to (potentially non-atomic)
copies rather than renames, if the temporary directory used for atomic
write-and-rename is on a different filesystem to the configured database
location (:issue:`4335`).
