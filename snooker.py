from PySide6.QtCore import QSize, Qt, Signal, Slot, QThreadPool, QRunnable, QTimer
from PySide6.QtGui import QColor, QPainter, QPixmap, QVector2D as Vec2, QRasterWindow, QTransform

from physics import PhysicsManager, Body, Circle, Edge, Shape, PhysicsManager_Grid

import math
from enum import Enum

def rotatePixmap(pm: QPixmap, radian: float) -> QPixmap:
        w = pm.size().width()
        h = pm.size().height()
        my_transform = QTransform()
        #my_transform.translate(-w/2, -h/2)
        my_transform.rotateRadians(radian)
        #my_transform.translate(w/2, h/2)
        return pm.transformed(my_transform)

class Ball(object):
    radius = 10.0
    
    def __init__(self, pos:Vec2):
        super().__init__()
        self.body = Body(Circle(Ball.radius),Body.Type.Dynamic)
        self.body.position = pos

    
    def position(self) -> Vec2:
        return self.body.position
    
    def angle(self) -> float:
        return self.body.angle
    
    def speed(self) -> float:
        return self.body.linear_velocity.length()
    
    def hit(self, impulse):
        self.body.applyImpulseLinear(impulse)

class Cushion():

    class Face(Enum):
        UP = 0
        DOWN = 1
        LEFT = 2
        RIGHT = 3

    pos1: Vec2
    pos2: Vec2
    orientation: Face

    corner_radius = 15
    
    def __init__(self, pos1, pos2, orientation):
        corner_radius = Cushion.corner_radius
        self.pos1 = pos1
        self.pos2 = pos2
        self.orientation = orientation
        self.edge = Body(Edge(pos2 - pos1), Body.Type.Static)
        self.edge.position = pos1
        self.corner1 = Body(Circle(corner_radius), Body.Type.Static)
        self.corner2 = Body(Circle(corner_radius), Body.Type.Static)
        match orientation:
            case Cushion.Face.UP:
                self.corner1.position = pos1 + Vec2(0, corner_radius)
                self.corner2.position = pos2 + Vec2(0, corner_radius)
            case Cushion.Face.DOWN:
                self.corner1.position = pos1 - Vec2(0, corner_radius)
                self.corner2.position = pos2 - Vec2(0, corner_radius)
            case Cushion.Face.LEFT:
                self.corner1.position = pos1 + Vec2(corner_radius, 0)
                self.corner2.position = pos2 + Vec2(corner_radius, 0)
            case Cushion.Face.RIGHT:
                self.corner1.position = pos1 - Vec2(corner_radius, 0)
                self.corner2.position = pos2 - Vec2(corner_radius, 0)
        
    

class SnookerBoard(QRasterWindow):
    physicManager: PhysicsManager
    board_size = Vec2(400,800)

    def __init__(self, width:int, height:int, parent=None):
        super().__init__(parent)

        world_size = self.board_size
        world_w = self.board_size.x()
        world_h = self.board_size.y()

        # Timer
        self._timer = QTimer(self)
        self._timer.setInterval(1000//60)
        self._timer.timeout.connect(self.update)
        

        self.hit_timer = QTimer(self)
        self.hit_timer.setInterval(2000)
        
        self.ball_list = []
        self.ball_focused = None

        pockets = []
        pockets.append(Vec2(5/128,5/256) * world_size)
        pockets.append(Vec2(122/128,5/256) * world_size)
        pockets.append(Vec2(5/128,128/256) * world_size)
        pockets.append(Vec2(122/128,128/256) * world_size)
        pockets.append(Vec2(5/128,250/256) * world_size)
        pockets.append(Vec2(122/128,250/256) * world_size)
        self.pockets = pockets

        cushions = []
        # Top and Bottom
        cushions.append(Cushion(Vec2(14/128, 8/256) * world_size, Vec2(114/128, 8/256) * world_size, Cushion.Face.DOWN))
        cushions.append(Cushion(Vec2(14/128, 248/256) * world_size, Vec2(114/128, 248/256) * world_size, Cushion.Face.UP))
        # Left Top and Left Bottom
        cushions.append(Cushion(Vec2(8/128, 14/256) * world_size, Vec2(8/128, 120/256) * world_size, Cushion.Face.RIGHT))
        cushions.append(Cushion(Vec2(8/128, 137/256) * world_size, Vec2(8/128, 242/256) * world_size, Cushion.Face.RIGHT))
        # Right Top and Right Bottom
        cushions.append(Cushion(Vec2(120/128, 14/256) * world_size, Vec2(120/128, 120/256) * world_size, Cushion.Face.LEFT))
        cushions.append(Cushion(Vec2(120/128, 137/256) * world_size, Vec2(120/128, 242/256) * world_size, Cushion.Face.LEFT))
        self.cushions = cushions



        # Physics

        self.max_hit_force = 500.0
        grid_manager = False
        if not grid_manager:
            self.physicManager = PhysicsManager(self._timer)
            for obj in cushions:
                self.physicManager.add_body(obj.edge)
                self.physicManager.add_body(obj.corner1)
                self.physicManager.add_body(obj.corner2)
        else:
            self.physicManager = PhysicsManager_Grid(self._timer, world_w, world_h, 2, 4)
            for obj in cushions:
                self.physicManager.add_static_body(obj.corner1)
                self.physicManager.add_static_body(obj.corner2)
            self.physicManager.add_static_body_multicell(cushions[0].edge, [(0,0),(1,0)])
            self.physicManager.add_static_body_multicell(cushions[1].edge, [(0,3),(1,3)])
            self.physicManager.add_static_body_multicell(cushions[2].edge, [(0,0),(0,1)])
            self.physicManager.add_static_body_multicell(cushions[3].edge, [(0,2),(0,3)])
            self.physicManager.add_static_body_multicell(cushions[4].edge, [(1,0),(1,1)])
            self.physicManager.add_static_body_multicell(cushions[5].edge, [(1,2),(1,3)])
        
        self.physicManager.global_friction = 0.5
        wh_ratio = world_w / world_h

        if(width < height * wh_ratio):
            self.resize(width, width / wh_ratio)
            self.zoom = self.width() / world_w
        else:
            self.resize(height * wh_ratio, height)
            self.zoom = self.height() / world_h
        
        # UI
        self.cursor_position = Vec2(0,0)
        self.mouseRightPressed = False
        self.mouseLeftPressed = False

        self.ball_pixmap = QPixmap()
        self.ball_pixmap.load("ball.png")

        self.background = QPixmap()
        self.background.load("snookeboard.png")

        # start loop
        self._timer.start()
    
    def add_ball(self, position: Vec2):
        new_ball = Ball(position)
        self.ball_list.append(new_ball)
        self.physicManager.add_body(new_ball.body)
    
    def remove_ball(self, ball: Ball):
        self.physicManager.remove_body(ball.body)
        self.ball_list.remove(ball)

    def hit_level(self):
        return (math.cos(self.hit_timer.remainingTime() / self.hit_timer.interval() * 2 * math.pi - math.pi) + 1) / 2
     
    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.mouseRightPressed = True
            mouse_position = Vec2(event.position())
            self.add_ball(mouse_position / self.zoom)
        elif event.button() == Qt.LeftButton:
            self.mouseLeftPressed = True
            self.hit_timer.start()
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton:
            self.mouseRightPressed = False
        elif event.button() == Qt.LeftButton:
            self.mouseLeftPressed = False
            if self.ball_focused:
                force = self.max_hit_force * self.hit_level() * (self.cursor_position - self.ball_focused.position()).normalized()
                self.ball_focused.hit(force)
                self.hit_timer.stop()
    
    def mouseMoveEvent(self, event):
        cursor_position = Vec2(event.position()) / self.zoom
        self.cursor_position = cursor_position
        if not self.mouseLeftPressed:
            nearest_distance = 1000000.0
            nearest_ball = None
            for ball in self.ball_list:
                distance = (ball.position() - cursor_position).length()
                if distance < nearest_distance:
                    nearest_distance = distance
                    nearest_ball = ball
            self.ball_focused = nearest_ball
        
    
    def paintEvent(self, e):
        with QPainter(self) as p:
            self.render(p)

    def render(self,p):
        zoom = self.zoom
        # p.fillRect(0, 0, self.width(), self.height(), Qt.black)
        p.drawPixmap(0,0,self.width(), self.height(), self.background)
        p.setPen(QColor(250, 120, 120))
        p.drawText(40, 40, 'physic_time: '+str(self.physicManager.frametime))
        for ball in self.ball_list:
            render_r = int(Ball.radius * zoom)
            pos = ball.position() * zoom
            p.drawEllipse(pos.toPoint(), render_r, render_r)
            pm = self.ball_pixmap
            p.drawPixmap(pos.x() - render_r, pos.y() - render_r, render_r * 2, render_r * 2, pm)
        
        if self.ball_focused:
            p.drawText(40, 50, 'ball_speed: '+str(self.ball_focused.speed()/self._timer.interval()))
            p.setPen(QColor(200, 200, 200))
            pos = self.ball_focused.position()
            p.drawEllipse((pos * zoom).toPoint(), render_r // 2, render_r // 2)
            if self.mouseLeftPressed:
                a = pos * zoom
                b = self.cursor_position * zoom
                a_b = a + (b - a).normalized() * self.hit_level() * 80
                p.drawLine(a.toPoint(), a_b.toPoint())
                gray = int(self.hit_level() * 200 + 50)
                p.setPen(QColor(gray, gray, gray))
                p.drawEllipse(b.toPoint(), render_r, render_r)
        
        for obj in self.cushions:
            corner_radius = Cushion.corner_radius * zoom
            p.drawLine((obj.pos1 * zoom).toPoint(), (obj.pos2 * zoom).toPoint())
            p.drawEllipse((obj.corner1.position * zoom).toPoint(), corner_radius, corner_radius)
            p.drawEllipse((obj.corner2.position * zoom).toPoint(), corner_radius, corner_radius)

    
    def update(self):
        super().update()
        for ball in self.ball_list:
            for hole in self.pockets:
                if (ball.position() - hole).lengthSquared() < Ball.radius:
                    self.remove_ball(ball)
                    self.ball_focused = None
                    print("hit")
    
    

    

