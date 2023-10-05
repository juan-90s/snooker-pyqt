from physics.common import *
from physics.shape import Shape, Edge, Circle
from enum import Enum
class Body(object):

    class Type(Enum):
        Static = 0
        Dynamic = 1
    
    _shape: Shape
    _invMass: float
    _invI: float
    type: Type
    position: Vec2
    linear_velocity: Vec2
    angle: float
    angle_velocity: float
    elasticity: float
    friction: float

    def __init__(self, shape, type):

        if not isinstance(shape, Shape):
            raise Exception('parameter shape is not shape')

        self._shape = shape
        self.type = type
        
        self.position = Vec2(0,0)
        self.linear_velocity = Vec2(0,0)
        self.angle = 0.0
        self.angle_velocity = 0.0
        self.elasticity = 0.9
        self.friction = 0.5

        if self.type == Body.Type.Static:
            self._invMass = 0
            self._invI = 0
        else:
            self.set_mass(1.0)
    
    @property
    def shape(self) ->Shape:
        return self._shape
    
    @property
    def shapeType(self) -> Shape.Type:
        return self._shape.type()

    def center(self) -> Vec2:
        # local to world
        return self.position + rotate_vec(self.shape.center_mass(), self.angle)

    def point_local_to_world(self, local_point: Vec2) -> Vec2:
        return self.position + rotate_vec(local_point, self.angle)
    
    @property
    def mass(self) -> float:
        return 1.0 / self._invMass
    

    def set_mass(self, mass: float):
        if self.type == Body.Type.Static:
            raise Exception("mass is unavailable on a static body ")
        self._invMass = 1.0 / (mass + eps)
        I = mass * self.shape.inerita_tenser() - mass * self.shape.center_mass().lengthSquared()
        self._invI = 1.0 / (I + eps)
        
    
    @property
    def invMass(self) ->float:
        return self._invMass
    
    @property
    def invI(self) -> float:
        return self._invI

    def applyImpulseLinear(self, impulse: Vec2):
        if self.type != Body.Type.Dynamic:
            return
        
        if 0 == self._invMass:
            return
        self.linear_velocity += impulse * self._invMass
    
    def applyImpulseAngular(self, impulse: float):
        if self.type != Body.Type.Dynamic:
            return
        
        if 0 == self._invMass:
            return
        
        self.angle_velocity += self._invI * impulse

    def applyImpulse(self, impulse_point:Vec2, impulse: Vec2):
        if self.type != Body.Type.Dynamic:
            return
        
        if 0 == self._invMass:
            return
        self.linear_velocity += impulse * self._invMass
        vec_ = impulse_point - self.center()
        self.angle_velocity += self._invI * cross(vec_, impulse)
    
    def update(self, dt: float):
        self.position += self.linear_velocity * dt 
        new_angle = self.angle + self.angle_velocity * dt
        if new_angle > 2 * Pi:
            self.angle = new_angle - 2 * Pi
        else:
            self.angle = new_angle