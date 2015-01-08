SELF=$(readlink -f $0)
python -m pytest --maxfail=1 $(
    find hypothesis -name "test_*.py"  -printf '%T@ %p\n' |
    sort -k 1nr | 
    sed 's/^[^ ]* //'
)
inotifywait -qe modify $(find hypothesis -name "*.py") $SELF pytest.ini
exec $SELF
