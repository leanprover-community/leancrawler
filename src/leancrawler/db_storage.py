"""
Databases models of the LeanCrawler. All paths in database are relative.
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from peewee import (SqliteDatabase, Model,
                    CharField, IntegerField, ForeignKeyField, DateTimeField)

from leancrawler.python_storage import LeanLib, LeanFile, LeanItem, logger


db = SqliteDatabase(None)


class BaseModel(Model):
    class Meta:
        database = db


class LeanLibModel(BaseModel):
    name = CharField(unique=True)

    @classmethod
    def from_path(cls, name: str, path: Path, prelude: bool = False):
        """Get a LeanLibModel object from its path, fetching files either from
           database or source."""
        try:
            lean_lib_m = cls.get(name=name)
        except cls.DoesNotExist:
            lean_lib_m = cls.create(name=name)

        # Delete non-existing files from db
        for lean_file_m in lean_lib_m.files:
            if not (path/lean_file_m.path).exists():
                lean_file_m.delete().execute()
        #logger.debug(f"Will copy deps.lean to {path / 'src'}")
        #shutil.copy(str(Path(__file__).parent / 'deps.lean'), path / 'src')

        for file_path in path.glob('**/*.lean'):
            if file_path.name == 'deps.lean':
                continue
            mtime = os.path.getmtime(file_path)
            rel_path = str(file_path.relative_to(path))

            # A file may need update either because it's not in the database or
            # because it has been modified since last visit.
            needs_update = False
            try:
                lean_file_m = LeanFileModel.get(path=rel_path)
                if lean_file_m.visited.timestamp() < mtime:
                    needs_update = True
            except LeanFileModel.DoesNotExist:
                lean_file_m = LeanFileModel.create(lib=lean_lib_m,
                                                   path=rel_path)
                needs_update = True

            if needs_update:
                lean_file_m.read(path, prelude)
            else:
                logger.debug(f"No need to update {rel_path}")
        #(path/'src'/'deps.lean').unlink()
        return lean_lib_m

    def to_py(self, path: Path) -> LeanLib:
        lib = LeanLib(name=self.name, path=path)
        for lf_m in self.files:
            logger.debug(f"Importing {lf_m.path}")
            lib.files[Path(lf_m.path)] = lf_m.to_py()
        return lib


class LeanFileModel(BaseModel):
    lib = ForeignKeyField(LeanLibModel, backref='files', null=True)
    path = CharField(unique=True)
    visited = DateTimeField(default=datetime.now)
    nb_lines = IntegerField(default=0)

    def read(self, path: Path, prelude: bool = False) -> None:
        logger.debug(f"LeanFileModel reading {path}")
        LeanItemModel.delete().where(LeanItemModel.leanfile == self)
        ImportModel.delete().where(ImportModel.importer == self)
        lf = LeanFile.from_path(path/self.path, root=path, prelude=prelude)
        for imported in lf.imports:
            imp_path = imported.replace('.', '/') + '.lean'
            other_file_m = LeanFileModel.get_or_create(path=imp_path)[0]
            ImportModel.create(importer=self, imported=other_file_m)
        for key, val in lf.items.items():
            LeanItemModel.from_py(self, val)

        self.nb_lines = lf.nb_lines
        self.save()

    def to_py(self) -> LeanFile:
        return LeanFile(Path(path=self.path),
                        visited=self.visited,
                        nb_lines=self.nb_lines,
                        imports=[f.imported.path for f in self.imports],
                        items={i.name: i.to_py() for i in self.items})


class ImportModel(BaseModel):
    importer = ForeignKeyField(LeanFileModel, backref='imports')
    imported = ForeignKeyField(LeanFileModel, backref='imported_by')


class NameSpaceModel(BaseModel):
    fullname = CharField(unique=True)


class LeanItemModel(BaseModel):
    kind = CharField(max_length=10, default='unknown')
    name = CharField(unique=True)
    #  null ⇔ root namespace
    namespace = ForeignKeyField(NameSpaceModel, null=True)
    leanfile = ForeignKeyField(LeanFileModel, backref='items', null=True)
    line_nb = IntegerField(default=0)
    size = IntegerField(default=0)
    proof_size = IntegerField(default=0)

    def to_py(self) -> LeanItem:
        def_deps = []
        pf_deps = []
        for item in self.deps:
            if item.kind == 'def':
                def_deps.append(item.used.name)
            else:
                pf_deps.append(item.used.name)
        return LeanItem(self.kind,
                        name=self.name,
                        size=self.size,
                        line_nb=self.line_nb,
                        def_depends=def_deps,
                        proof_size=self.proof_size,
                        proof_depends=pf_deps)

    @staticmethod
    def from_py(lf_m: LeanFileModel, item: LeanItem) -> 'LeanItemModel':
        li_m, _ = LeanItemModel.get_or_create(name=item.name)

        li_m.kind = item.kind
        li_m.name = item.name
        li_m.namespace = NameSpaceModel.get_or_create(
            fullname='.'.join(item.namespace))[0]
        li_m.leanfile = lf_m
        li_m.line_nb = item.line_nb or 0
        li_m.size = item.size
        li_m.proof_size = item.proof_size
        li_m.save()

        for dep in item.def_depends:
            try:
                used_m = LeanItemModel.get(name=dep)
            except LeanItemModel.DoesNotExist:
                used_m = LeanItemModel.create(name=dep)
            DependanceModel.create(kind='def',
                                   user=li_m,
                                   used=used_m)
        for dep in item.proof_depends:
            try:
                used_m = LeanItemModel.get(name=dep)
            except LeanItemModel.DoesNotExist:
                used_m = LeanItemModel.create(kind='unknown', name=dep)
            DependanceModel.create(kind='proof',
                                   user=li_m,
                                   used=used_m)
        for field in item.fields:
            StructureFieldModel.create(name=field, parent=li_m)
        if item.kind == 'instance':
            try:
                class_m = LeanItemModel.get(name=item.instance_target)
            except LeanItemModel.DoesNotExist:
                class_m = LeanItemModel.create(name=item.instance_target)
            InstanceModel.create(instance=li_m, target=class_m)
        return li_m


class StructureFieldModel(BaseModel):
    name = CharField()
    parent = ForeignKeyField(LeanItemModel, backref='fields')


class DependanceModel(BaseModel):
    kind = CharField(max_length=5)  # 'def' or 'proof'
    user = ForeignKeyField(LeanItemModel, backref='deps')
    used = ForeignKeyField(LeanItemModel, backref='used_by')


class InstanceModel(BaseModel):
    instance = ForeignKeyField(LeanItemModel, backref='classes')
    target = ForeignKeyField(LeanItemModel, backref='instances')


def create_db(name: str):
    db.init(name)
    db.create_tables([LeanLibModel, LeanFileModel, LeanItemModel, ImportModel,
                      NameSpaceModel, StructureFieldModel, DependanceModel,
                      InstanceModel])


def use_db(name: str):
    db.init(name)
