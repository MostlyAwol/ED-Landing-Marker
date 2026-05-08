from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Optional


@dataclass
class MarkerResult:
    x: float
    y: float
    visible_side: bool
    in_front: bool
    clamped: bool
    distance_m: float
    bearing_deg: float
    delta_heading_deg: float


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def norm(v: tuple[float, float, float]) -> float:
    return math.sqrt(dot(v, v))


def normalize(v: tuple[float, float, float]) -> tuple[float, float, float]:
    n = norm(v)
    if n <= 1e-9:
        return (0.0, 0.0, 0.0)
    return (v[0] / n, v[1] / n, v[2] / n)


def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def scale(v, s: float):
    return (v[0] * s, v[1] * s, v[2] * s)


def latlon_to_vector(lat_deg: float, lon_deg: float, radius_m: float) -> tuple[float, float, float]:
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    return (
        radius_m * math.cos(lat) * math.cos(lon),
        radius_m * math.cos(lat) * math.sin(lon),
        radius_m * math.sin(lat),
    )


def local_basis(lat_deg: float, lon_deg: float):
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)

    up = normalize((
        math.cos(lat) * math.cos(lon),
        math.cos(lat) * math.sin(lon),
        math.sin(lat),
    ))

    east = normalize((-math.sin(lon), math.cos(lon), 0.0))
    north = normalize(cross(up, east))
    return east, north, up


def rotate_about_axis(v, axis, angle_deg: float):
    # Rodrigues rotation formula.
    a = normalize(axis)
    theta = math.radians(angle_deg)
    c = math.cos(theta)
    s = math.sin(theta)
    return add(add(scale(v, c), scale(cross(a, v), s)), scale(a, dot(a, v) * (1 - c)))


def bearing_to_target(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    x = math.sin(dlon) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0


def heading_delta(current_heading: float, target_bearing: float) -> float:
    return (target_bearing - current_heading + 540.0) % 360.0 - 180.0


def angular_distance_rad(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    c = math.sin(p1) * math.sin(p2) + math.cos(p1) * math.cos(p2) * math.cos(dlon)
    return math.acos(clamp(c, -1.0, 1.0))


def surface_distance_m(lat1: float, lon1: float, lat2: float, lon2: float, radius_m: float) -> float:
    return radius_m * angular_distance_rad(lat1, lon1, lat2, lon2)


def is_visible_side(lat1: float, lon1: float, lat2: float, lon2: float, radius_m: float, altitude_m: float) -> bool:
    # From altitude h, angle to horizon around the sphere is acos(R/(R+h)).
    h = max(0.0, altitude_m)
    if radius_m <= 0:
        return False
    horizon = math.acos(clamp(radius_m / (radius_m + h), -1.0, 1.0))
    return angular_distance_rad(lat1, lon1, lat2, lon2) <= horizon


def calculate_marker(
    current_lat: float,
    current_lon: float,
    heading_deg: float,
    altitude_m: float,
    target_lat: float,
    target_lon: float,
    planet_radius_m: float,
    screen_w: int,
    screen_h: int,
    horizontal_fov_deg: float = 70.0,
    vertical_fov_deg: float = 43.0,
    pitch_offset_deg: float = 0.0,
) -> Optional[MarkerResult]:
    if planet_radius_m <= 0 or screen_w <= 0 or screen_h <= 0:
        return None

    ship_pos = latlon_to_vector(current_lat, current_lon, planet_radius_m + max(0.0, altitude_m))
    target_pos = latlon_to_vector(target_lat, target_lon, planet_radius_m)
    to_target = sub(target_pos, ship_pos)

    east, north, local_up = local_basis(current_lat, current_lon)
    h = math.radians(heading_deg)

    # ED heading: 0 north, 90 east.
    forward = normalize(add(scale(north, math.cos(h)), scale(east, math.sin(h))))
    right = normalize(cross(forward, local_up))

    # Optional pitch calibration. Positive values lift the reticle upward.
    if abs(pitch_offset_deg) > 0.0001:
        forward = normalize(rotate_about_axis(forward, right, pitch_offset_deg))

    camera_up = normalize(cross(right, forward))

    x_cam = dot(to_target, right)
    y_cam = dot(to_target, camera_up)
    z_cam = dot(to_target, forward)

    in_front = z_cam > 0.01

    # If behind camera, still give an edge indication rather than disappearing.
    if not in_front:
        z_for_projection = 0.01
    else:
        z_for_projection = z_cam

    fx = (screen_w / 2.0) / math.tan(math.radians(horizontal_fov_deg) / 2.0)
    fy = (screen_h / 2.0) / math.tan(math.radians(vertical_fov_deg) / 2.0)

    raw_x = screen_w / 2.0 + fx * (x_cam / z_for_projection)
    raw_y = screen_h / 2.0 - fy * (y_cam / z_for_projection)

    margin = 24
    x = clamp(raw_x, margin, screen_w - margin)
    y = clamp(raw_y, margin, screen_h - margin)
    clamped = abs(x - raw_x) > 0.1 or abs(y - raw_y) > 0.1

    bearing = bearing_to_target(current_lat, current_lon, target_lat, target_lon)
    distance = surface_distance_m(current_lat, current_lon, target_lat, target_lon, planet_radius_m)
    visible = is_visible_side(current_lat, current_lon, target_lat, target_lon, planet_radius_m, altitude_m)

    return MarkerResult(
        x=x,
        y=y,
        visible_side=visible,
        in_front=in_front,
        clamped=clamped,
        distance_m=distance,
        bearing_deg=bearing,
        delta_heading_deg=heading_delta(heading_deg, bearing),
    )
