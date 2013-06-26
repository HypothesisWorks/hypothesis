SELF=$(readlink -f $0)
inotifywait -qe modify $(find hypothesis -name "*.py") $SELF pytest.ini
py.test hypothesis --maxfail=1
exec $SELF
