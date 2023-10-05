from physics.common import *
from physics.body import Body
from physics.shape import Shape, Circle, Edge

class Contact(object):
    pt_A_worldspace: Vec2
    pt_B_worldspace: Vec2
    pt_A_localspace: Vec2
    pt_B_localspace: Vec2

    normal: Vec2
    distance: float
    time_impact: float

    bodyA: Body
    bodyB: Body

    intersect:bool

    def __init__(self, bodyA: Body, bodyB: Body):
        self.bodyA = bodyA
        self.bodyB = bodyB
        self.intersect = False
        if bodyA == bodyB:
            return
        if bodyA.shapeType == Shape.Type.Circle and bodyB.shapeType == Shape.Type.Circle:
            a_b = bodyB.position - bodyA.position
            
            self.normal = a_b.normalized()
            self.pt_A_worldspace = bodyA.position + self.normal * bodyA.shape.radius
            self.pt_B_worldspace = bodyB.position - self.normal * bodyB.shape.radius
            
            radii_ab = bodyA.shape.radius + bodyB.shape.radius
            lengthSquare = a_b.lengthSquared()
            self.intersect = lengthSquare <= radii_ab ** 2 and lengthSquare > eps
        
        elif bodyA.shapeType == Shape.Type.Circle and bodyB.shapeType == Shape.Type.Edge:
            radius = bodyA.shape.radius
            # b1, b2 are two vertex of edge B
            b1 = bodyB.position
            b2 = bodyB.point_local_to_world(bodyB.shape.vec)
            vec_edge = rotate_vec(bodyB.shape.vec, bodyB.angle)
            vec_edge_unit = vec_edge.normalized()
            a_b1 = bodyA.position - b1
            a_b2 = - vec_edge + a_b1

            perpendicular_point = b1 + vec_edge_unit * Vec2.dotProduct(a_b1, vec_edge_unit)
            if Vec2.dotProduct(a_b1, vec_edge) < 0:
                # perpendicular_point not on edge, out of b1
                if (perpendicular_point - b1).lengthSquared() >= radius ** 2:
                    self.intersect = False
                else:
                    self.normal = - a_b1.normalized()
                    self.pt_A_worldspace = bodyA.position + self.normal * radius
                    self.pt_B_worldspace = b1
                    lengthSquare = (bodyA.position - b1).lengthSquared()
                    self.intersect = lengthSquare <= radius ** 2 and lengthSquare > eps
            elif Vec2.dotProduct(a_b2, -vec_edge) < 0:
                # perpendicular_point not on edge, out of b2
                if (perpendicular_point - b2).lengthSquared() >= radius ** 2:
                    self.intersect = False
                else:
                    self.normal = - a_b2.normalized()
                    self.pt_A_worldspace = bodyA.position + self.normal * radius
                    self.pt_B_worldspace = b2
                    lengthSquare = (bodyA.position - b2).lengthSquared()
                    self.intersect = lengthSquare <= radius ** 2 and lengthSquare > eps
            else:
                # perpendicular_point on edge
                vec_edge_norm = Vec2(vec_edge.y(),-1.0 * vec_edge.x())
                if Vec2.dotProduct(vec_edge_norm, a_b1) < 0:
                    self.normal = vec_edge_norm.normalized()
                else:
                    self.normal =  -1.0 * vec_edge_norm.normalized()

                self.pt_A_worldspace = bodyA.position + self.normal * radius
                self.pt_B_worldspace = bodyB.position + vec_edge_unit * Vec2.dotProduct(a_b1, vec_edge_unit)
                lengthSquare = (bodyA.position - perpendicular_point).lengthSquared()
                self.intersect = lengthSquare <= radius ** 2 and lengthSquare > eps
        else:
            self.intersect = False
        #     raise Exception("unknown intersect")
    
    def resolve(self):
        if not self.intersect:
            return
        bodyA = self.bodyA
        bodyB = self.bodyB
        sum_invMass = bodyA.invMass + bodyB.invMass
        elasticity_AB = bodyA.elasticity * bodyB.elasticity

        ra = self.pt_A_worldspace - bodyA.center()
        rb = self.pt_B_worldspace - bodyB.center()

        n = self.normal
        angularJA = cross(bodyA.invI * cross(ra, n), ra)
        angularJB = cross(bodyB.invI * cross(rb, n), rb)
        angularFactor = Vec2.dotProduct((angularJA + angularJB), n)

        # get the world space velocity of the motion and rotation
        velA = bodyA.linear_velocity + cross(bodyA.angle_velocity, ra)
        velB = bodyB.linear_velocity + cross(bodyB.angle_velocity, rb)
        vel_a_b = velA - velB

        # calculate the collision impulse
        impulse = (1.0 + elasticity_AB) * Vec2.dotProduct(vel_a_b, n) / (sum_invMass + angularFactor)
        vec_impulse = n * impulse

        self.bodyA.applyImpulse(self.pt_A_worldspace, vec_impulse * -1.0)
        self.bodyB.applyImpulse(self.pt_B_worldspace, vec_impulse)

        #
        # calculate the impulse caused by friction
        #

        friction = bodyA.friction * bodyB.friction

        vel_norm = n * Vec2.dotProduct(n, vel_a_b)
        vel_tang = vel_a_b - vel_norm
        tang = vel_tang.normalized()

        inertiaA = cross(bodyA.invI * cross(ra, tang), ra)
        inertiaB = cross(bodyB.invI * cross(rb, tang), rb)
        inv_inertia = Vec2.dotProduct((inertiaA + inertiaB), tang)

        impulse_friction = vel_tang * friction / (sum_invMass + inv_inertia)

        # Apply kinetic friction
        self.bodyA.applyImpulse(self.pt_A_worldspace, impulse_friction * -1.0)
        self.bodyB.applyImpulse(self.pt_B_worldspace, impulse_friction)

        # move collider out of both
        tA = self.bodyA.invMass / sum_invMass
        tB = self.bodyB.invMass / sum_invMass

        ds = self.pt_B_worldspace - self.pt_A_worldspace
        if self.bodyA.type != Body.Type.Static:
            self.bodyA.position += ds * tA
        if self.bodyB.type != Body.Type.Static:
            self.bodyB.position -= ds * tB