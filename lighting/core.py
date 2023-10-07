import numpy as np
from lighting.illuminant import *
from lighting.material import *
class LightingManager():
    lighting_list: [LightSource]
    ambient_intensity: float
    # spotlight distance fraction
    f_a = 0.001
    f_b = 0.01
    f_c = 1
    def __init__(self):
        pass
        self.lighting_list = []
        self.ambient_intensity = 0.1
        self.ambient_color = np.array([1,1,1])
    

    def add_light_source(self, source):
        self.lighting_list.append(source)

    def set_color(self, color):
        if isinstance(color, QColor):
            self.ambient_color = np.array((color.redF(), color.greenF(), color.blueF()))

    def illuminate(self, surface, material:Material)->np.ndarray:
        if surface.shape[:2] != material.diffuse_map.shape[:2]:
            raise Exception("currently not support resample, surface: ", surface.shape[:2], "diffuse_map: ",material.diffuse_map.shape[:2])
        I_diffuse = np.zeros(shape=material.size())
        for source in self.lighting_list:
            match source.type:
                case LightSource.Type.Parallel:
                    if material.normal_map is not None:
                        lambert = np.maximum(np.dot(material.normal_map, -source.direction), 0)
                    else:
                        lambert = np.ones(I_diffuse.shape)
                    I_diffuse_i = source.intensity * lambert

                case LightSource.Type.Spot:
                    spot2surface = (surface - source.position)
                    distance = np.sqrt(np.sum(spot2surface**2,axis=-1))
                    spot2surface_unit = spot2surface/np.expand_dims(distance, -1)
                    distance_factor = 1.0 / (self.f_a * distance**2 + self.f_b * distance + self.f_c)
                    spread_factor = np.dot(spot2surface_unit, source.direction) ** source.spread

                    if material.normal_map is not None:
                        lambert = np.maximum(np.sum(material.normal_map * -spot2surface_unit, axis=-1), 0)
                    else:
                        lambert = np.ones(I_diffuse.shape)
                    I_diffuse_i = source.intensity * distance_factor * spread_factor * lambert
            I_diffuse += I_diffuse_i
        diffuse = material.diffuse_map * I_diffuse[:,:,np.newaxis]
        ambient = material.diffuse_map * self.ambient_color * self.ambient_intensity
        illuminated = np.minimum(diffuse + ambient, 255)
        return np.concatenate((illuminated, material.alpha_map), axis=-1)
