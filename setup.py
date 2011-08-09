#!/usr/bin/env python
import os
from setuptools import Command
from setuptools import setup

def shell(cmdline):
    args = cmdline.split(' ')
    os.execlp(args[0], *args)

class GToolsCommand(Command):
    def initialize_options(self): pass
    def finalize_options(self): pass
    user_options = []

class TestCommand(GToolsCommand):
    description = "run tests with nose"
    
    def run(self):
        shell("nosetests")

class CoverageCommand(GToolsCommand):
    description = "run test coverage report with nose"
    
    def run(self):
        shell("nosetests --with-coverage --cover-package=raiden")

setup(
    name='Raiden',
    version='0.1.0',
    author='Jeff Lindsay',
    author_email='jeff.lindsay@twilio.com',
    description='',
    packages=['raiden'],
    install_requires=['gevent_tools'],
    data_files=[],
    cmdclass={
        'test': TestCommand,
        'coverage': CoverageCommand,}
)
