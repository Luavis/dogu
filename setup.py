#!/usr/bin/env python
from setuptools import setup, find_packages


def install():

    setup(
        name='dogu',
        version='1.0',
        license='MIT',
        description='Dogu server, Implementation of dogu interace',
        long_description='Dogu server, Implementation of dogu interace',
        author='Luavis Kang',
        author_email='luaviskang@gmail.com',
        url='https://github.com/SomaSoma/dogu',
        classifiers=[
            'Development Status :: 2 - Pre-Alpha',
            'License :: Freeware',
            'Operating System :: POSIX',
            'Operating System :: Microsoft :: Windows',
            'Operating System :: MacOS :: MacOS X',
            'Topic :: Scientific/Engineering :: Interface Engine/Protocol Translator',
            'Programming Language :: Python',
            'Programming Language :: Python :: 2.6',
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 3.2',
            'Programming Language :: Python :: 3.3',
            'Programming Language :: Python :: 3.4'],
        packages=find_packages(),
        install_requires=[
            'pytest==2.7.2',
            'gevent==1.1b3',
            'hpack==1.1.0',
            'daemonize==2.3.1',
        ],
        scripts=["dogu-server"],
    )

if __name__ == "__main__":
    install()
