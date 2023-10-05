from PySide6.QtGui import QVector2D as Vec2
from math import sin, cos, pi as Pi

eps = 0.000000001

def cross(a, b):
    if isinstance(a, Vec2) and isinstance(b, Vec2):
        return a.x() * b.y() - a.y() * b.x()
    elif isinstance(a, Vec2) and isinstance(b, float):
        return Vec2(a * b.y(), -a * b.x())
    elif isinstance(a, float) and isinstance(b, Vec2):
        return Vec2(-a * b.y(), a * b.x())
    else:
        raise Exception("Unknown type for cross product")

def rotate_vec(vec: Vec2, angle: float) -> Vec2:
    s = sin(angle)
    c = cos(angle)
    x = vec.x()
    y = vec.y()
    return Vec2(c * x - s * y, s * x + c * y)