SELF=$(readlink -f $0)

PYTHONPATH=src coverage run --branch --include 'src/hypothesis/*'\
    $(which py.test) -v tests --capture=no 

rm -rf htmlcov

coverage html

inotifywait -qe modify $(find src tests -name "*.py") $SELF pytest.ini
exec $SELF
