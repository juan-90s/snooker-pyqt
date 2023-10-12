from PySide6.QtGui import QVector2D as Vec2
from PySide6.QtCore import QThreadPool as ThreadPool, QRunnable as Worker, QTimer as Timer, Signal, Slot, QMutex as Mutex


from physics.shape import Shape, Edge, Circle
from physics.common import *
from physics.body import Body
from physics.collision_grid import *
from physics.contact import Contact

import timeit

class PhysicsManager():
    tps = 60

    def __init__(self, timer:Timer=None):
        if timer:
            self._timer = timer
        else:
            self._timer = Timer()
            self._timer.start(1000 // self.tps)
        self._timer.timeout.connect(self.update)
        self.dt = self._timer.interval() / 1000
        
        self._bodies = []
        self._statics = []
        self._mutex = Mutex()

        self.frametime = 0
        self.global_friction = 0
        self.gravity = 0
        self.gravity_center = None
    
    def add_body(self, body: Body):
        if body.type == Body.Type.Static:
            self._statics.append(body)
        else:
            self._bodies.append(body)

    def add_bodies(self, bodies: list[Body]):
        self._bodies = self._bodies + bodies
    
    def remove_body(self, body: Body):
        self._mutex.lock()
        self._bodies.remove(body)
        self._mutex.unlock()
    
    def solve_movement(self, dt):
        # movement
        for body in self._bodies:
            body.update(dt)
            if body.type is not Body.Type.Dynamic:
                continue
            if self.global_friction > 0 and body.linear_velocity.lengthSquared() > 0:
                # apply slow donw effect
                linear_velocity_after = body.linear_velocity - (1 - self.global_friction * body.friction) * dt * body.linear_velocity - self.global_friction * dt * body.linear_velocity.normalized()
                if Vec2.dotProduct(linear_velocity_after, body.linear_velocity) > 0:
                    body.linear_velocity = linear_velocity_after
                else:
                    body.linear_velocity *= 0
        

    def solve_contact(self):
        # contact
        for bodyA in self._bodies:

            if bodyA.linear_velocity.lengthSquared() <= 0.001:
                continue
            for bodyB in self._bodies:
                if (bodyA.position - bodyB.position).lengthSquared() > (bodyA.shape.radius+bodyB.shape.radius)**2:
                    continue
                contact = Contact(bodyA, bodyB)
                if(contact.intersect):
                    contact.resolve()  

            for bodyS in self._statics:

                contact = Contact(bodyA, bodyS)
                if(contact.intersect):
                    vel_normal = Vec2.dotProduct(bodyA.linear_velocity, contact.normal)
                    contact.resolve()
                    if vel_normal < 0.01:
                        bodyA.linear_velocity -= vel_normal * contact.normal

 

    @Slot()
    def update(self):
        self._mutex.lock()
        t = timeit.default_timer()
        self.solve_contact()
        self.solve_movement(self.dt)
        self.frametime = 1000 * (timeit.default_timer() - t)
        self._mutex.unlock()


# Do not use
class PhysicsManager_Grid(PhysicsManager):
    def __init__(self, timer:Timer, world_width, world_height, grid_width, grid_height):
        super().__init__(timer)
        self.grid = CollisionGrid(grid_width, grid_height, world_width // grid_width, world_height // grid_height)
        self._threadpool = ThreadPool()
        self._sub_steps = 2
        self.num_body = 0
    
    def add_static_body(self, body:Body):
        body.type = Body.Type.Static
        self.grid.load_body(body)
    
    def add_static_body_cell(self, body:Body, coordinate: (int,int)):
        body.type = Body.Type.Static
        x,y = coordinate
        self.grid.cell(x,y).add_body(body)

    def add_static_body_multicell(self, body:Body, coordinates: [(int,int)]):
        body.type = Body.Type.Static
        for x,y in coordinates:
            self.grid.cell(x,y).add_body(body)

    def reload_grid(self):
        self.grid.unload_body()
        for body in self._bodies:
            self.grid.load_body(body)
    
    class ContactSolver(Worker):
        def __init__(self, manager, i, slice_size):
            super().__init__()
            self.manager = manager
            self.i = i
            self.slice_size = slice_size

        def run(self):
            start = self.i * self.slice_size
            end = start + self.slice_size
            for index in range(start, end):
                self.manager.grid.check_collision(index)
        
    
    def solve_contact(self):
        thread_count = self._threadpool.maxThreadCount()
        slice_count = thread_count * 2
        slice_size = int(self.grid.width / slice_count) * self.grid.height
        if slice_size < self.grid.height:
            slice_size = 1
        for i in range(0, thread_count):
            worker = self.ContactSolver(self, 2 * i, slice_size) 
            worker.setAutoDelete(True)
            self._threadpool.start(worker)
        self._threadpool.waitForDone()

        for i in range(0, thread_count):
            worker = self.ContactSolver(self, 2 * i + 1, slice_size) 
            worker.setAutoDelete(True)
            self._threadpool.start(worker)
        self._threadpool.waitForDone()
    
    @Slot()
    def update(self):
        self.num_body = 0
        t = timeit.default_timer()
        sub_dt = self.dt / self._sub_steps
        for i in range(0, self._sub_steps):
            self.reload_grid()
            self.solve_contact()
            self.solve_movement(sub_dt)
        self.frametime = 1000 * (timeit.default_timer() - t)

