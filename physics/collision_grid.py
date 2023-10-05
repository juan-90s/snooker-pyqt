from physics.body import Body
from physics.contact import Contact
class CollisionCell():
    bodies: [Body]
    def __init__(self):
        self.bodies = []
    def add_body(self, body: Body):
        self.bodies.append(body)
    def unload_body(self):
        for body in self.bodies:
            if body.type != Body.Type.Static:
                self.bodies.remove(body)


class CollisionGrid():
    width: int
    height: int
    cell_width: float
    cell_height: float
    cells: [CollisionCell]
    def __init__(self, width = 0, height = 0, cell_width = 1, cell_height = 1):
        self.width = width
        self.height = height
        self.cell_width = cell_width
        self.cell_height = cell_height
        self.cells = []
        for i in range(0, width * height):
            self.cells.append(CollisionCell())
    
    def cell(self, x:int, y:int) -> CollisionCell:
        if not self._check_coordinate(x, y):
            print(x, y)
            return None
        return self.cells[x * self.height + y]

    def _cell(self, index: int) -> CollisionCell:
        if index >= self.width * self.height or index < 0:
            # invalid idx
            return None
        return self.cells[index]
    
    def setCell(self, x:int, y:int, obj:object):
        if not self._check_coordinate(x, y):
            return
        self.cells[x  * self.height + y] = obj
    
    def _check_coordinate(self, x, y):
        if x >= 0 and x < self.width:
            if y >= 0 and y < self.height:
                return True
        else:
            return False
    
    def load_body(self, body: Body):
        x = int(body.position.x() // self.cell_width)
        y = int(body.position.y() // self.cell_height)
        if not self._check_coordinate(x, y):
            return
        idx = x  * self.height + y
        self.cells[idx].add_body(body)
    
    
    def unload_body(self):
        for cell in self.cells:
            cell.unload_body()
    
    def check_collision(self, idx):
        width = self.width
        height = self.height
        if idx >= width * height or idx < 0:
            # invalid idx
            return
        cell = self.cells[idx]
        for body in cell.bodies:
            if body.type == Body.Type.Static:
                continue
            self._check_body_cell(body, self._cell(idx - 1))
            self._check_body_cell(body, self._cell(idx))
            self._check_body_cell(body, self._cell(idx + 1))
            self._check_body_cell(body, self._cell(idx + height - 1))
            self._check_body_cell(body, self._cell(idx + height))
            self._check_body_cell(body, self._cell(idx + height + 1))
            self._check_body_cell(body, self._cell(idx - height - 1))
            self._check_body_cell(body, self._cell(idx - height))
            self._check_body_cell(body, self._cell(idx - height + 1))

    @classmethod
    def _check_body_cell(cls, body: Body, cell: CollisionCell):
        if body == None or cell == None:
            return
        for bodyB in cell.bodies:
            contact = Contact(body, bodyB)
            contact.resolve()

