from distutils.core import setup
from setuptools.command.test import test as TestCommand
import sys


class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest
        errno = pytest.main(self.test_args)
        sys.exit(errno)

setup(
    name='hypothesis',
    version='0.2.0',
    author='David R. MacIver',
    author_email='david@drmaciver.com',
    packages=['hypothesis'],
    url='https://github.com/DRMacIver/hypothesis',
    license='LICENSE.txt',
    description='Tools for falsifying hypothesis with random data generation',
    long_description=open('README').read(),
    tests_require=['pytest', 'pytest-timeout', 'flake8'],
    install_requires=['six'],
    cmdclass={'test': PyTest},
)
