#!/usr/bin/env python3
"""Validate the current spatial coordinate evidence contract.

The validator is local and read-only. It guards D-291 business semantics; it
does not geocode, call a map or route API, render a map, decide competitors,
or grade evidence for customer-facing use.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "spatial_coordinate_evidence.v2"
OBJECT_SET_OWNER = "downstream_consumer"
PROJECT_LOCATION_MODEL = "single_map_marker_centerpoint"
LARGE_RESOURCE_LOCATION_MODEL = "geometry_for_perpendicular_distance"
ROUTE_SNAP = "provider_auto_snap_from_centerpoints"
FOUR_SIDE_RENDERING_OWNER = "downstream_consumer"
FOUR_SIDE_OUTLINE_USE = "downstream_approximate_outline_only"

OBJECT_ROLES = {
    "case_project",
    "competitor",
    "amenity_compact",
    "amenity_large_or_elongated",
    "reference_center",
}
POINT_ROLES = {
    "case_project",
    "competitor",
    "amenity_compact",
    "reference_center",
}
DISTANCE_TYPES = {
    "straight_line",
    "walking_route",
    "driving_route",
    "perpendicular_shortest_straight",
}
ROUTE_DISTANCE_TYPES = {"walking_route", "driving_route"}
BARRIER_TYPES = {
    "arterial_road",
    "expressway",
    "river",
    "elevation",
    "wall",
    "closed_passage",
    "park_or_large_open_space",
    "none",
}
WALKING_EFFECTS = {
    "more_convenient",
    "less_convenient",
    "neutral",
    "not_assessed",
}
RELATIVE_FINDINGS = {
    "case_distance_advantage",
    "case_walking_convenience_advantage",
    "no_clear_case_advantage",
    "not_assessed",
}

FORBIDDEN_LEGACY_KEYS = {
    "actual_entrance",
    "actual_entrance_point",
    "entrance",
    "entrance_point",
    "entrance_distance",
    "sales_office",
    "sales_office_point",
    "anchor_points",
    "alternate_centerpoints",
    "multiple_project_points",
    "project_boundary",
    "redline_polygon",
    "nearest_boundary",
    "customer_facing_map_ready",
    "formal_map_signed_off",
    "render_manifest",
    "rendered_map",
}


def _error(code: str, path: str, message: str) -> dict[str, str]:
    return {"code": code, "path": path, "message": message}


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _nonnegative_number(value: Any) -> bool:
    return _finite_number(value) and value >= 0


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(_nonempty_string(item) for item in value)


def _clockwise_coordinate_order(coordinates: list[dict[str, Any]]) -> bool:
    """Use signed area to verify the supplied corner sequence is clockwise."""

    if len(coordinates) != 4:
        return False
    points: list[tuple[float, float]] = []
    for coordinate in coordinates:
        if not isinstance(coordinate, dict):
            return False
        longitude = coordinate.get("longitude")
        latitude = coordinate.get("latitude")
        if not _finite_number(longitude) or not _finite_number(latitude):
            return False
        points.append((float(longitude), float(latitude)))
    if len(set(points)) != 4:
        return False
    signed_twice_area = sum(
        points[index][0] * points[(index + 1) % 4][1]
        - points[(index + 1) % 4][0] * points[index][1]
        for index in range(4)
    )
    return signed_twice_area < 0


def _contains_absolute_exclusivity(value: Any) -> bool:
    serialized = json.dumps(value, ensure_ascii=False).casefold()
    return "独占" in serialized or "exclusive" in serialized


def _walk_keys(value: Any, path: str = "$") -> Iterable[tuple[str, str]]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            yield key, child_path
            yield from _walk_keys(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_keys(child, f"{path}.{index}")


def _validate_coordinate(
    coordinate: Any,
    path: str,
    errors: list[dict[str, str]],
) -> bool:
    if not isinstance(coordinate, dict):
        errors.append(_error("invalid_coordinate", path, "坐标必须为 longitude/latitude 对象"))
        return False
    longitude = coordinate.get("longitude")
    latitude = coordinate.get("latitude")
    if not _finite_number(longitude) or not -180 <= longitude <= 180:
        errors.append(_error("invalid_coordinate", f"{path}.longitude", "经度必须在 -180 到 180 之间"))
        return False
    if not _finite_number(latitude) or not -90 <= latitude <= 90:
        errors.append(_error("invalid_coordinate", f"{path}.latitude", "纬度必须在 -90 到 90 之间"))
        return False
    return True


def _require_object(data: dict[str, Any], key: str, path: str, errors: list[dict[str, str]]) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        errors.append(_error("required_object", f"{path}.{key}", "字段必须为对象"))
        return {}
    return value


def _require_list(data: dict[str, Any], key: str, path: str, errors: list[dict[str, str]]) -> list[Any]:
    value = data.get(key)
    if not isinstance(value, list):
        errors.append(_error("required_list", f"{path}.{key}", "字段必须为数组"))
        return []
    return value


def validate_contract(data: Any) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if not isinstance(data, dict):
        return [_error("contract_not_object", "$", "合同根节点必须为对象")]

    for key, path in _walk_keys(data):
        if key.casefold() in FORBIDDEN_LEGACY_KEYS:
            errors.append(
                _error(
                    "forbidden_legacy_spatial_field",
                    path,
                    f"D-291 现行空间包禁止字段 {key!r}",
                )
            )

    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(
            _error(
                "schema_version_mismatch",
                "$.schema_version",
                f"schema_version 必须为 {SCHEMA_VERSION}",
            )
        )
    if not _nonempty_string(data.get("task_id")):
        errors.append(_error("required_nonempty_string", "$.task_id", "task_id 必须为非空字符串"))

    ownership = _require_object(data, "input_ownership", "$", errors)
    case_project_id = ownership.get("case_project_id")
    if not _nonempty_string(case_project_id):
        errors.append(
            _error(
                "required_nonempty_string",
                "$.input_ownership.case_project_id",
                "必须给出本案对象 ID",
            )
        )
        case_project_id = ""
    if ownership.get("object_set_owner") != OBJECT_SET_OWNER:
        errors.append(
            _error(
                "object_set_owner_mismatch",
                "$.input_ownership.object_set_owner",
                "竞品与配套对象清单必须由调用方／下游提供",
            )
        )

    ownership_lists: dict[str, list[str]] = {}
    for key in ("competitor_ids", "resource_ids", "reference_ids"):
        value = ownership.get(key)
        if not _string_list(value):
            errors.append(
                _error(
                    "caller_object_id_list_invalid",
                    f"$.input_ownership.{key}",
                    "对象清单必须是非空字符串组成的数组；允许空数组",
                )
            )
            ownership_lists[key] = []
        else:
            ownership_lists[key] = list(value)
            if len(set(value)) != len(value):
                errors.append(
                    _error(
                        "caller_object_id_list_duplicate",
                        f"$.input_ownership.{key}",
                        "调用方对象清单不得重复",
                    )
                )

    provider = _require_object(data, "provider", "$", errors)
    for key in ("name", "coordinate_crs", "capture_date"):
        if not _nonempty_string(provider.get(key)):
            errors.append(
                _error(
                    "required_nonempty_string",
                    f"$.provider.{key}",
                    f"后台复算信息 {key} 必须为非空字符串",
                )
            )

    objects = _require_list(data, "objects", "$", errors)
    object_by_id: dict[str, dict[str, Any]] = {}
    unavailable_ids: set[str] = set()
    case_objects: list[dict[str, Any]] = []
    for index, obj in enumerate(objects):
        path = f"$.objects.{index}"
        if not isinstance(obj, dict):
            errors.append(_error("object_not_object", path, "空间对象必须为对象"))
            continue
        object_id = obj.get("object_id")
        role = obj.get("role")
        if not _nonempty_string(object_id) or object_id in object_by_id:
            errors.append(
                _error(
                    "duplicate_or_invalid_object_id",
                    f"{path}.object_id",
                    "object_id 必须为非空且唯一",
                )
            )
            continue
        object_by_id[object_id] = obj
        if not _nonempty_string(obj.get("name")):
            errors.append(_error("required_nonempty_string", f"{path}.name", "对象名称不能为空"))
        if role not in OBJECT_ROLES:
            errors.append(_error("object_role_invalid", f"{path}.role", "对象角色不在允许集合"))
            continue
        if role == "case_project":
            case_objects.append(obj)

        location_status = obj.get("location_status", "verified")
        if location_status not in {"verified", "not_available", "approximate_only"}:
            errors.append(_error("location_status_invalid", path, "位置状态必须明确为可靠、未取得或近似辅助"))
        if location_status in {"not_available", "approximate_only"}:
            unavailable_ids.add(object_id)
            if not _nonempty_string(obj.get("gap_reason")):
                errors.append(_error("location_gap_reason_required", path, "未取得精确位置时须说明缺口"))
            if obj.get("centerpoint") is not None or obj.get("geometry_reference") is not None:
                errors.append(_error("gap_cannot_claim_precise_location", path, "缺口或近似材料不能同时声称已有精确中心点或几何"))
            if location_status == "approximate_only":
                if obj.get("location_model") != "address_or_area_illustration":
                    errors.append(_error("approximate_model_required", path, "近似定位须明确为门牌或区域示意"))
                auxiliary = obj.get("approximate_location", {})
                if not isinstance(auxiliary, dict):
                    auxiliary = {}
                _validate_coordinate(auxiliary.get("coordinate"), f"{path}.approximate_location.coordinate", errors)
                if not _nonempty_string(auxiliary.get("accepted_use_ref")) or not _nonempty_string(auxiliary.get("usage_boundary")):
                    errors.append(_error("approximate_use_required", path, "须引用任务已接受的示意用途并说明精度限制"))
            elif obj.get("approximate_location") is not None:
                errors.append(_error("unavailable_has_approximation", path, "有近似材料时须使用 approximate_only"))
            continue
        if obj.get("approximate_location") is not None:
            errors.append(_error("approximation_cannot_be_verified_center", path, "近似材料不得冒充精确中心点"))
        if role in POINT_ROLES:
            if obj.get("location_model") != PROJECT_LOCATION_MODEL:
                errors.append(
                    _error(
                        "single_centerpoint_required",
                        f"{path}.location_model",
                        "项目、竞品和紧凑对象必须使用单一地图标注中心点",
                    )
                )
            _validate_coordinate(obj.get("centerpoint"), f"{path}.centerpoint", errors)
        elif role == "amenity_large_or_elongated":
            if obj.get("location_model") != LARGE_RESOURCE_LOCATION_MODEL:
                errors.append(
                    _error(
                        "large_resource_geometry_required",
                        f"{path}.location_model",
                        "大型或狭长资源必须提供可计算垂距的几何信息",
                    )
                )
            if not _nonempty_string(obj.get("geometry_reference")):
                errors.append(
                    _error(
                        "large_resource_geometry_required",
                        f"{path}.geometry_reference",
                        "大型或狭长资源必须提供 geometry_reference",
                    )
                )
            if "centerpoint" in obj:
                errors.append(
                    _error(
                        "large_resource_centerpoint_forbidden",
                        f"{path}.centerpoint",
                        "大型或狭长资源不得退化为中心点距离模型",
                    )
                )

    if len(case_objects) != 1 or not case_project_id or case_objects[0].get("object_id") != case_project_id:
        errors.append(
            _error(
                "case_project_count_invalid",
                "$.objects",
                "必须且只能有一个与 case_project_id 一致的本案对象",
            )
        )

    expected_ids = {
        item
        for item in [case_project_id]
        + ownership_lists["competitor_ids"]
        + ownership_lists["resource_ids"]
        + ownership_lists["reference_ids"]
        if item
    }
    if set(object_by_id) != expected_ids:
        errors.append(
            _error(
                "object_set_mismatch",
                "$.objects",
                "objects 必须与调用方提供的对象清单完全一致，空间渠道不得增删竞品或配套",
            )
        )

    expected_roles = {
        case_project_id: {"case_project"},
        **{item: {"competitor"} for item in ownership_lists["competitor_ids"]},
        **{
            item: {"amenity_compact", "amenity_large_or_elongated"}
            for item in ownership_lists["resource_ids"]
        },
        **{item: {"reference_center"} for item in ownership_lists["reference_ids"]},
    }
    for object_id, allowed_roles in expected_roles.items():
        if object_id in object_by_id and object_by_id[object_id].get("role") not in allowed_roles:
            errors.append(
                _error(
                    "caller_role_mismatch",
                    f"$.objects[{object_id}].role",
                    "对象角色与调用方清单不一致",
                )
            )

    four_sides = _require_object(data, "four_side_coordinate_evidence", "$", errors)
    if four_sides.get("case_project_id") != case_project_id:
        errors.append(
            _error(
                "four_side_case_mismatch",
                "$.four_side_coordinate_evidence.case_project_id",
                "四至必须绑定本案对象",
            )
        )
    if four_sides.get("rendering_owner") != FOUR_SIDE_RENDERING_OWNER:
        errors.append(
            _error(
                "four_side_rendering_owner_mismatch",
                "$.four_side_coordinate_evidence.rendering_owner",
                "近似轮廓绘制责任必须属于下游",
            )
        )
    if four_sides.get("outline_use") != FOUR_SIDE_OUTLINE_USE:
        errors.append(
            _error(
                "four_side_outline_use_mismatch",
                "$.four_side_coordinate_evidence.outline_use",
                "四至只能供下游绘制近似轮廓",
            )
        )
    status = four_sides.get("status")
    corners = four_sides.get("corners")
    if not isinstance(corners, list):
        errors.append(_error("required_list", "$.four_side_coordinate_evidence.corners", "corners 必须为数组"))
        corners = []
    if status == "ready":
        if four_sides.get("order_direction") != "clockwise":
            errors.append(
                _error(
                    "four_side_clockwise_order_invalid",
                    "$.four_side_coordinate_evidence.order_direction",
                    "四个角点必须按顺时针排列",
                )
            )
        if len(corners) != 4:
            errors.append(
                _error(
                    "four_side_corner_count_invalid",
                    "$.four_side_coordinate_evidence.corners",
                    "ready 状态必须恰好提供四个角点",
                )
            )
        orders: list[Any] = []
        corner_coordinates: list[dict[str, Any]] = []
        for index, corner in enumerate(corners):
            path = f"$.four_side_coordinate_evidence.corners.{index}"
            if not isinstance(corner, dict):
                errors.append(_error("four_side_corner_invalid", path, "角点必须为对象"))
                continue
            orders.append(corner.get("order"))
            coordinate = corner.get("coordinate")
            if _validate_coordinate(coordinate, f"{path}.coordinate", errors):
                corner_coordinates.append(coordinate)
            nearby = corner.get("nearby_reference")
            if not isinstance(nearby, dict):
                errors.append(
                    _error(
                        "four_side_nearby_reference_required",
                        f"{path}.nearby_reference",
                        "每个角点必须配一条相邻道路或路口坐标",
                    )
                )
                continue
            if not _nonempty_string(nearby.get("name")) or nearby.get("kind") not in {"road", "intersection"}:
                errors.append(
                    _error(
                        "four_side_nearby_reference_required",
                        f"{path}.nearby_reference",
                        "相邻参照必须包含道路／路口名称和类型",
                    )
                )
            _validate_coordinate(nearby.get("coordinate"), f"{path}.nearby_reference.coordinate", errors)
        if orders != [1, 2, 3, 4]:
            errors.append(
                _error(
                    "four_side_clockwise_order_invalid",
                    "$.four_side_coordinate_evidence.corners",
                    "角点 order 必须依次为 1、2、3、4",
                )
            )
        if len(corner_coordinates) == 4 and not _clockwise_coordinate_order(corner_coordinates):
            errors.append(
                _error(
                    "four_side_clockwise_geometry_invalid",
                    "$.four_side_coordinate_evidence.corners",
                    "角点坐标本身必须按顺时针排列且不得重合",
                )
            )
    elif status == "not_available":
        if corners:
            errors.append(
                _error(
                    "four_side_unavailable_corners_forbidden",
                    "$.four_side_coordinate_evidence.corners",
                    "not_available 状态的 corners 必须为空",
                )
            )
        if not _nonempty_string(four_sides.get("note")):
            errors.append(
                _error(
                    "four_side_unavailable_note_required",
                    "$.four_side_coordinate_evidence.note",
                    "四至不可用时需给出简短原因",
                )
            )
        if four_sides.get("order_direction") != "not_applicable":
            errors.append(
                _error(
                    "four_side_unavailable_order_invalid",
                    "$.four_side_coordinate_evidence.order_direction",
                    "四至不可用时 order_direction 必须为 not_applicable",
                )
            )
    else:
        errors.append(
            _error(
                "four_side_status_invalid",
                "$.four_side_coordinate_evidence.status",
                "四至状态只能是 ready 或 not_available",
            )
        )

    distances = _require_list(data, "distances", "$", errors)
    distance_ids: set[str] = set()
    distance_by_id: dict[str, dict[str, Any]] = {}
    for index, distance in enumerate(distances):
        path = f"$.distances.{index}"
        if not isinstance(distance, dict):
            errors.append(_error("distance_not_object", path, "距离记录必须为对象"))
            continue
        distance_id = distance.get("distance_id")
        if not _nonempty_string(distance_id) or distance_id in distance_ids:
            errors.append(_error("distance_id_invalid", f"{path}.distance_id", "distance_id 必须非空且唯一"))
        else:
            distance_ids.add(distance_id)
            distance_by_id[distance_id] = distance
        from_id = distance.get("from_id")
        to_id = distance.get("to_id")
        if from_id not in object_by_id or to_id not in object_by_id:
            errors.append(_error("distance_object_unknown", path, "距离两端必须来自调用方对象清单"))
            continue
        if from_id in unavailable_ids or to_id in unavailable_ids:
            errors.append(_error("distance_requires_verified_location", path, "未取得或近似位置不得参与正式距离或路线计算"))
            continue
        if object_by_id[from_id].get("role") not in {"case_project", "competitor"}:
            errors.append(
                _error(
                    "distance_origin_must_be_project_centerpoint",
                    f"{path}.from_id",
                    "距离起点必须是本案或竞品中心点",
                )
            )
        distance_type = distance.get("distance_type")
        if distance_type not in DISTANCE_TYPES:
            errors.append(_error("distance_type_invalid", f"{path}.distance_type", "距离类型不在 v2 允许集合"))
            continue
        if not _nonnegative_number(distance.get("distance_m")):
            errors.append(_error("nonnegative_distance_required", f"{path}.distance_m", "距离必须为非负数"))
        target_role = object_by_id[to_id].get("role")
        if target_role == "amenity_large_or_elongated" and distance_type != "perpendicular_shortest_straight":
            errors.append(
                _error(
                    "large_resource_requires_perpendicular_distance",
                    f"{path}.distance_type",
                    "大型或狭长资源必须使用垂距",
                )
            )
        if distance_type == "perpendicular_shortest_straight" and target_role != "amenity_large_or_elongated":
            errors.append(
                _error(
                    "perpendicular_target_mismatch",
                    f"{path}.to_id",
                    "垂距只能用于大型或狭长资源",
                )
            )
        if distance_type in ROUTE_DISTANCE_TYPES:
            if distance.get("route_snap") != ROUTE_SNAP:
                errors.append(
                    _error(
                        "route_snap_mismatch",
                        f"{path}.route_snap",
                        "步行／驾车必须接受地图平台从项目中心点自动吸附道路",
                    )
                )
            if not _nonnegative_number(distance.get("duration_min")):
                errors.append(
                    _error(
                        "route_duration_required",
                        f"{path}.duration_min",
                        "路线距离必须提供非负数时长",
                    )
                )

    barrier_observations = _require_list(data, "barrier_observations", "$", errors)
    for index, observation in enumerate(barrier_observations):
        path = f"$.barrier_observations.{index}"
        if not isinstance(observation, dict):
            errors.append(_error("barrier_observation_invalid", path, "阻隔记录必须为对象"))
            continue
        if observation.get("from_id") not in object_by_id or observation.get("to_id") not in object_by_id:
            errors.append(_error("barrier_object_unknown", path, "阻隔两端必须来自调用方对象清单"))
        barriers = observation.get("barriers")
        if not isinstance(barriers, list) or not barriers or any(item not in BARRIER_TYPES for item in barriers):
            errors.append(_error("barrier_invalid", f"{path}.barriers", "阻隔类型不在允许集合"))
        elif "none" in barriers and len(barriers) != 1:
            errors.append(_error("barrier_invalid", f"{path}.barriers", "none 不能与其他阻隔并列"))
        if observation.get("walking_effect") not in WALKING_EFFECTS:
            errors.append(_error("walking_effect_invalid", f"{path}.walking_effect", "步行影响不在允许集合"))

    relative_findings = _require_list(data, "relative_access_findings", "$", errors)
    caller_project_ids = {case_project_id, *ownership_lists["competitor_ids"]}
    relative_finding_ids: set[str] = set()
    for index, finding in enumerate(relative_findings):
        path = f"$.relative_access_findings.{index}"
        if not isinstance(finding, dict):
            errors.append(_error("relative_finding_invalid", path, "相对便利性记录必须为对象"))
            continue
        finding_id = finding.get("finding_id")
        if not _nonempty_string(finding_id) or finding_id in relative_finding_ids:
            errors.append(
                _error(
                    "relative_finding_id_invalid",
                    f"{path}.finding_id",
                    "finding_id 必须非空且唯一",
                )
            )
        else:
            relative_finding_ids.add(finding_id)
        finding_value = finding.get("finding")
        if finding_value not in RELATIVE_FINDINGS:
            errors.append(
                _error(
                    "relative_finding_invalid",
                    f"{path}.finding",
                    "只能输出给定集合内的相对距离／步行便利性",
                )
            )
        if _contains_absolute_exclusivity(finding):
            errors.append(
                _error(
                    "absolute_exclusivity_forbidden",
                    path,
                    "相对结论及其说明不得宣称全城市绝对独占",
                )
            )
        if finding.get("comparison_scope") != "caller_supplied_set_only":
            errors.append(
                _error(
                    "relative_scope_mismatch",
                    f"{path}.comparison_scope",
                    "相对结论必须限定在调用方给定集合内",
                )
            )
        comparison_ids = finding.get("comparison_project_ids")
        comparison_id_set = set(comparison_ids) if _string_list(comparison_ids) else set()
        if (
            not _string_list(comparison_ids)
            or len(set(comparison_ids)) != len(comparison_ids)
            or case_project_id not in comparison_ids
            or not set(comparison_ids).issubset(caller_project_ids)
        ):
            errors.append(
                _error(
                    "relative_comparison_outside_caller_set",
                    f"{path}.comparison_project_ids",
                    "比较项目必须包含本案且全部来自调用方竞品集合",
                )
            )
        if finding.get("subject_id") != case_project_id:
            errors.append(_error("relative_subject_mismatch", f"{path}.subject_id", "相对优势判断主体必须为本案"))
        reference_object_id = finding.get("reference_object_id")
        if finding_value != "not_assessed" and unavailable_ids.intersection(comparison_id_set | {reference_object_id}):
            errors.append(_error("relative_finding_requires_verified_locations", path, "相关位置缺口未闭合时不得作该组比较结论"))
        if (
            reference_object_id not in object_by_id
            or object_by_id[reference_object_id].get("role")
            not in {"amenity_compact", "amenity_large_or_elongated", "reference_center"}
        ):
            errors.append(
                _error(
                    "relative_reference_unknown",
                    f"{path}.reference_object_id",
                    "相对结论的参照对象必须来自调用方的配套或参照对象清单",
                )
            )
        basis_ids = finding.get("basis_distance_ids")
        basis_valid = _string_list(basis_ids) and all(item in distance_ids for item in basis_ids)
        if finding_value != "not_assessed" and (not basis_ids or not basis_valid):
            errors.append(
                _error(
                    "relative_basis_invalid",
                    f"{path}.basis_distance_ids",
                    "已形成的相对结论必须引用本包已有距离记录",
                )
            )
        elif finding_value == "not_assessed" and not _string_list(basis_ids):
            errors.append(
                _error(
                    "relative_basis_invalid",
                    f"{path}.basis_distance_ids",
                    "暂不判断时 basis_distance_ids 可以为空，但必须仍是数组",
                )
            )
        if basis_valid:
            mismatched_basis = [
                item
                for item in basis_ids
                if distance_by_id[item].get("to_id") != reference_object_id
                or distance_by_id[item].get("from_id") not in comparison_id_set
            ]
            if mismatched_basis:
                errors.append(
                    _error(
                        "relative_basis_mismatch",
                        f"{path}.basis_distance_ids",
                        "相对结论引用的距离必须连接本比较集合中的项目与同一参照对象",
                    )
                )

    osm = _require_object(data, "osm_use", "$", errors)
    asset_included = osm.get("asset_included")
    if not isinstance(asset_included, bool):
        errors.append(_error("osm_asset_flag_invalid", "$.osm_use.asset_included", "asset_included 必须为布尔值"))
    if any(osm.get(key) is not False for key in ("bulk_tile_downloaded", "prefetch_executed", "offline_tile_package_created")):
        errors.append(
            _error(
                "osm_bulk_or_offline_forbidden",
                "$.osm_use",
                "禁止批量抓取、预取公共瓦片或制作离线瓦片包",
            )
        )
    if asset_included is True:
        if osm.get("provider") != "OpenStreetMap Standard":
            errors.append(_error("osm_provider_invalid", "$.osm_use.provider", "OSM 资产必须标为 OpenStreetMap Standard"))
        attribution = osm.get("attribution_text")
        if osm.get("attribution_visible") is not True or not isinstance(attribution, str) or "OpenStreetMap contributors" not in attribution:
            errors.append(
                _error(
                    "osm_attribution_required",
                    "$.osm_use.attribution_text",
                    "实际使用 OSM 资产时必须保留可见署名",
                )
            )
        if not _nonempty_string(osm.get("asset_pointer")):
            errors.append(_error("osm_asset_pointer_required", "$.osm_use.asset_pointer", "实际使用 OSM 资产时需给出资产指针"))

    return errors


def delivery_summary(data: Any, errors: list[dict[str, str]]) -> dict[str, Any]:
    """Report material availability without claiming the business task is done."""
    groups = {"verified": [], "not_available": [], "approximate_only": []}
    objects = data.get("objects", []) if isinstance(data, dict) else []
    for obj in objects if isinstance(objects, list) else []:
        if isinstance(obj, dict) and obj.get("location_status", "verified") in groups:
            groups[obj.get("location_status", "verified")].append(obj.get("object_id"))
    has_gaps = bool(groups["not_available"] or groups["approximate_only"])
    return {
        "delivery_status": "invalid" if errors else ("partial" if has_gaps else "complete_coordinate_set"),
        "usable_object_ids": [] if errors else groups["verified"],
        "unavailable_object_ids": groups["not_available"],
        "auxiliary_object_ids": [] if errors else groups["approximate_only"],
        "task_completion": "not_assessed_against_business_goal",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate spatial_coordinate_evidence.v2 locally.")
    parser.add_argument("--input", required=True, type=Path, help="Path to a spatial evidence JSON package.")
    args = parser.parse_args()

    data = json.loads(args.input.read_text(encoding="utf-8"))
    errors = validate_contract(data)
    result = {
        "status": "pass" if not errors else "fail",
        "schema_version": SCHEMA_VERSION,
        "error_count": len(errors),
        "errors": errors,
        **delivery_summary(data, errors),
        "boundary": "local contract validation only; no map service, API, rendering, competitor decision or downstream write",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
