import base64
import datetime
import json
import logging
import math
import typing as t

from dataclasses import dataclass

from sqlalchemy import desc, func, asc, BinaryExpression, or_, and_, Select, select, ColumnElement, TextClause
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Template, Mailing, BaseModel
from database.paginator.anchor_store import retrieve_payload_by_token, store_payload_with_token, store_page_anchor_state

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)


def _b64encode_str(s: str) -> str:
    try:
        encoded = base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")
        logger.debug("Encoded string to base64 (len %d): %s...", len(encoded), encoded[:50])
        return encoded
    except Exception as e:
        logger.exception("Failed to base64-encode string")
        raise


def _b64decode_str(s: str) -> str:
    logger.debug("Decoding base64 cursor (len %d)", len(s) if s is not None else 0)
    try:
        pad = "=" * (-len(s) % 4)
        decoded = base64.urlsafe_b64decode((s + pad).encode()).decode()
        logger.debug("Decoded base64 cursor, len %d", len(decoded))
        return decoded
    except Exception as e:
        logger.exception("Failed to base64-decode cursor: %r", s)
        raise


def _serialize_single_value(v: t.Any) -> t.Dict[str, t.Any]:
    if v is None:
        logger.debug("Serializing value: None -> null")
        return {"t": "null", "v": None}
    if isinstance(v, bool):
        logger.debug("Serializing bool: %r", v)
        return {"t": "bool", "v": v}
    if isinstance(v, int):
        logger.debug("Serializing int: %d", v)
        return {"t": "int", "v": v}
    if isinstance(v, float):
        logger.debug("Serializing float: %f", v)
        return {"t": "float", "v": v}
    if isinstance(v, (datetime.datetime, datetime.date)):
        iso = v.isoformat()
        logger.debug("Serializing datetime: %s", iso)
        return {"t": "datetime", "v": iso}
    logger.debug("Serializing as str: %r", v)
    return {"t": "str", "v": str(v)}


def _deserialize_single_value(item: t.Dict[str, t.Any]) -> t.Any:
    type_ = item.get("t")
    value = item.get("v")
    logger.debug("Deserializing single value: type=%s, raw=%r", type_, value)
    try:
        if type_ == "null":
            return None
        if type_ == "bool":
            return bool(value)
        if type_ == "int":
            return int(value)
        if type_ == "float":
            return float(value)
        if type_ == "datetime":
            try:
                return datetime.datetime.fromisoformat(value)
            except Exception:
                return datetime.date.fromisoformat(value)
        return value
    except Exception as e:
        logger.exception("Failed to deserialize item: %r", item)
        raise


@dataclass
class AnchorColumn:
    col: t.Any
    order: str = "asc"

    def ordering_expr(self):
        return asc(self.col) if self.order == "asc" else desc(self.col)


class Paginator:
    _Model: "BaseModel"

    @staticmethod
    def _get_ordering(anchor_columns: t.Sequence[AnchorColumn], forward: bool) -> t.List[t.Any]:
        ordering = []
        for ac in anchor_columns:
            if forward:
                ordering.append(ac.ordering_expr())
            else:
                ordering.append(desc(ac.col) if ac.order == "asc" else asc(ac.col))
        logger.debug("Computed ordering for forward=%s: %s", forward, ordering)
        return ordering

    @staticmethod
    def _encode_anchor(values: t.Sequence[t.Any], page: t.Optional[int] = None) -> str:
        try:
            serialized = [_serialize_single_value(v) for v in values]
            payload: t.Dict[str, t.Any] = {"values": serialized}
            if page is not None:
                payload["page"] = int(page)
            raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
            encoded = _b64encode_str(raw)
            logger.info("Encoded anchor for page %s (values count %d)", page, len(values))
            return encoded
        except Exception:
            logger.exception("Failed to encode anchor values: %r", values)
            raise

    @staticmethod
    def _decode_anchor(cursor: str) -> t.Tuple[t.List[t.Any], t.Optional[int]]:
        logger.info("Decoding cursor (len %d)", len(cursor) if cursor else 0)
        try:
            raw = _b64decode_str(cursor)
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                values = [_deserialize_single_value(item) for item in parsed]
                logger.debug("Decoded cursor into list (len %d)", len(values))
                return values, None
            if isinstance(parsed, dict) and "values" in parsed:
                values = [_deserialize_single_value(item) for item in parsed["values"]]
                page = parsed.get("page")
                logger.debug("Decoded cursor into dict values (len %d), page=%r", len(values), page)
                if page is None:
                    return values, None
                try:
                    return values, int(page)
                except Exception:
                    logger.warning("Cursor page is not an int: %r", page)
                    return values, None
            raise ValueError("Invalid cursor format")
        except Exception:
            logger.exception("Failed to decode cursor: %r", cursor)
            raise

    @staticmethod
    def anchor_from_values(values: t.Sequence[t.Any], page: t.Optional[int] = None) -> str:
        return Paginator._encode_anchor(values, page=page)

    @staticmethod
    def decode_anchor_to_values(anchor: str) -> t.Tuple[t.List[t.Any], t.Optional[int]]:
        return Paginator._decode_anchor(anchor)

    @staticmethod
    def _build_keyset_filter(anchor_columns: t.Sequence[AnchorColumn], anchor_values: t.Sequence[t.Any], forward: bool,
                             is_deletion: bool) -> ColumnElement[bool]:
        if len(anchor_values) != len(anchor_columns):
            logger.error("anchor_values length %d doesn't match anchor_columns %d", len(anchor_values), len(anchor_columns))
            raise ValueError("anchor_values length must match number of anchor_columns")

        logger.debug("Building keyset filter forward=%s is_deletion=%s", forward, is_deletion)
        clauses = []
        for i in range(len(anchor_columns)):
            parts = []
            for j in range(i):
                parts.append(anchor_columns[j].col == anchor_values[j])

            col = anchor_columns[i].col
            val = anchor_values[i]

            col_order = anchor_columns[i].order
            use_gt = (col_order == "asc") == forward

            if use_gt:
                parts.append(col >= val if (is_deletion and not forward) else col > val)
            else:
                parts.append(col <= val if (is_deletion and not forward) else col < val)

            clauses.append(and_(*parts))
            logger.debug("Added clause for index %d (col=%s, order=%s, val=%r)", i, getattr(col, "name", repr(col)), col_order, val)
        filter_expr = or_(*clauses)
        logger.debug("Built keyset filter: %r", filter_expr)
        return filter_expr

    @classmethod
    async def paginate(
            cls,
            session: AsyncSession,
            base_stmt: Select,

            anchor_columns: t.Optional[t.Sequence[AnchorColumn]] = None,
            page_size: int | None = None,
            anchor: t.Optional[str] = None,
            forward: bool = True,
            compute_page_info: bool = True,
            is_deletion: bool = False,

            sort_by: t.Optional[t.List[t.Tuple[str, str]]] = None,
            sort_map: t.Optional[t.Dict[str, t.Any]] = None,
            default_sort_by: t.Optional[t.List[t.Tuple[str, str]]] = None,
    ) -> t.Tuple[t.List[t.Any], t.Optional[str], t.Optional[str], int, t.Optional[int]]:

        if page_size is None:
            page_size = getattr(cls, "PAGE_SIZE", 50)

        logger.info("Paginate called: page_size=%d anchor=%r forward=%s compute_page_info=%s is_deletion=%s",
                    page_size, anchor[:50] if anchor else None, forward, compute_page_info, is_deletion)

        if anchor_columns is None:
            if sort_by is None:
                sort_by = getattr(cls, "_DEFAULT_SORT_BY", None) or default_sort_by or []
            sort_map = sort_map or getattr(cls, "_SORT_MAP", {}) or {}

            anchor_columns_list: t.List[AnchorColumn] = []
            for field_name, direction in sort_by:
                column = sort_map.get(field_name)
                if column is not None:
                    anchor_columns_list.append(AnchorColumn(column, direction))
                    logger.debug("Added anchor column for field '%s' direction '%s'", field_name, direction)
                else:
                    logger.debug("Sort field '%s' ignored: not found in sort_map", field_name)
            model_id_col = getattr(cls._Model, "id", None)
            if model_id_col is not None and not any(getattr(ac.col, "key", None) == getattr(model_id_col, "key", None)
                                                    or getattr(ac.col, "name", None) == getattr(model_id_col, "name",
                                                                                                None)
                                                    for ac in anchor_columns_list):
                anchor_columns_list.append(AnchorColumn(model_id_col, "asc"))
                logger.debug("Added id anchor column as tiebreaker")

            anchor_columns = anchor_columns_list
        else:
            logger.debug("Using provided anchor_columns: %r", anchor_columns)

        stmt = base_stmt.order_by(*cls._get_ordering(anchor_columns, forward))

        incoming_page: t.Optional[int] = None
        if anchor:
            try:
                anchor_values, incoming_page = cls._decode_anchor(anchor)
                logger.info("Applying keyset filter from anchor, page=%r values=%r", incoming_page, anchor_values)
                keyset_filter = cls._build_keyset_filter(anchor_columns, anchor_values, forward, is_deletion)
                stmt = stmt.where(keyset_filter)
            except Exception:
                logger.exception("Invalid anchor cursor provided: %r", anchor)
                raise

        try:
            executed = await session.execute(stmt.limit(page_size + 1))
            rows = list(executed.scalars().all())
            logger.info("Executed statement, fetched rows=%d", len(rows))
        except Exception:
            logger.exception("Database execution failed for pagination")
            raise

        has_more = len(rows) > page_size
        if has_more:
            logger.debug("There are more rows than page_size (%d): has_more=True", page_size)
            rows = rows[:page_size]
        else:
            logger.debug("No more rows: total fetched %d", len(rows))

        if not forward:
            rows.reverse()
            logger.debug("Reversed rows because forward=False")

        current_page = incoming_page or 1

        next_cursor = None
        prev_cursor = None

        if rows:
            first_vals = [cls._get_col_value(rows[0], ac.col) for ac in anchor_columns]
            last_vals = [cls._get_col_value(rows[-1], ac.col) for ac in anchor_columns]
            logger.debug("First values: %r", first_vals)
            logger.debug("Last values: %r", last_vals)

            if forward:
                if has_more:
                    next_cursor = cls._encode_anchor(last_vals, current_page + 1)
                    logger.info("Next cursor for page %d generated after forward moving", current_page + 1)
                if current_page > 1:
                    prev_cursor = cls._encode_anchor(first_vals, current_page - 1)
                    logger.info("Prev cursor for page %d generated after forward moving", current_page - 1)
            else:
                next_cursor = cls._encode_anchor(last_vals, current_page + 1)
                logger.info("Next cursor for page %d generated after backward moving", current_page + 1)
                if has_more:
                    prev_cursor = cls._encode_anchor(first_vals, max(1, current_page - 1))
                    logger.info("Prev cursor for page %d generated after backward moving", max(1, current_page - 1))

        total_pages = None
        if compute_page_info:
            try:
                total = await cls._Model.count_total(session=session, base_stmt=base_stmt)
                total_pages = max(1, math.ceil(total / page_size))
                logger.info("Computed total pages: %d (total rows=%d page_size=%d)", total_pages, total, page_size)
            except Exception:
                logger.exception("Failed to compute page info (total pages)")
                raise

        return rows, prev_cursor, next_cursor, current_page, total_pages

    @staticmethod
    def _get_col_value(row: t.Any, col: t.Any) -> t.Any:
        try:
            val = getattr(row, col.key)
            logger.debug("Got column value by key '%s': %r", getattr(col, "key", None), val)
            return val
        except AttributeError:
            val = getattr(row, col.name, None)
            logger.debug("Got column value by name '%s': %r", getattr(col, "name", None), val)
            return val

    @classmethod
    async def get_next_page(
            cls,
            user_id: int,
            session: AsyncSession,
            filters: list[TextClause] | None = None,
            anchor: str | None = None,
            forward: bool = True,
            is_deletion: bool = False,
            is_back: bool = False,
    ):
        if anchor and not is_back and not is_deletion:
            anchor = await retrieve_payload_by_token(anchor, user_id)
        stmt = cls._Model.get_select_statement(filters=filters)
        entities, backward_anchor, forward_anchor, current_page, total_pages = await cls.paginate(
            session=session, base_stmt=stmt, anchor=anchor, forward=forward, is_deletion=is_deletion)
        if len(entities) == 0:
            return [], None, None, 0, 0
        ext_backward = None
        ext_forward = None
        if backward_anchor and current_page != 1:
            ext_backward = await store_payload_with_token(backward_anchor, user_id)
        if forward_anchor and current_page != total_pages:
            ext_forward = await store_payload_with_token(forward_anchor, user_id)
        await store_page_anchor_state(user_id, anchor, forward, current_page)
        return entities, ext_backward, ext_forward, current_page, total_pages

class TemplatePaginator(Paginator):
    _Model = Template
    PAGE_SIZE = 2
    _SORT_MAP = {
        "id": Template.id,
        "created_at": Template.created_at,
        "name": Template.name
    }
    _DEFAULT_SORT_BY = [("created_at", "desc")]



class MailingPaginator(Paginator):
    _Model = Mailing
    PAGE_SIZE = 2
    _SORT_MAP = {
        "id": Mailing.id,
        "created_at": Mailing.created_at,
    }
    _DEFAULT_SORT_BY = [("created_at", "desc")]


