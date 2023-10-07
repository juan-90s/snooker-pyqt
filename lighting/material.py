
import numpy as np

class Material():
    _width: int
    _height: int
    diffuse_map: np.ndarray
    normal_map: np.ndarray
    def __init__(self):
        self._width = None
        self._height = None
        self.diffuse_map = None
        self.normal_map = None
        self.alpha_map = None
    def set_diffuse_map(self, _map: np.ndarray):
        self.diffuse_map = _map[:,:,:3]
        if _map.shape[2] == 4:
            self.alpha_map = _map[:,:,-1][:,:,np.newaxis]
        else:
            self.alpha_map = np.ones((_map.shape[0], _map.shape[1], 1))
        if not self._width:
            self._width, self._height = _map.shape[:2]
        elif _map.shape[:2] != (self._width, self._height):
            raise Exception('set_diffuse_map size ', _map.shape[:2], ' is not matched ', (self._width, self._height))


    def set_normal_map(self, _map: np.ndarray):
        self.normal_map = _map
        if self._width:
            self._width, self._height = _map.shape[:2]
        elif _map.shape[:2] != (self._width, self._height):
            raise Exception('set_normal_map size is not matched')

    def size(self) ->tuple:
        return (self._width, self._height)