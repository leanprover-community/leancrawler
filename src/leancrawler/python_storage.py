"""
Python classes storing information about Lean libs
"""

from typing import List, Dict, Optional
from typing.io import TextIO
from pathlib import Path
import subprocess
from datetime import datetime
import logging
from tempfile import NamedTemporaryFile

import regex
import yaml

logger = logging.getLogger("Lean Crawler")
#logger.setLevel(logging.DEBUG)
logger.setLevel(logging.INFO)
if (logger.hasHandlers()):
    logger.handlers.clear()
logger.addHandler(logging.StreamHandler())

ident = r'(?<name>[^ (){}\[\]\n:]+)'
idents = r'(?<names>(((?<name>[^ ]+)) *)+)'

import_regex = regex.compile(r'import +' + idents)
instance_regex = regex.compile(r'([^{]*).{')

AUX_DEF_SUFFIX = ('.rec', '.brec', '.brec_on', '.mk', '.rec_on', '.inj_on',
                  '.has_sizeof_inst', '.no_confusion_type', '.no_confusion',
                  '.cases_on', '.inj_arrow', '.sizeof', '.inj',
                  '.inj_eq', '.sizeof_spec', '.drec', '.dcases_on',
                  '.drec_on', '.below', '.ibelow', '.binduction_on',)

TOOLCHAIN = Path.home()/'.elan/toolchains/3.4.2/'

class LeanError(Exception):
    pass

class LeanRunner:
    def __init__(self, exec_path=TOOLCHAIN / 'bin/lean',) -> None:
        self.exec_path = exec_path

    def run(self, path: Path, cwd: Path = None) -> str:
        logger.debug(f"Calling Lean at {self.exec_path} in {cwd} on {path}")
        return subprocess.run(["lean", "-T500000", str(path)],
                              stderr=subprocess.PIPE,
                              encoding="utf-8", cwd=cwd).stderr


class LeanItem:
    def __init__(self, kind: str, name: str, size: int = 0,
                 line_nb: int = 0,
                 def_depends: List[str] = None,
                 fields: List[str] = None,
                 proof_size: int = 0,
                 proof_depends: List[str] = None,
                 instance_target: str = '') -> None:
        """ An item from a Lean file """
        self.kind = kind
        self.name = name
        self.namespace = name.split('.')[:-1]
        self.size = size
        self.line_nb = line_nb
        self.def_depends = def_depends or []
        self.fields = fields or []
        self.proof_size = proof_size
        self.proof_depends = proof_depends or []
        self.instance_target = instance_target

    def __repr__(self):
        return str(self.name)


class LeanFile:
    def __init__(self, path: Path = None, visited: datetime = None,
                 nb_lines: int = 0, imports: List[str] = None,
                 items: dict = None) -> None:
        self.path = path
        self.visited = visited or datetime.now()
        self.nb_lines = nb_lines
        self.imports = imports or []
        self.items = items or dict()

    def __getitem__(self, key: str) -> LeanItem:
        return self.items[key]

    def __setitem__(self, key: str, value: LeanItem) -> None:
        self.items[key] = value

    def __delitem__(self, key: str) -> None:
        del self.items[key]

    def __contains__(self, key: str) -> bool:
        return key in self.items

    def __repr__(self):
        return str(list(self.items.keys()))

    def get(self, key: str, default: LeanItem = None) -> LeanItem:
        return self.items.get(key, default)

    @classmethod
    def from_path(cls, path: Path, root: Path = None, prelude: bool = False) -> 'LeanFile':
        """Builds a LeanFile object from a file path."""
        root = root or path.parent
        logger.info(f"Creating LeanFile from path {path}")
        with path.open(encoding="utf-8") as f:
            lean_file = cls.from_stream(f, root, prelude)
        lean_file.path = path
        return lean_file

    @classmethod
    def from_stream(cls, stream: TextIO, root: Path, prelude: bool = False) -> 'LeanFile':
        """Builds a LeanFile object from a stream of lines, running Lean from
        root directory."""
        lean_file = cls()
        tmp_file = NamedTemporaryFile("w+t", encoding="utf-8", delete=False)
        if not prelude:
            tmp_file.write("import deps\n")
        line_nb = 0
        for line in stream:
            line_nb += 1
            tmp_file.write(line)
            if prelude and 'prelude' in line:
                tmp_file.write("import deps\n")

            m = import_regex.match(line)
            if m:
                new_imports = m["names"].split()
                lean_file.imports += new_imports
                logger.debug("Detected imports: "+', '.join(new_imports))
                continue
        tmp_file.write("\n#eval print_content")
        tmp_file.close()
        lean_file.nb_lines = line_nb

        lean_output = LeanRunner().run(Path(tmp_file.name), cwd=root)
        logger.debug(lean_output)
        if ': error:' in lean_output:
            logger.error('Lean pointed out an error.')
            raise LeanError
        Path(tmp_file.name).unlink()
        lean_file.parse_lean_output(lean_output)
        return lean_file

    def parse_lean_output(self, lean_output: str) -> None:
        if lean_output:
            logger.debug("Parsing Lean output")
        else:
            logger.warning("No Lean output.")
            return
        if ': error:' in lean_output:
            logger.warning('Lean pointed out an error.')
        decls = sorted(yaml.safe_load(lean_output),
                       key=lambda x: (x["Line"] or 0, x["Type"]))
        for decl in decls:
            name = decl["Name"]
            # Now fight yaml.load which tried to be too clever
            if name is True:
                name = 'true'
            elif name is False:
                name = 'false'
            kind = decl["Type"]
            line = decl["Line"]
            logger.debug(f"Parsing Lean ouput at: {name} ({kind})")
            if name.endswith(AUX_DEF_SUFFIX):
                logger.debug(f"Was aux def: {name}")
                continue
            uses = (decl.get("Uses", []) + decl.get("Type uses", []) + decl.get("Body uses", []) +
                decl.get("Statement uses", []) + decl.get("Proof uses lemmas", []) + decl.get("and uses", []))
            if kind == "structure_field":
                parent = '.'.join(decl["Parent"].split('.')[:-1])
                logger.debug(f"structure field: {name} added to {parent}")
                # self[parent].size += decl["Size"]
                for use in uses:
                    if use != parent:
                        self[parent].def_depends.append(use)
                continue

            item = self[name] = LeanItem(kind, name, line_nb=line)

            # item.size = decl["Size"]
            if kind in ['theorem', 'lemma']:
                item.def_depends = decl["Statement uses"]
                # item.proof_size = decl["Proof size"]
                item.proof_depends = uses
            elif kind in ['definition', 'inductive', 'constant', 'axiom']:
                item.def_depends = uses
            elif kind == 'instance':
                item.def_depends = uses
                target = decl["Target"]
                m = instance_regex.match(target)
                item.instance_target = m.group(1) if m else target
            elif kind in ['structure', 'class']:
                item.def_depends = uses
                item.fields = decl["Fields"]

                # Detect structure extension
                #for field in item.fields:
                #    if field.startswith('to_'):
                #        target = field[3:]
                #        item.def_depends.append(target)

            else:
                logger.warning(f"Dropping: {name}")
    
    @classmethod
    def from_yaml(cls, path: str) -> 'LeanFile':
        lf = cls()
        lf.parse_lean_output(Path(path).read_text())
        return lf


class LeanLib:
    def __init__(self, name, path: Path = None,
                 files: Dict[Path, LeanFile] = None) -> None:
        self.name = name
        self.path = path
        self.files = files or dict()

    def __getitem__(self, key: Path) -> LeanFile:
        return self.files[key]

    def __setitem__(self, key: Path, value: LeanFile) -> None:
        self.files[key] = value

    def __delitem__(self, key: Path) -> None:
        del self.files[key]

    def __contains__(self, key: Path) -> bool:
        return key in self.files

    def get(self, key: Path, default: LeanFile = None) -> Optional[LeanFile]:
        return self.files.get(key, default)
