import sys

from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import QTimer, Slot, Signal, Qt
from PySide6.QtGui import QVector2D, QPainter, QColor, QPen, QRasterWindow

from physics import *
import random
import math
from queue import Queue

color_palette = ['#2ecc71', '#3498db', '#27ae60', '#e74c3c', '#9b59b6', '#ecf0f1', '#f1c40f', '#f39c12', '#e67e22']

class PhysicsManager_Gravity(PhysicsManager):
    def __init__(self):
        super().__init__()
        self.gravity = 0
        self.gravity_center = None

    def solve_movement(self, dt):
        for body in self._bodies:
            body.update(dt)
            if body.type is not Body.Type.Dynamic:
                continue
            if self.gravity > 0:
                # gravity
                if self.gravity_center is not None:
                    diff = self.gravity_center - body.position
                    lengthSquared = diff.lengthSquared()
                    if lengthSquared < 100:
                        body.linear_velocity *= 0
                    else:
                        vec_G = diff.normalized() / lengthSquared
                        vec_G *= self.gravity * 20000 * dt
                        body.linear_velocity += vec_G
                else:
                    body.linear_velocity += Vec2(0, self.gravity*dt)


class Ball():
    def __init__(self, radius:float, color=None):
        self.radius = radius

        self.color = QColor(random.choice(color_palette))
        self.body = Body(Circle(radius), Body.Type.Dynamic)
        self.body.elasticity = 0.8
        self.body.set_mass(2 * math.pi * radius**2)
    
    def position(self):
        return self.body.position

    def paint(self, p: QPainter):
        pen = QPen(self.color.darker(),3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(self.color)
        p.drawEllipse(self.position().toPoint(), self.radius, self.radius)
        r = self.radius

class Ledge():
    def __init__(self, p1:QVector2D, p2:QVector2D):
        self.p1 = p1
        self.p2 = p2
        self.body = Body(Edge(p2 - p1), Body.Type.Static)
        self.body.position = p1

    def paint(self, p: QPainter):
        pen = QPen(QColor('#7f8c8d'),5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        p.drawLine(self.p1.toPoint(), self.p2.toPoint())

class Field(QRasterWindow):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.resize(1280, 720)
        self.ball_list = []
        self.ledge_list = []
        self.physics = PhysicsManager_Gravity()
        self.physics.gravity = 200
        # self.border = {}
        # self.border['up'] = Body(Edge(QVector2D(self.width(),0)),Body.Type.Static)
        # self.border['up'].position = QVector2D(0, 0)
        # self.border['down'] = Body(Edge(QVector2D(self.width(),0)),Body.Type.Static)
        # self.border['down'].position = QVector2D(0, self.height())
        # self.border['left'] = Body(Edge(QVector2D(0,self.height())),Body.Type.Static)
        # self.border['left'].position = QVector2D(0, 0)
        # self.border['right'] = Body(Edge(QVector2D(0,self.height())),Body.Type.Static)
        # self.border['right'].position = QVector2D(self.width(), 0)
        # for i in self.border:
        #     self.physics.add_body(self.border[i])
        
        self._timer = QTimer(self)
        self._timer.setInterval(1000//60)
        self._timer.timeout.connect(self.update)
        self._timer.start()

        self.last_click = None
        self.cursor_position = Vec2(0,0)
        self.mouseRightPressed = False
        self.mouseLeftPressed = False
        self.mouseMiddlePressed = False

        self.overstep = 0
        self.cum = 1.0
        # self.physics.gravity_center = Vec2(self.width()/2, self.height()/2)

    def add_ball(self, position):
        radius = random.randint(15,30)
        ball = Ball(radius)
        ball.body.position = position
        self.ball_list.append(ball)
        self.physics.add_body(ball.body)

        # diff = position - self.physics.gravity_center
        # du = diff.normalized()
        # rsr = math.sqrt(diff.length())
        # rm = random.gauss(1,0.1)
        # ball.body.linear_velocity = Vec2(-du.y() * 2000 * rm / rsr, du.x() * 2000 * rm / rsr)
    def add_ledge(self, p1, p2):
        ledge = Ledge(p1,p2)
        self.ledge_list.append(ledge)
        self.physics.add_body(ledge.body)

    def remove_ball(self, ball):
        self.physics.remove_body(ball.body)
        self.ball_list.remove(ball)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.mouseRightPressed = True
            mouse_position = Vec2(event.position())
            self.add_ball(mouse_position)
        elif event.button() == Qt.LeftButton:
            self.mouseLeftPressed = True
            self.last_click = Vec2(event.position())
            self.cursor_position = Vec2(event.position())
        elif event.button() == Qt.MiddleButton:
            self.mouseMiddlePressed = True
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton:
            self.mouseRightPressed = False
        elif event.button() == Qt.LeftButton:
            if self.mouseLeftPressed:
                self.add_ledge(self.last_click, Vec2(event.position()))
            self.mouseLeftPressed = False
        elif event.button() == Qt.MiddleButton:
            self.mouseMiddlePressed = False
    
    def mouseMoveEvent(self, event):
        self.cursor_position = Vec2(event.position())
        if not self.mouseLeftPressed:
            self.last_click = Vec2(event.position())
        
        if self.mouseMiddlePressed:
            self.physics.gravity_center = Vec2(event.position())
    
    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.cum -= 0.05
            if self.cum < 0.05:
                self.cum = 0.05
        else:
            self.cum += 0.05
            if self.cum > 1:
                self.cum = 1
    def resizeEvent(self, event):
        new_size = event.size()
        new_width = new_size.width()
        new_height = new_size.height()
        # self.border['up'].shape.vec = QVector2D(new_width,0)
        # self.border['down'].shape.vec = QVector2D(new_width,0)
        # self.border['down'].position = QVector2D(0, new_height)
        # self.border['left'].shape.vec = QVector2D(0,new_height)
        # self.border['right'].shape.vec = QVector2D(0,new_height)
        # self.border['right'].position = QVector2D(new_width, 0)

    def paintEvent(self, event):
        with QPainter(self) as p:
            p.setRenderHints(QPainter.Antialiasing)
            self.overstep = (self.overstep + 1) % 1
            if self.overstep == 0:
                c = QColor('#34495e')
                c.setAlphaF(self.cum)
                p.fillRect(0, 0, self.width(), self.height(), c)
            # p.fillRect(0, 0, self.width(), self.height(), QColor('#34495e'))
            # p.drawText(20,20, str(self.physics.frametime))
            if self.mouseLeftPressed:
                pen = QPen(QColor('#7f8c8d'),5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                p.setPen(pen)
                p.drawLine(self.last_click.toPoint(), self.cursor_position.toPoint())

            for ball in self.ball_list:
                ball.paint(p)
                if (ball.position()-QVector2D(self.width()/2, self.height()/2)).lengthSquared() > self.height()**2 + self.width()**2:
                    self.remove_ball(ball)
                # if ball.position().y() + ball.radius > self.height():
                #     ball.position().setY(self.height() - ball.radius)
                #     ball.body.linear_velocity.setY(0)
            
            for ledge in self.ledge_list:
                ledge.paint(p)
            

            
    

class MainWindow(QWidget):
    def _init__(self, parent= None):
        super().__init__()



if __name__ == '__main__':
    app = QApplication(sys.argv)
    widget = Field()
    widget.show()
    sys.exit(app.exec())