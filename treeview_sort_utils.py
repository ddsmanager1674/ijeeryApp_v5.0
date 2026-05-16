"""
Tri centralisé pour ttk.Treeview — indicateurs ↕ ▲ ▼ (même style que Suivi présence).

Usage minimal (tri des lignes visibles) :
    from treeview_sort_utils import attach_tree_sort
    attach_tree_sort(self.tree, ["Col A", "Col B"], column_widths={...})

Usage avec cache / logique métier :
    ctrl = TreeSortController(self.tree, columns, sort_state=self._sort)
    ctrl.on_sort = lambda sk, desc: self._apply_filter()
    ctrl.wire_headings()
    # après chargement : ctrl.sort_rows(self._rows, sk, desc)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Callable, Iterable, Mapping, MutableMapping, Optional, Sequence, Union

ARROW_NEUTRAL = "↕"
ARROW_ASC = "▲"
ARROW_DESC = "▼"

SortState = dict[str, Any]
OnSortCallback = Callable[[str, bool], None]


def new_sort_state() -> SortState:
    return {"col": None, "desc": False}


def toggle_sort_state(state: SortState, sort_key: str) -> tuple[str, bool]:
    if state.get("col") == sort_key:
        state["desc"] = not state.get("desc", False)
    else:
        state["col"] = sort_key
        state["desc"] = False
    return sort_key, bool(state["desc"])


def heading_label(base_text: str, sort_key: str, sort_state: Mapping[str, Any]) -> str:
    if sort_state.get("col") == sort_key:
        arrow = ARROW_DESC if sort_state.get("desc") else ARROW_ASC
        return f"{base_text} {arrow}"
    return f"{base_text} {ARROW_NEUTRAL}"


def sort_key_for_value(
    val: Any,
    sort_type: str = "str",
    *,
    state_order: Optional[Sequence[str]] = None,
    label_to_state: Optional[Mapping[str, str]] = None,
    custom: Optional[Callable[[Any], Any]] = None,
) -> Any:
    if custom is not None:
        return custom(val)
    if sort_type == "int":
        try:
            return int(val)
        except (TypeError, ValueError):
            return 0
    if sort_type == "float":
        try:
            return float(val)
        except (TypeError, ValueError):
            return 0.0
    if sort_type == "fr_float":
        try:
            s = str(val or "").strip().replace(" ", "")
            if not s or s == "-":
                return 0.0
            s = s.replace("Ar", "").replace("ar", "").strip()
            return float(s.replace(".", "").replace(",", "."))
        except (TypeError, ValueError):
            return 0.0
    if sort_type == "date":
        if isinstance(val, datetime):
            return val.date()
        if isinstance(val, date):
            return val
        s = str(val or "").strip()
        if not s or s == "-":
            return date.min
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
            try:
                return datetime.strptime(s[:10], fmt).date()
            except ValueError:
                continue
        return s.lower()
    if sort_type == "datetime":
        if isinstance(val, datetime):
            return val
        s = str(val or "").strip()
        if not s:
            return datetime.min
        for fmt in ("%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
            try:
                return datetime.strptime(s[:19], fmt)
            except ValueError:
                continue
        return s.lower()
    if sort_type == "state":
        order = list(state_order or [])
        label_map = label_to_state or {}
        s = val if isinstance(val, str) else str(val or "")
        if s in order:
            return order.index(s)
        mapped = label_map.get(s)
        if mapped in order:
            return order.index(mapped)
        return 99
    return (str(val or "")).lower()


@dataclass
class TreeColumn:
    col_id: str
    sort_key: str = ""
    sort_type: str = "str"
    width: int = 100
    anchor: str = "w"
    text: str = ""
    sortable: bool = True
    minwidth: int = 30
    stretch: Optional[bool] = None

    def __post_init__(self):
        if not self.sort_key:
            self.sort_key = self.col_id
        if not self.text:
            self.text = self.col_id


def columns_from_tuples(
    specs: Sequence[tuple],
) -> list[TreeColumn]:
    """(col_id, width, anchor, sort_key, sort_type) comme Suivi présence."""
    out = []
    for spec in specs:
        if len(spec) >= 5:
            col_id, width, anchor, sort_key, sort_type = spec[:5]
            out.append(
                TreeColumn(
                    col_id=col_id,
                    width=int(width),
                    anchor=str(anchor),
                    sort_key=str(sort_key),
                    sort_type=str(sort_type),
                )
            )
        elif len(spec) >= 2:
            out.append(TreeColumn(col_id=spec[0], width=int(spec[1])))
        else:
            out.append(TreeColumn(col_id=spec[0]))
    return out


def _row_value(row: Any, sort_key: str, col: TreeColumn) -> Any:
    if isinstance(row, dict):
        return row.get(sort_key, row.get(col.col_id))
    if isinstance(row, (list, tuple)) and sort_key.isdigit():
        return row[int(sort_key)]
    return row


class TreeSortController:
    """Contrôleur de tri pour un Treeview (en-têtes + données)."""

    def __init__(
        self,
        tree,
        columns: Sequence[Union[TreeColumn, tuple]],
        *,
        sort_state: Optional[SortState] = None,
        state_order: Optional[Sequence[str]] = None,
        label_to_state: Optional[Mapping[str, str]] = None,
        value_getters: Optional[Mapping[str, Callable[[Any], Any]]] = None,
    ):
        self.tree = tree
        self.columns = [
            c if isinstance(c, TreeColumn) else columns_from_tuples([c])[0]
            for c in columns
        ]
        self.sort_state = sort_state if sort_state is not None else new_sort_state()
        self.state_order = state_order
        self.label_to_state = label_to_state
        self.value_getters = value_getters or {}
        self.on_sort: Optional[OnSortCallback] = None

    def _col_by_sort_key(self, sort_key: str) -> Optional[TreeColumn]:
        for c in self.columns:
            if c.sort_key == sort_key:
                return c
        return None

    def refresh_headings(self) -> None:
        for col in self.columns:
            label = heading_label(col.text, col.sort_key, self.sort_state)
            try:
                self.tree.heading(col.col_id, text=label)
            except Exception:
                pass

    def wire_headings(self, *, configure_columns: bool = True) -> None:
        for col in self.columns:
            if configure_columns:
                kw = {"width": col.width, "anchor": col.anchor, "minwidth": col.minwidth}
                if col.stretch is not None:
                    kw["stretch"] = col.stretch
                try:
                    self.tree.column(col.col_id, **kw)
                except Exception:
                    pass
            if col.sortable:
                self.tree.heading(
                    col.col_id,
                    text=heading_label(col.text, col.sort_key, self.sort_state),
                    command=lambda sk=col.sort_key: self.click(sk),
                )
            else:
                self.tree.heading(col.col_id, text=col.text)

    def click(self, sort_key: str) -> tuple[str, bool]:
        sk, desc = toggle_sort_state(self.sort_state, sort_key)
        self.refresh_headings()
        if self.on_sort:
            self.on_sort(sk, desc)
        return sk, desc

    def _key_fn(self, sort_key: str) -> Callable[[Any], Any]:
        col = self._col_by_sort_key(sort_key)
        stype = col.sort_type if col else "str"
        custom = self.value_getters.get(sort_key)

        def fn(row):
            if custom:
                return custom(row)
            val = _row_value(row, sort_key, col) if col else row
            return sort_key_for_value(
                val,
                stype,
                state_order=self.state_order,
                label_to_state=self.label_to_state,
            )

        return fn

    def sort_rows(
        self,
        rows: list,
        sort_key: Optional[str] = None,
        desc: Optional[bool] = None,
        *,
        in_place: bool = True,
    ) -> list:
        sk = sort_key if sort_key is not None else self.sort_state.get("col")
        if not sk:
            return rows
        d = bool(desc) if desc is not None else bool(self.sort_state.get("desc"))
        key_fn = self._key_fn(sk)
        if in_place:
            rows.sort(key=key_fn, reverse=d)
            return rows
        return sorted(rows, key=key_fn, reverse=d)

    def sort_visible(
        self,
        sort_key: Optional[str] = None,
        desc: Optional[bool] = None,
        *,
        alt_tags: tuple[str, str] = ("even", "odd"),
    ) -> None:
        col = self._col_by_sort_key(
            sort_key if sort_key is not None else self.sort_state.get("col") or ""
        )
        if not col:
            return
        d = bool(desc) if desc is not None else bool(self.sort_state.get("desc"))
        stype = col.sort_type
        sk = col.sort_key
        custom = self.value_getters.get(sk)

        items = [(self.tree.set(iid, col.col_id), iid) for iid in self.tree.get_children("")]
        items.sort(
            key=lambda x: (
                custom(x[0])
                if custom
                else sort_key_for_value(
                    x[0],
                    stype,
                    state_order=self.state_order,
                    label_to_state=self.label_to_state,
                )
            ),
            reverse=d,
        )
        for idx, (_v, iid) in enumerate(items):
            self.tree.move(iid, "", idx)
            if alt_tags:
                self.tree.item(iid, tags=(alt_tags[0] if idx % 2 == 0 else alt_tags[1],))

    def after_click_sort_rows(
        self,
        rows: list,
        refresh_callback: Callable[[], None],
        *,
        empty_sort_visible: bool = True,
    ) -> None:
        """Helper : tri du cache puis rafraîchissement (Suivi présence)."""
        sk = self.sort_state.get("col")
        if rows and sk:
            self.sort_rows(rows, sk, self.sort_state.get("desc"))
            refresh_callback()
        elif empty_sort_visible and sk:
            self.sort_visible(sk, self.sort_state.get("desc"))


def attach_tree_sort(
    tree,
    column_ids: Sequence[str],
    *,
    sort_state: Optional[SortState] = None,
    column_widths: Optional[Mapping[str, int]] = None,
    column_anchors: Optional[Mapping[str, str]] = None,
    column_types: Optional[Mapping[str, str]] = None,
    sortable: Optional[Mapping[str, bool]] = None,
    on_sort: Optional[OnSortCallback] = None,
    configure_columns: bool = True,
    value_getters: Optional[Mapping[str, Callable[[Any], Any]]] = None,
) -> TreeSortController:
    """
    Branche le tri sur un Treeview déjà défini (colonnes = identifiants Treeview).
    Par défaut, tri des lignes visibles au clic.
    """
    specs = []
    for cid in column_ids:
        specs.append(
            TreeColumn(
                col_id=cid,
                sort_key=cid,
                sort_type=(column_types or {}).get(cid, "str"),
                width=(column_widths or {}).get(cid, 100),
                anchor=(column_anchors or {}).get(cid, "w"),
                sortable=(sortable or {}).get(cid, True) if sortable else True,
            )
        )
    ctrl = TreeSortController(
        tree,
        specs,
        sort_state=sort_state,
        value_getters=value_getters,
    )
    if on_sort is not None:
        ctrl.on_sort = on_sort
    else:
        ctrl.on_sort = lambda sk, desc: ctrl.sort_visible(sk, desc)
    ctrl.wire_headings(configure_columns=configure_columns)
    return ctrl
