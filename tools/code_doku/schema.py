"""Bericht → Schema 2 des Leitfadens Code-Dokumentation (Typen, Properties, Methoden, Quelltext)."""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from typing import TYPE_CHECKING

from .constants import (
    CTOR_NAMES,
    DOC_PARAGRAPH_BREAK,
    DOT,
    DUPLICATE_MARK,
    EMPTY,
    ENCODING,
    ID_SEPARATOR,
    KIND_CLASS,
    KIND_CTOR,
    KIND_ENUM,
    KIND_METHOD,
    LAYER_INNER_TO_OUTER,
    NAMESPACE_ROOTS,
    NEWLINE,
    PRODUCT_NAME,
    PROP_ENUM,
    PY_PRIVATE_PREFIX,
    SCHEMA_VERSION,
    SLASH,
    SPACE,
    STEM_FILES,
    SUFFIX_PYTHON,
    SUFFIX_TS,
    VIS_PRIVATE,
    VIS_PUBLIC,
)
from .metrics import instability
from .schema_models import SchemaDocument, SchemaMember, SchemaMeta, SchemaMethod, SchemaType

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from pathlib import Path

    from .models import MethodInfo, ModuleInfo, PropertyInfo, Report, TypeInfo

type Index = Mapping[str, list[tuple[str, str]]]


def _summary(doc: str) -> str:
    """Erster Absatz eines Docstrings in einer Zeile."""
    return SPACE.join(doc.split(DOC_PARAGRAPH_BREAK, maxsplit=1)[0].split())


def _visibility(name: str) -> str:
    return VIS_PRIVATE if name.startswith(PY_PRIVATE_PREFIX) else VIS_PUBLIC


def _member(prop: PropertyInfo) -> SchemaMember:
    return SchemaMember(
        n=prop.name,
        type=prop.type,
        kind=prop.kind,
        acc=prop.access,
        init=prop.init,
        vis=prop.visibility,
        static=prop.static,
        l=prop.line_start,
        e=prop.line_end,
        doc=prop.doc,
    )


def _method(method: MethodInfo) -> SchemaMethod:
    return SchemaMethod(
        n=method.name,
        kind=KIND_CTOR if method.name in CTOR_NAMES else KIND_METHOD,
        sig=method.signature,
        l=method.line_start,
        e=method.line_end,
        loc=method.metrics.loc,
        cc=method.metrics.cc,
        vis=_visibility(method.name) if method.name not in CTOR_NAMES else VIS_PUBLIC,
        static=False,
        abstract=method.abstract,
        doc=_summary(method.doc),
    )


def namespace(module: ModuleInfo, layer: str) -> str:
    """Namensraum: Schicht + Modulpfad ohne Wurzelordner und Endung, mit Punkten."""
    path = module.path
    for root in NAMESPACE_ROOTS:
        path = path.removeprefix(root)
    stem = path.removesuffix(SUFFIX_PYTHON).removesuffix(SUFFIX_TS)
    return DOT.join([layer, *stem.split(SLASH)])


def module_name(module: ModuleInfo) -> str:
    """Name des Modul-Eintrags: Dateiname; bei `__init__`/`index` der Ordner."""
    parts = module.path.removesuffix(SUFFIX_PYTHON).removesuffix(SUFFIX_TS).split(SLASH)
    return parts[-2] if parts[-1] in STEM_FILES and len(parts) > 1 else parts[-1]


def _type_entry(module: ModuleInfo, info: TypeInfo) -> SchemaType:
    props = [_member(prop) for prop in info.props]
    is_enum = bool(props) and all(prop.kind == PROP_ENUM for prop in props)
    return SchemaType(
        id=EMPTY,
        name=info.name,
        ns=namespace(module, module.layer),
        project=module.layer,
        kind=KIND_ENUM if is_enum else info.kind,
        file=module.path,
        l=info.line_start,
        dl=info.line_start,
        e=info.line_end,
        doc=_summary(info.doc),
        bases=list(info.bases),
        vis=_visibility(info.name),
        static=False,
        loc=info.metrics.loc,
        cc=info.metrics.cc,
        mi=round(info.metrics.mi),
        tested=info.tested,
        props=props,
        meths=[_method(method) for method in info.methods],
    )


def _module_entry(module: ModuleInfo, lines: int) -> SchemaType:
    """Eintrag für die Funktionen und Konstanten auf oberster Ebene einer Datei."""
    own = sum(info.metrics.loc for info in module.types)
    functions = sum(method.metrics.loc for method in module.functions)
    return SchemaType(
        id=EMPTY,
        name=module_name(module),
        ns=namespace(module, module.layer),
        project=module.layer,
        kind=KIND_CLASS,
        file=module.path,
        l=1,
        dl=1,
        e=lines,
        doc=_summary(module.doc),
        bases=[],
        vis=VIS_PUBLIC,
        static=True,
        loc=max(functions, module.metrics.loc - own),
        cc=sum(method.metrics.cc for method in module.functions) or 1,
        mi=round(module.metrics.mi),
        tested=module.tested,
        props=[_member(prop) for prop in module.constants],
        meths=[_method(method) for method in module.functions],
    )


def _entries(module: ModuleInfo, lines: int) -> list[tuple[SchemaType, frozenset[str], bool]]:
    """Einträge eines Moduls mit ihren Bezeichnern und der Kennung „Modul-Eintrag“."""
    found = [(_type_entry(module, info), info.refs, False) for info in module.types]
    if module.functions or module.constants:
        found.append((_module_entry(module, lines), module.refs, True))
    return found


def _assign_ids(entries: Iterable[SchemaType]) -> None:
    """Eindeutige Kennungen: `Schicht|Name`, bei Namensgleichheit mit Namensraum, dann `#n`."""
    items = list(entries)
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for item in items:
        counts[item.project, item.name] += 1
    used: dict[str, int] = defaultdict(int)
    for item in items:
        name = item.name if counts[item.project, item.name] == 1 else f"{item.ns}{DOT}{item.name}"
        base = f"{item.project}{ID_SEPARATOR}{name}"
        used[base] += 1
        item.id = base if used[base] == 1 else f"{base}{DUPLICATE_MARK}{used[base]}"


def _index(
    modules: list[tuple[ModuleInfo, list[tuple[SchemaType, frozenset[str], bool]]]],
) -> Index:
    """Bezeichner → (Modulpfad, Kennung): Typnamen sowie Modul-, Funktions- und Konstantennamen."""
    index: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for module, entries in modules:
        for entry, _, is_module in entries:
            if is_module:
                names = {
                    module_name(module),
                    *(m.n for m in entry.meths),
                    *(p.n for p in entry.props),
                }
            else:
                names = {entry.name}
            for name in names:
                index[name].append((module.path, entry.id))
    return index


def _dependencies(
    module: ModuleInfo, entry: SchemaType, refs: frozenset[str], is_module: bool, index: Index
) -> list[str]:
    """Kennungen genutzter Einträge: Namen aus importierten Modulen (oder dem eigenen)."""
    allowed = {*module.deps} if is_module else {module.path, *module.deps}
    found = {
        target
        for name in refs
        for path, target in index.get(name, ())
        if path in allowed and target != entry.id
    }
    return sorted(found)


def _couple(types: list[SchemaType]) -> None:
    """Ca, Ce und Instabilität aus den Abhängigkeiten."""
    users: dict[str, int] = defaultdict(int)
    for item in types:
        for dep in item.deps:
            users[dep] += 1
    for item in types:
        item.ca, item.ce = users[item.id], len(item.deps)
        item.instab = instability(item.ca, item.ce)


def _layers(types: list[SchemaType]) -> list[str]:
    present = {item.project for item in types}
    return [layer for layer in LAYER_INNER_TO_OUTER if layer in present]


def _project_deps(types: list[SchemaType]) -> dict[str, list[str]]:
    by_id = {item.id: item for item in types}
    deps: dict[str, set[str]] = defaultdict(set)
    for item in types:
        deps[item.project].update(
            by_id[dep].project for dep in item.deps if by_id[dep].project != item.project
        )
    return {layer: sorted(found) for layer, found in sorted(deps.items())}


def build_schema(root: Path, report: Report) -> tuple[SchemaDocument, dict[str, str]]:
    """Schema-2-Daten und Quelltexte `{Datei: Text}` für die Vorlage des Leitfadens."""
    files: dict[str, str] = {}
    built = []
    for module in report.modules:
        text = (root / module.path).read_text(encoding=ENCODING)
        entries = _entries(module, text.count(NEWLINE) + 1)
        if entries:
            files[module.path] = text
            built.append((module, entries))
    types = [entry for _, entries in built for entry, _, _ in entries]
    _assign_ids(types)
    index = _index(built)
    for module, entries in built:
        for entry, refs, is_module in entries:
            entry.deps = _dependencies(module, entry, refs, is_module, index)
    _couple(types)
    types.sort(key=lambda item: (item.project, item.ns, item.name))
    meta = SchemaMeta(
        name=PRODUCT_NAME,
        version=report.version,
        prefix=EMPTY,
        layers=_layers(types),
        generated=dt.datetime.now(dt.UTC).date().isoformat(),
        tests=True,
    )
    document = SchemaDocument(SCHEMA_VERSION, meta, _project_deps(types), types)
    return document, files
