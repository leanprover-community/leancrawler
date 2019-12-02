import networkx as nx

from leancrawler import LeanItemModel, DependanceModel
from leancrawler.python_storage import logger, LeanFile

COLORS = {'theorem':   {'a': 1, 'r': 9, 'b': 200, 'g': 200},
          'lemma':   {'a': 1, 'r': 9, 'b': 200, 'g': 200},
          'definition': {'a': 1, 'r': 9, 'b': 236, 'g': 173},
          'structure': {'a': 1, 'r': 9, 'b': 236, 'g': 173},
          'constant': {'a': 1, 'r': 9, 'b': 236, 'g': 173},
          'axiom': {'a': 1, 'r': 9, 'b': 236, 'g': 173},
          'class': {'a': 1, 'r': 9, 'b': 236, 'g': 173},
          'inductive': {'a': 1, 'r': 9, 'b': 236, 'g': 173},
          'instance': {'a': 1, 'r': 9, 'b': 136, 'g': 253},
          'unknown': {'a': 1,  'r': 10, 'b': 10, 'g': 10}}


class ItemGraph(nx.DiGraph):
    @classmethod
    def from_db(cls, db, known_kind_only=True, **kwargs):
        graph = cls(**kwargs)
        for item in LeanItemModel.select():
            if known_kind_only and item.kind == 'unknown':
                continue
            graph.add_node(item)
            graph.nodes[item]['id'] = item.name
            graph.nodes[item]['label'] = item.name
            graph.nodes[item]['kind'] = item.kind
            graph.nodes[item]['size'] = item.size + item.proof_size
            graph.nodes[item]['viz'] = {'color': COLORS[item.kind]}

        for dep in DependanceModel.select():
            if known_kind_only and dep.used.kind == 'unknown':
                continue

            graph.add_edge(dep.used, dep.user)
        return graph

    @classmethod
    def from_py(cls, lean: LeanFile, **kwargs):
        graph = cls(**kwargs)
        for name, item in lean.items.items():
            graph.add_node(name)
            graph.nodes[name]['id'] = item.name
            graph.nodes[name]['label'] = item.name
            graph.nodes[name]['kind'] = item.kind
            graph.nodes[name]['viz'] = {'color': COLORS[item.kind]}

            for dep in item.def_depends + item.proof_depends:
                if dep in lean:
                    graph.add_edge(dep, name)
                else:
                    stripped =  '.'.join(dep.split('.')[:-1])
                    if stripped != name and stripped in lean:
                        graph.add_edge(stripped, name)
        return graph

    def component_of(self, key):
        return self.subgraph(nx.ancestors(self, key).union([key]))

    def write(self, name: str):
        nx.write_gexf(self, name)
