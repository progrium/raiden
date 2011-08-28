#!/usr/bin/env python
import os
from setuptools import Command
from setuptools import setup, find_packages

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

class CleanCommand(GToolsCommand):
    description = "delete stupid shit left around"
    files = "Raiden.egg-info build serviced.log serviced.pid"
        
    def run(self):
        shell("rm -rf %s" % self.files)

setup(
    name='Raiden',
    version='0.1.0',
    author='Jeff Lindsay',
    author_email='jeff.lindsay@twilio.com',
    description='',
    packages=find_packages(),
    install_requires=['gevent_tools', 'gevent_zeromq', 'msgpack-python', 'webob', 'ws4py'],
    data_files=[],
    cmdclass={
        'test': TestCommand,
        'coverage': CoverageCommand,
        'clean': CleanCommand,}
)
