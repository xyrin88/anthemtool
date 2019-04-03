from setuptools import setup, find_packages

setup(
    name='anthemtool',
    version='1.1',
    description='Unpacker for the Frostbite Engine based Anthem Game.',
    author='xyrin88',
    author_email='xyrin88@gmail.com',
    install_requires=['diskcache'],
    packages=find_packages(exclude=["scripts"]),
)
