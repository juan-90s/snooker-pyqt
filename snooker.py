from PySide6.QtCore import QSize, Qt, Signal, Slot, QThreadPool, QRunnable, QTimer, QEvent  
from PySide6.QtGui import QColor, QPainter, QPixmap, QVector2D as Vec2, QRasterWindow, QTransform, QImage, QTransform, QGuiApplication, QResizeEvent
from PySide6.QtWidgets import QApplication, QWidget
from physics import PhysicsManager, Body, Circle, Edge, Shape, PhysicsManager_Grid
from lighting import LightSource, LightingManager, Material
from lighting.common import *

import sys
import math
from enum import Enum
import timeit
import random

def pole_normal(image:np.ndarray) -> np.ndarray:
    alpha_mask = image[:,:,3] != 0
    height, width = image.shape[:2]
    x = np.linspace(0, 1, width)
    y = np.linspace(-1, 1, height)
    X,Y = np.meshgrid(x,y)
    
    front = 4
    end = 8
    front /= height
    end /= height

    Y = Y / (X * (end - front) + front)
    Z = np.sqrt(1 - Y**2)
    X *= 0
    normal_map = np.stack((X,Y,Z),axis=-1)
    nan_mask = np.isnan(normal_map[:,:,2])
    normal_map[:,:,:][nan_mask] = 0
    normal_map *= alpha_mask[:, :, np.newaxis]
    return normal_map

def pole_surface(image:np.ndarray) -> np.ndarray:
    alpha_mask = image[:,:,3] != 0
    height, width = image.shape[:2]
    x = np.linspace(0, 1, width)
    y = np.linspace(-height, height, height)
    X,Y = np.meshgrid(x,y)
    
    front = 3
    end = 8

    Z = np.sqrt((X * (end - front) + front) - Y**2) + 20
    X *= width
    normal_map = np.stack((X,Y,Z),axis=-1)
    nan_mask = np.isnan(normal_map[:,:,2])
    normal_map[:,:,:][nan_mask] = 0
    normal_map *= alpha_mask[:, :, np.newaxis]
    return normal_map

class Ball(object):
    radius = 10.0

    class Color(Enum):
        White=0
        Red=1
        Pink=2
        Black=3
        Yellow=4
        Blue=5
        Brown=6
        Green=7
    
    def __init__(self, pos:Vec2, color:Color):
        super().__init__()
        self.body = Body(Circle(Ball.radius),Body.Type.Dynamic)
        self.body.position = pos
        self.texture = None
        self.color = color

    
    def position(self) -> Vec2:
        return self.body.position
    
    def angle(self) -> float:
        return self.body.angle
    
    def speed(self) -> float:
        return self.body.linear_velocity.length()
    
    def speedSquared(self) -> float:
        return self.body.linear_velocity.lengthSquared()
    
    def hit(self, impulse):
        self.body.applyImpulseLinear(impulse)
    
    def reset(self, position=None):
        self.body.linear_velocity *= 0
        self.body.angle_velocity *= 0
        if position is not None:
            self.body.position = position

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
        self.edge.elasticity = 0.6
        self.corner1 = Body(Circle(corner_radius), Body.Type.Static)
        self.corner2 = Body(Circle(corner_radius), Body.Type.Static)
        self.corner1.elasticity = 0.7
        self.corner2.elasticity = 0.7
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
    lighting_update_step_num = 3
    def __init__(self, width:int, height:int, parent=None, landscape=False):
        super().__init__(parent)
        
        self.installEventFilter(self)
        world_size = self.board_size
        world_w = self.board_size.x()
        world_h = self.board_size.y()
        wh_ratio = world_w / world_h
        self._render_transform = QTransform()

        if(width < height * wh_ratio):
            self.resize(width, width / wh_ratio)
            self.zoom = self.width() / world_w
        else:
            self.resize(height * wh_ratio, height)
            self.zoom = self.height() / world_h
        
        self.aspect_ratio = wh_ratio
        if landscape:
            self.aspect_ratio = 1/wh_ratio
            self._render_transform.rotate(90).scale(1, -1)
            self.resize(world_h * self.zoom, world_w * self.zoom)

        # Timer
        self._timer = QTimer(self)
        self._timer.setInterval(1000//60)
        self._timer.timeout.connect(self.update)
        

        self.hit_timer = QTimer(self)
        self.hit_timer.setInterval(2000)
        

        # Physics

        self.max_hit_force = 1000.0
        grid_manager = False
        self.physicManager = PhysicsManager(self._timer)
        self.physicManager.global_friction = 0.5
        
        # UI
        self.cursor_position = Vec2(0,0)
        self.mouseRightPressed = False
        self.mouseLeftPressed = False

        # Lighting
        self.lighting_update_step = 0

        self.lighting = LightingManager()
        self.lighting.ambient_intensity = 0.3
        paralell = LightSource(LightSource.Type.Parallel)
        paralell.set_position((0,0,120))
        paralell.set_direction((0,0,-1))
        paralell.intensity = 0.2
        bulb1 = LightSource(LightSource.Type.Spot)
        bulb1.set_position((200,250,130))
        bulb1.set_direction((0,0,-1))
        bulb1.spread = 0.1
        bulb1.intensity = 10
        bulb1.set_color(QColor('#ffffaa'))
        bulb2 = LightSource(LightSource.Type.Spot)
        bulb2.set_position((200,550,130))
        bulb2.set_direction((0,0,-1))
        bulb2.spread = 0.1
        bulb2.intensity = 10
        bulb2.set_color(QColor('#ffaaff'))
        self.lighting.add_light_source(bulb1)
        self.lighting.add_light_source(bulb2)


        # Texture
        ball_image = QImage()
        ball_image.load("ball.png")
        ball_image_array = Array_from_QImage(ball_image)
        ball_normal_map = sphere_normal(ball_image_array[0:16,0:16,:])

        ball_material_list = []
        for i in range(0, 8):
            mt1 = Material()
            mt1.set_diffuse_map(ball_image_array[:,16*i:16*(i+1),:])
            mt1.set_normal_map(ball_normal_map)
            mt1.smoothness = 0.5
            mt1.metalness = 10
            ball_material_list.append(mt1)
        self.ball_material_list = ball_material_list

        board_img = QImage()
        board_img.load("board.png")
        board_material = Material()
        board_material.set_diffuse_map(Array_from_QImage(board_img))
        board_surface = plain_local(board_img.width(), board_img.height(), world_w, world_h)
        board_texture = self.lighting.illuminate(board_surface, board_material)
        board_image_illum = QImage_from_Array(board_texture)

        self.pole_image = QImage()
        self.pole_image.load("pole.png")
        pole_array = Array_from_QImage(self.pole_image)
        self.pole_material = Material()
        self.pole_material.set_diffuse_map(pole_array)
        self.pole_material.set_normal_map(pole_normal(pole_array))
        self.pole_surface = pole_surface(pole_array)
        self.pole_texture = self.pole_image

        
        self.background = QPixmap.fromImage(board_image_illum)
        self.render_time = 0

        # Objects
        self.ball_list = []
        self.ball_focused = Ball(Vec2(200, 600), 0)
        self.physicManager.add_body(self.ball_focused.body)


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
        cushions.append(Cushion(Vec2(15/128, 8/256) * world_size, Vec2(113/128, 8/256) * world_size, Cushion.Face.DOWN))
        cushions.append(Cushion(Vec2(15/128, 248/256) * world_size, Vec2(113/128, 248/256) * world_size, Cushion.Face.UP))
        # Left Top and Left Bottom
        cushions.append(Cushion(Vec2(8/128, 15/256) * world_size, Vec2(8/128, 120/256) * world_size, Cushion.Face.RIGHT))
        cushions.append(Cushion(Vec2(8/128, 137/256) * world_size, Vec2(8/128, 241/256) * world_size, Cushion.Face.RIGHT))
        # Right Top and Right Bottom
        cushions.append(Cushion(Vec2(120/128, 15/256) * world_size, Vec2(120/128, 120/256) * world_size, Cushion.Face.LEFT))
        cushions.append(Cushion(Vec2(120/128, 137/256) * world_size, Vec2(120/128, 241/256) * world_size, Cushion.Face.LEFT))
        self.cushions = cushions

        
        for obj in cushions:
            self.physicManager.add_body(obj.edge)
            self.physicManager.add_body(obj.corner1)
            self.physicManager.add_body(obj.corner2)
        
        # start loop
        self._timer.start()
        self.resizing = False
    
    def add_ball(self, position: Vec2, ball_color: Ball.Color):
        new_ball = Ball(position, ball_color)
        self.ball_list.append(new_ball)
        self.physicManager.add_body(new_ball.body)
    
    def remove_ball(self, ball: Ball):
        self.physicManager.remove_body(ball.body)
        self.ball_list.remove(ball)

    def hit_level(self) -> float:
        return (math.cos(self.hit_timer.remainingTime() / self.hit_timer.interval() * 2 * math.pi - math.pi) + 1) / 2

    def is_active(self) -> bool:
        if self.ball_focused.speedSquared() < 0.01:
            return True
        else:
            return False
     
    def mousePressEvent(self, event):
        inverse = self._render_transform.inverted()[0].scale(1/self.zoom, 1/self.zoom)
        cursor_position = QVector2D(inverse.map(event.position()))
        if event.button() == Qt.RightButton:
            self.mouseRightPressed = True
            self.add_ball(cursor_position, random.randint(1,7))
        elif event.button() == Qt.LeftButton:
            self.mouseLeftPressed = True
            self.hit_timer.start()
    
    def mouseReleaseEvent(self, event):
        inverse = self._render_transform.inverted()[0].scale(1/self.zoom, 1/self.zoom)
        cursor_position = QVector2D(inverse.map(event.position()))
        if event.button() == Qt.RightButton:
            self.mouseRightPressed = False
        elif event.button() == Qt.LeftButton:
            self.mouseLeftPressed = False
            if self.is_active():
                force = self.max_hit_force * self.hit_level() * (cursor_position - self.ball_focused.position()).normalized()
                self.ball_focused.hit(force)
                self.hit_timer.stop()
    
    def mouseMoveEvent(self, event):
        inverse = self._render_transform.inverted()[0].scale(1/self.zoom, 1/self.zoom)
        cursor_position = QVector2D(inverse.map(event.position()))
        self.cursor_position = cursor_position

        

        # change focus ball
        # if not self.mouseLeftPressed:
        #     nearest_distance = 1000000.0
        #     nearest_ball = None
        #     for ball in self.ball_list:
        #         distance = (ball.position() - cursor_position).length()
        #         if distance < nearest_distance:
        #             nearest_distance = distance
        #             nearest_ball = ball
        #     self.ball_focused = nearest_ball
    
    def eventFilter(self, watched, event:QEvent):
        if watched == self:
            if event.type() == QEvent.Resize:
                new_width = event.size().width()
                new_height = event.size().height()
                old_width = event.oldSize().width()
                old_height = event.oldSize().height()
                if self.resizing or new_width == old_width and new_height == old_height:
                    self.resizing = False
                    return True
                elif new_width == old_width:
                    self.resize(old_width, old_height)
                    return False
                elif new_height == old_height:
                    self.resize(old_width, old_height)
                    return False
                else:
                    self.resize(new_height * self.aspect_ratio, new_height)
                    if self.aspect_ratio > 1:
                        # landscape
                        self.zoom = new_height / self.board_size.x()
                    else:
                        self.zoom = new_height / self.board_size.y()
                    return False
        return super().eventFilter(watched, event)
    
    def resizeEvent(self, event):
        self.resizing = True

    def paintEvent(self, e):
        with QPainter(self) as p:
            t = timeit.default_timer()
            self.render(p)
            self.render_time = 1000 * (timeit.default_timer() - t)
    

    def render_ball(self, ball: Ball, p: QPainter, update:bool = True):
        zoom = self.zoom
        render_r = int(Ball.radius) * zoom
        pos = ball.position() * zoom
        
        if self.lighting_update_step == 0 and update:
            ball_material = self.ball_material_list[ball.color]
            ball_surface = ball_material.normal_map*Ball.radius + Array_from_QVector3D(ball.position().toVector3D())
            ball.texture = QImage_from_Array(self.lighting.illuminate(ball_surface, ball_material))
        if ball.texture is not None:
            p.drawImage(pos.x() - render_r, pos.y() - render_r, ball.texture.scaled(render_r*2, render_r*2))
        else:
            p.drawPoint(pos.toPoint())
    
    def render_pole(self, p:QPainter):
        render_r = int(Ball.radius)
        hit_d = Ball.radius + 5
        if self.mouseLeftPressed:
            hit_d += self.hit_level() * 20
        a = self.ball_focused.position()
        direction = (self.ball_focused.position() - self.cursor_position).normalized()
        rotate = lambda v: QTransform(v.x(), v.y(), -v.y(), v.x(), 0, 0)
        rotate_counter = lambda v: QTransform(v.x(), -v.y(), v.y(), v.x(), 0, 0)
        translate = lambda dx,dy: QTransform(1,0,0,1,dx,dy)
        scale = lambda x,y: QTransform(x, 0, 0, y, 0, 0)
        transform = translate(hit_d, -3) * rotate(direction) * scale(1.5, 1.5) * translate(a.x(),a.y())
        inv_transform = translate(-a.x(),-a.y()) * scale(2/3, 2/3) * rotate_counter(direction) * translate(-hit_d, 3)
        if self.lighting_update_step == 0:
            transform_matrix = Matrix_from_QTransform(inv_transform)
            self.pole_texture = QImage_from_Array(self.lighting.illuminate(self.pole_surface, self.pole_material, transform_matrix))
        p.setTransform(transform * self._render_transform * scale(self.zoom, self.zoom))
        p.drawImage(0, 0, self.pole_texture)
        p.setTransform(self._render_transform * scale(self.zoom, self.zoom))

    def render(self,p):
        # p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(0, 0, self.width(), self.height(), Qt.black)
        p.setTransform(self._render_transform)
        p.scale(self.zoom, self.zoom)
        p.drawPixmap(0,0,self.board_size.x(), self.board_size.y(), self.background)
        p.setPen(QColor(250, 120, 120))
        p.drawText(40, 30, 'mouse_point: '+str(self.cursor_position.toTuple()))
        p.drawText(40, 40, 'physic_time: '+str(self.physicManager.frametime))
        p.drawText(40, 50, 'render_time: '+str(self.render_time))
        render_r = int(Ball.radius * self.zoom)
        self.lighting_update_step = (self.lighting_update_step + 1) % self.lighting_update_step_num

        # for obj in self.cushions:
        #     corner_radius = Cushion.corner_radius
        #     p.drawLine((obj.pos1).toPoint(), (obj.pos2).toPoint())
        #     p.drawEllipse((obj.corner1.position).toPoint(), corner_radius, corner_radius)
        #     p.drawEllipse((obj.corner2.position).toPoint(), corner_radius, corner_radius)

        # render balls, remove pre scale in painter to avoid bad upscaling on ball textures
        p.setTransform(self._render_transform)
        for ball in self.ball_list:
            upd = True
            if ball.texture is not None and ball.speedSquared() < 0.01:
                upd = False
            self.render_ball(ball, p, upd)
        
        if not self.ball_focused:
            return
        self.render_ball(self.ball_focused, p)
        p.scale(self.zoom, self.zoom)

        if self.is_active():
            # indicator line
            p.drawEllipse(self.cursor_position.toPoint(), Ball.radius, Ball.radius)
            p.drawLine(self.ball_focused.position().toPoint(), self.cursor_position.toPoint())

            self.render_pole(p)
            
            
    
    def update(self):
        super().update()
        for ball in self.ball_list:
            hit = False
            pos = ball.position()
            if (pos.x() < 3 or pos.x() > self.board_size.x() - 3) or (pos.y() < 3 or pos.y() > self.board_size.y() - 3):
                hit = True
            else:
                for hole in self.pockets:
                    if (pos - hole).lengthSquared() < Ball.radius**2-Ball.radius:
                        hit = True
                        break
            
            if hit:
                self.remove_ball(ball)
                print("hit")
        
        if self.ball_focused:
            ball = self.ball_focused
            hit = False
            pos = ball.position()
            if (pos.x() < 3 or pos.x() > self.board_size.x() - 3) or (pos.y() < 3 or pos.y() > self.board_size.y() - 3):
                hit = True
            else:
                for hole in self.pockets:
                    if (pos - hole).lengthSquared() < Ball.radius**2-Ball.radius:
                        hit = True
                        break
            
            if hit:
                self.ball_focused.reset(Vec2(200 * self.zoom, 600 * self.zoom))
                print("OOPS")
    

if __name__ == '__main__':
    
    app = QGuiApplication([])
    game = SnookerBoard(400,800,landscape=True)
    game.show()
    sys.exit(app.exec()) 

