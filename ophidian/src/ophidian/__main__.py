import click
from ophidian.core import Ophidian


@click.command()
@click.option('--major', type=int, default=None)
@click.option('--minor', type=int, default=None)
@click.option('--micro', type=int, default=None)
@click.option('--install/--no-install', default=True)
def main(major, minor, micro, install):
    ophidian = Ophidian()

    def predicate(python):
        if major is not None and python.version[0] != major:
            return False
        if minor is not None and python.version[1] != minor:
            return False
        if micro is not None and python.version[2] != micro:
            return False
        return True
    click.echo(ophidian.find_python(predicate).path)


if __name__ == '__main__':
    main()
