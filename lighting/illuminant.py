from enum import Enum
from PySide6.QtGui import QVector3D, QColor
from lighting.common import Array_from_QVector3D
import numpy as np

class LightSource():
    class Type(Enum):
        Parallel = 0
        Spot = 1
    type: Type
    position: np.ndarray
    direction: np.ndarray
    color: np.ndarray
    intensity: float
    spread: float
    def __init__(self, type):
        self.type = type
        self.position = np.array([0,0,0])
        self.direction = np.array([0,0,0])
        self.color = np.array([1,1,1])
        self.intensity = 1
        self.spread = 1
    
    def set_position(self, position):
        if isinstance(position, QVector3D):
            self.position = Array_from_QVector3D(position)
        elif isinstance(position, tuple) or isinstance(position, list):
            self.position = np.array(position, dtype=float)
    
    def set_direction(self, vector):
        if isinstance(vector, QVector3D):
            vector.normalize()
            self.direction = Array_from_QVector3D(vector)
        elif isinstance(vector, tuple) or isinstance(vector, list):
            if len(vector) != 3:
                raise Exception('parameter direction should be 3D vector')
            self.direction = np.array(vector, dtype=float)
            lengthSquare = np.sum(self.direction * self.direction)
            if lengthSquare != 1:
                self.direction /= lengthSquare
    
    def set_color(self, color):
        if isinstance(color, QColor):
            # The default Qt image format is in ARGB32, which store like 0xBBGGRRAA
            self.color = np.array((color.blueF(), color.greenF(), color.redF()))
