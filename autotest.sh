SELF=$(readlink -f $0)

coverage run --branch --include 'hypothesis/*'\
    $(which py.test) -v hypothesis --capture=no 

rm -rf htmlcov

coverage html

inotifywait -qe modify $(find hypothesis -name "*.py") $SELF pytest.ini
exec $SELF
