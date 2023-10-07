import numpy as np
from PySide6.QtGui import QVector2D, QVector3D, QPixmap, QImage

def plain_local(width, height, width_world=None, height_world=None) ->np.ndarray:
    if width_world is None:
        width_world = width
    if height_world is None:
        width_world = height
    x = np.linspace(0, width_world - 1, width)
    y = np.linspace(0, height_world - 1, height)
    X,Y = np.meshgrid(x,y)
    Z = np.zeros(X.shape)
    return np.stack((X,Y,Z),axis=-1)

def sphere_local(image:np.ndarray) -> np.ndarray:
    width, height = image.shape[:2]
    if not width == height:
        raise Exception("image has different width and height can not be built into sphere")
    radius = width//2
    # regardless x y actually stand for
    x = np.linspace(-radius, radius, width)
    y = np.linspace(-radius, radius, height)
    X,Y = np.meshgrid(x,y)
    Z = np.sqrt(radius**2 - X**2 - Y**2)
    local_map = np.stack((X,Y,Z),axis=-1)
    nan_mask = np.isnan(local_map[:,:,2])
    local_map[:,:,:][nan_mask] = 0
    return local_map

def sphere_normal(image:np.ndarray) -> np.ndarray:
    width, height = image.shape[:2]
    if not width == height:
        raise Exception("image has different width and height can not be built into sphere")
    x = np.linspace(-1, 1, width)
    y = np.linspace(-1, 1, height)
    X,Y = np.meshgrid(x,y)
    Z = np.sqrt(1 - X**2 - Y**2)
    normal_map = np.stack((X,Y,Z),axis=-1)
    nan_mask = np.isnan(normal_map[:,:,2])
    normal_map[:,:,:][nan_mask] = 0
    return normal_map

def Array_from_QImage(qimage: QImage) -> np.ndarray:
    width = qimage.width()
    height = qimage.height()
    if qimage.hasAlphaChannel():
        colors = 4
    else:
        colors = 3
    pixel_data = qimage.constBits()
    image_array = np.frombuffer(pixel_data, dtype=np.uint8).reshape((height, width, colors)).astype(dtype=np.float32)
    # image_array = np.transpose(image_array, (1,0,2))
    return image_array

def QImage_from_Array(image_array: np.ndarray) -> QImage:
    # image_array = np.transpose(image_array, (1,0,2))
    height, width = image_array.shape[:2]
    image_array = image_array.astype(dtype=np.uint8)
    colors = image_array.shape[2]
    return QImage(image_array.data, width, height, width * colors, QImage.Format_ARGB32)

def Array_from_QVector3D(vector: QVector3D) -> np.ndarray:
    return np.array(vector.toTuple())



