"""
Python classes storing information about Lean libraries
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from copy import deepcopy
import pickle

from yaml import safe_load
import networkx as nx
from networkx.drawing.nx_pydot import graphviz_layout

def strip_name(name):
    """ Remove the last component of a Lean name."""
    return '.'.join(name.split('.')[:-1])

# Lean names ending with the following are auxilliary definitions
AUX_DEF_SUFFIX = ('.rec', '.brec', '.brec_on', '.mk', '.rec_on', '.inj_on',
                  '.has_sizeof_inst', '.no_confusion_type', '.no_confusion',
                  '.cases_on', '.inj_arrow', '.sizeof', '.inj',
                  '.inj_eq', '.sizeof_spec', '.drec', '.dcases_on',
                  '.drec_on', '.below', '.ibelow', '.binduction_on',)

@dataclass
class LeanDecl:
    """ A Lean declaration """
    # pylint: disable=too-many-instance-attributes
    name: str
    filename: str
    line_nb: int = 0
    kind: str = ''
    is_inductive: bool = False
    is_structure: bool = False
    is_structure_field: bool = False
    is_class: bool = False
    is_instance: bool = False
    is_recursor: bool = False
    is_constructor: bool = False
    Type: str = ''
    type_uses_proofs: Set[str] = field(default_factory=set)
    type_uses_others: Set[str] = field(default_factory=set)
    type_size: int = 0
    type_dedup_size: int = 0
    type_pp_size: int = 0
    Value: str = ''
    value_uses_proofs: Set[str] = field(default_factory=set)
    value_uses_others: Set[str] = field(default_factory=set)
    value_size: int = 0
    value_dedup_size: int = 0
    value_pp_size: int = 0
    target_class: Optional[str] = None
    parent: Optional[str] = None
    fields: Optional[List[str]] = None

    @classmethod
    def from_dict(cls, d):
        """ Create a LeanDecl from a dictionary coming from a YaML file. """
        decl = cls(name=d['Name'],
                   filename=d['File'],
                   line_nb=d['Line'],
                   kind=d['Kind'],
                   is_inductive=d['Modifiers']['inductive'],
                   is_structure=d['Modifiers']['structure'],
                   is_structure_field=d['Modifiers']['structure_field'],
                   is_class=d['Modifiers']['class'],
                   is_instance=d['Modifiers']['instance'],
                   is_recursor=d['Modifiers']['is_recursor'],
                   is_constructor=d['Modifiers']['is_constructor'],
                   Type=d['Type'],
                   type_uses_proofs=set(d['Type uses proofs']),
                   type_uses_others=set(d['Type uses others']),
                   type_size=d['Type size'],
                   type_dedup_size=d['Type dedup size'],
                   type_pp_size=d['Type pp size'],
                   Value=d['Value'],
                   value_uses_proofs=set(d['Value uses proofs']),
                   value_uses_others=set(d['Value uses others']),
                   value_size=d['Value size'],
                   value_dedup_size=d['Value dedup size'],
                   value_pp_size=d['Value pp size'],
                   target_class=d['Target class'],
                   parent=d['Parent'],
                   fields=d['Fields'])
        if decl.is_structure_field:
            # Remove the trailing ".mk"
            decl.parent = strip_name(decl.parent)
        elif decl.is_constructor:
            decl.parent = strip_name(decl.name)
        return decl

    @property
    def user_kind(self) -> str:
        """ A heuristic more informative kind of declaration. """
        if self.is_class:
            return 'class'
        if self.is_instance:
            return 'instance'
        if self.is_structure:
            return 'structure'
        if self.is_inductive:
            return 'inductive'
        return self.kind or 'unknown'

    @property
    def type_uses(self) -> Set[str]:
        """ Aggregated type declaration uses. """
        return self.type_uses_others.union(self.type_uses_proofs)

    @property
    def value_uses(self) -> List[str]:
        """ Aggregated value declaration uses. """
        return self.value_uses_others.union(self.value_uses_proofs)

    @property
    def uses(self) -> Set[str]:
        """ Aggregated uses. """
        return self.type_uses.union(self.value_uses)

    def __str__(self):
        return str(self.name)

@dataclass
class LeanLib:
    """ A Lean library, seen as a collection of Lean declarations."""
    name: str
    items: Dict[str, LeanDecl] = field(default_factory=dict)

    def __getitem__(self, key: str) -> LeanDecl:
        return self.items[key]

    def __setitem__(self, key: str, value: LeanDecl) -> None:
        self.items[key] = value

    def __delitem__(self, key: str) -> None:
        del self.items[key]

    def __contains__(self, key: str) -> bool:
        return key in self.items

    def __iter__(self):
        return iter(self.items.values())

    def get(self, key: str, default: LeanDecl = None) -> Optional[LeanDecl]:
        """ Return the Lean item whose name is "key", or the default value. """
        return self.items.get(key, default)

    @classmethod
    def from_yaml(cls, name: str, filename: str) -> 'LeanLib':
        """ Create a Lean library from a name and a Lean-exported YaML file path. """
        lib = cls(name)
        with open(filename, 'rb') as f:
            lean_output = f.read()
        for decl in safe_load(lean_output):
            lib[decl["Name"]] = LeanDecl.from_dict(decl)

        # Now aggregate data about inductives using constructors
        for decl in filter(lambda d: d.is_constructor, lib):
            parent = lib[decl.parent]
            parent.type_uses_proofs.update(decl.type_uses_proofs)
            parent.type_uses_others.update(decl.type_uses_others)
            parent.value_uses_proofs.update(decl.value_uses_proofs)
            parent.value_uses_others.update(decl.value_uses_others)
            def rself(s):
                """ remove self from uses."""
                s.difference_update(set([decl.parent]))
            rself(parent.type_uses_proofs)
            rself(parent.type_uses_others)
            rself(parent.value_uses_proofs)
            rself(parent.value_uses_others)
            parent.type_size += decl.type_size
            parent.type_dedup_size += decl.type_dedup_size
            parent.type_pp_size += decl.type_pp_size
            parent.value_size += decl.value_size
            parent.value_dedup_size += decl.value_dedup_size
            parent.value_pp_size += decl.value_pp_size

            lib[parent.name] = parent
        return lib


    @staticmethod
    def load_dump(name: str) -> 'LeanLib':
        """ Create a Lean library from a pickle dump filename. """
        with open(name, 'rb') as f:
            return pickle.load(f)

    def dump(self, name):
        """ Pickle dump a Lean library to a named file. """
        with open(name, 'wb') as f:
            pickle.dump(self, f)



COLORS = {'theorem':   {'a': 1, 'r': 9, 'b': 200, 'g': 200},
          'lemma':   {'a': 1, 'r': 9, 'b': 200, 'g': 200},
          'definition': {'a': 1, 'r': 9, 'b': 236, 'g': 173},
          'structure': {'a': 1, 'r': 9, 'b': 236, 'g': 173},
          'constant': {'a': 1, 'r': 9, 'b': 236, 'g': 173},
          'axiom': {'a': 1, 'r': 9, 'b': 236, 'g': 173},
          'class': {'a': 1, 'r': 9, 'b': 236, 'g': 173},
          'inductive': {'a': 1, 'r': 9, 'b': 236, 'g': 173},
          'instance': {'a': 1, 'r': 9, 'b': 136, 'g': 253},
          'unknown': {'a': 1, 'r': 10, 'b': 10, 'g': 10}}


class LeanDeclGraph(nx.DiGraph):
    """ A Lean declarations graph. """
    @classmethod
    def from_lib(cls, lean: LeanLib, **kwargs) -> 'LeanDeclGraph':
        """ Creates a graph from a LeanLib object """
        graph = cls(**kwargs)
        lib = deepcopy(lean)

        # Let us now drop some unwanted declarations from the lib
        for name, item in lean.items.items():
            if (name.endswith(AUX_DEF_SUFFIX) or item.is_structure_field or
                    item.is_constructor or item.is_recursor):
                lib.items.pop(name)

        # before adding nodes and edges
        for name, item in lib.items.items():
            graph.add_node(name)
            graph.nodes[name]['id'] = item.name
            graph.nodes[name]['label'] = item.name
            graph.nodes[name]['kind'] = item.user_kind
            graph.nodes[name]['viz'] = {'color': COLORS[item.user_kind]}

            for dep in item.uses:
                if dep in lib:
                    graph.add_edge(dep, name)
                else:
                    stripped = '.'.join(dep.split('.')[:-1])
                    if stripped != name and stripped in lib:
                        graph.add_edge(stripped, name)
        return graph


    def layout(self, root):
        """ Slowly sets node positions using graphviz, with given root. """
        for node, (x, y) in graphviz_layout(self, 'dot', root).items():
            self.nodes[node]['viz']['position'] = {'x': x, 'y': y, 'z': 0}

    def prune_foundations(self):
        """ Remove nodes that are too dependant on foundations and artificially
           create hubs. """
        self.remove_nodes_from([
            'eq', 'eq.refl', 'eq.mpr', 'eq.rec', 'eq.trans', 'eq.subst',
            'eq.symm', 'eq_self_iff_true', 'eq.mp',
            'ne', 'not', 'true', 'false', 'trivial', 'rfl',
            'congr', 'congr_arg', 'propext', 'funext',
            'and', 'and.intro', 'and.elim',
            'or', 'or.inl', 'or.inr', 'or.elim',
            'iff', 'iff.intro', 'iff.mp', 'iff.mpr', 'iff_true_intro',
            'iff_self', 'iff.refl', 'iff.rfl',
            'classical.choice', 'classical.indefinite_description',
            'classical.some', 'nonempty',
            'decidable', 'decidable_eq', 'decidable_rel',
            'imp_congr_eq',
            'auto_param',
            'Exists', 'Exists.intro', 'subtype', 'subtype.val',
            'id_rhs',
            'set', 'set.has_mem', 'set_of',
            'prod', 'prod.fst', 'prod.snd', 'prod.mk',
            'coe', 'coe_to_lift', 'coe_base', 'coe_fn', 'coe_sort', 'coe_t',
            'coe_trans'])

    def component_of(self, key):
        """ The subgraph containing everything needed to define key. """
        return self.subgraph(nx.ancestors(self, key).union([key]))

    def write(self, name: str):
        """ Saves declaration graph in GEXF format in a file named name. """
        nx.write_gexf(self, name)
