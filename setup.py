from setuptools import setup, find_packages

setup(
    name='leancrawler',
    version='0.0.2',
    url='https://github.com/PatrickMassot/leancrawler',
    author='Patrick Massot',
    author_email='patrickmassot@free.fr',
    description='A Lean prover library crawler',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    package_data={
        '': ['deps.lean'],
    },
    install_requires=['networkx >= 2.1', 'pyyaml >= 3.13', 'pydot >= 1.4.1'])
