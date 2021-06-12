from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='leancrawler',
    version='0.0.3',
    url='https://github.com/PatrickMassot/leancrawler',
    author='Patrick Massot',
    author_email='patrickmassot@free.fr',
    description='A Lean prover library crawler',
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages('src'),
    package_dir={'': 'src'},
    package_data={
        '': ['crawl.lean'],
    },
    entry_points={
        "console_scripts": [
            "leancrawler = leancrawler.crawler:crawl",
        ]},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent" ],
    python_requires='>=3.6',
    install_requires=['networkx >= 2.1', 'pyyaml >= 3.13', 'pydot >= 1.4.1'])
