# Lean crawler

This is a python library which gathers statistics and relational information
about Lean libraries. It is at a very early experimental stage, with low
efficiency and high code mess due to weak planning, but already usable for fun.

## Installation

You need Python 3.6 or later, and Lean 3.4. Make sure the python package
manager `pip` is installed.  Clone this repository, go to its root directory
and run `pip install .` (using `sudo` if needed). It's also recommended to
install `ipython` for interactive use. Alternatively, if you don't want to mess
up with your global python environment, you can use a dedicated virtual
environment, as explained below.

### Optional: setting up a virtual python environment
Use `pip install --user virtualenvwrapper`, and add to your `.bashrc` something like:
```bash
# Python virtualenvwrapper
export WORKON_HOME=$HOME/.virtualenvs
export VIRTUALENVWRAPPER_VIRTUALENV=/usr/local/bin/virtualenv
source $HOME/.local/bin/virtualenvwrapper.sh
```
You can then run `mkvirtualenv --python=/usr/bin/python3.6 leancrawler` to
create your virtual environment. Once inside this environment (either because
you just created it or after running `workon leancrawler`), you can pip
install. Note that you can leave the environment by running `deactivate`.


## Usage

Unless you explore a very small library, it is recommended to use the sqlite
database storage in order to crawl once and then explore freely. Run `ipython`
(or regular `python` if masochistic) and then try something like:

```python
from leancrawler import LeanLibModel, create_db, Path, LeanItemModel

create_db('mathlib.db')
LeanLibModel.from_path('mathlib', Path('/home/name/lean/mathlib/'))
```
The go get some coffee, have a walk, take care of your family for a while.

You can then count theorems using `LeanItemModel.select().where(LeanItemModel.kind=='theorem').count()`
(you can replace `theorem` by `definition`, `instance`, `structure`, `constant`, `axiom`, or `inductive`).
In order to find a declaration by name, say the quadratic reciprocity theorem, you can use 
`qr=LeanItemModel.get(LeanItemModel.name=='zmodp.quadratic_reciprocity')`.

To get [networkx](https://networkx.github.io/documentation/stable/) graphs, you can type
`from leancrawler import ItemGraph, nx, db` and then `g = ItemGraph.from_db(db)`. You can then export the graph, e.g. with
`nx.write_gexf(g, 'mathlib.gexf')` to export to [Gephi](https://gephi.org/).
You can also explore the graph using networkx's API, for instance 
`[x.name for x in nx.dag_longest_path(g)]` will show the longest path in the
graph.

In order to get the node corresponding to the database item `qr`, use `qr_node = g.nodes[qr]`.
Next one can get the subgraph of all nodes leading to the quadratic reciprocity theorem using
`qr_subgraph = g.subgraph(nx.ancestors(g, qr).union(set([qr])))`. Of course one can further filter, e.g.
`qr_subgraph = g.subgraph([node for node in nx.ancestors(g, qr).union(set([qr])) if 'cast' not in node.name and 'coe' not in node.name])`
removes all declaration whose name contains `coe` or `cat`.
Such a subgraph can be exported using `nx.write_gexf` as above.

## Contributing

In order to setup a dev environment, run `pip install -r requirements_tests.txt`.
You will probably want to install `leancrawler` in dev
mode using `pip install -e .` (adding the `-e` switch compared to instructions
above). You also need to make sure both python 3.6 and 3.7 are installed, since
tests are run against both version. See [pyenv](https://github.com/pyenv/pyenv)
if unsure how to ensure that. Then use `tox` to run tests and linting. If you only want to
* test for python 3.6: `tox -e py36`
* test for python 3.7: `tox -e py37`
* run [static type checking](http://mypy-lang.org/): `tox -e mypy`
* run [PEP8](https://www.python.org/dev/peps/pep-0008/) linting: `tox -e flake8`

Note that the testing setup is done, but currently there is only one trivial test.

## How does it work?

There are two main components. A Lean component, living in `deps.lean` uses Lean introspection capabilties to inspect the content of the current file. It spits out a [YaML](http://yaml.org/) file as the one in `tests/test.yaml`. In order to manually use it, you can import `deps` in a file and then use `#eval print_content` at the bottom. The python component does that on a temporary copy of each file it can find. This component is made of three parts. The module `python_storage` contains classes reading the YaML information and storing information in memory. Module `db_storage` stores this information in a SQLite database in order to save introspection time. Module `graph` creates a networkx graph from a database. Originally the design was meant to be less coupled, but I underestimated introspection time, changed my mind and created this mess.
