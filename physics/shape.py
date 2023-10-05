from PySide6.QtGui import QVector2D as Vec2
from abc import ABC, abstractmethod
from enum import Enum

class Shape(ABC):
    _center_mass: Vec2
    _inerita_tenser: float
    class Type(Enum):
        Circle = 0
        Edge = 1
    
    def __init__(self):
        pass
    
    @abstractmethod
    def type(self):
        pass

    @abstractmethod
    def inerita_tenser(self) -> float:
        pass

    # center mass is local space
    def center_mass(self) -> Vec2:
        return self._center_mass


    
class Circle(Shape):
    radius: float
    
    def __init__(self, radii):
        super().__init__()
        self.radius = float(radii)
        self._center_mass = Vec2(0,0)

    def type(self):
        return Shape.Type.Circle

    def inerita_tenser(self):
        return 0.5 * self.radius * self.radius

class Edge(Shape):
    vec: Vec2
    def __init__(self, vec):
        super().__init__()
        self._type = Shape.Type.Edge
        self.vec = vec
        self._center_mass = vec / 2
    
    def type(self):
        return Shape.Type.Edge
    
    def inerita_tenser(self):
        return 0
        