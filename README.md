# Lean crawler

This is a python library which gathers statistics and relational information
about Lean libraries. It is at a very early experimental stage, 
but already usable for fun.

## Installation

You need Python 3.6 or later, and Lean 3.26 or later. Make sure the python package
manager `pip` is installed.  Clone this repository, go to its root directory
and run `pip install .` (using `sudo` if needed). It's also recommended to
install `ipython` for interactive use. Alternatively, if you don't want to mess
up with your global python environment, you can use a dedicated virtual
environment, as explained below.

### Optional: setting up a virtual python environment
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

Inside a valid Lean project folder, if you want to inspect the theory
visible in `my_file.lean`, run `leancrawler my_file` (if `my_file` is not at
the root of you project source then you can indicate a dot separated path, just
as you would do when importing it in Lean). This will
create a file `crawl.lean` in the current folder. Then you need to make sure
you have up to date olean files for `my_file` and all its dependencies.
Then you can run `lean --run crawl.lean`.
This will take a while if you want to inspect a large theory. In the end you
should have a new file called `data.yaml` (you can change this name by providing a
second argument to the `leancrawler` invocation).

Then run `ipython` (or regular `python` if masochistic), and try something like:

```python
from leancrawler import LeanLib, LeanDeclGraph

lib = LeanLib.from_yaml('My nice lib', 'my_data.yaml')
```

This will also take a noticable time, but much less than Lean's work
above. You can save that work for later use by typing
`lib.dump('my_py_data')` and retrieve it in a later python session using
`lib = LeanLib.load_dump('my_py_data')`.

Then `lib` is basically a dictionary of whose keys are Lean names (as
python strings) and values are `LeanDecl` which contain a bunch a
informations about a Lean declaration. Try `lib['group']` to see what is
stored about the `group` declaration from Lean's core library.

One way of playing with the lib is to make a graph.

```python
G = LeanDeclGraph.from_lib(lib)
```

This graph will include lots of nodes coming from basic logic (like
`eq`, `Exists`, etc.) which can be seen as noise. You can get rid of
some of them using `lib.prune_foundations()` before creating the graph.
This function takes an optional argument `files` which is a list of substrings
whose appearance in a declaration filename flags it for removal.
For instance `lib.prune_foundations(files=['mathlib', 'elan'])` will remove
any declaration from mathlib and the core library.
Similarly, you can use the optional argument `prefixes` to indicate a list
of declaration name prefixes to remove.
For instance `lib.prune_foundations(prefixes=['list', 'set', 'finset'])` will remove
any declaration whose name starts with either `list`, `set` or `finset`.

If you are interested only in nodes leading up to `group`, you can try
`group_graph = G.component_of('group')`. Then you can export it as a
gexf file using `group_graph.write('group.gexf')`.


You can also explore the graph using networkx's API, for instance 
`nx.dag_longest_path(G)` will show the longest path in the graph
while `nx.shortest_path(gr, 'my_def', 'my_lemma')` will show the shortest
path from `my_def` to `my_lemma`.

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
