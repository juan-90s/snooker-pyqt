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
    k_glossy = 1
    def __init__(self):
        pass
        self.lighting_list = []
        self.ambient_intensity = 0.1
        self.ambient_color = np.array([1,1,1])
        self.view = np.array([0,0,1])
    

    def add_light_source(self, source):
        self.lighting_list.append(source)

    def set_color(self, color):
        if isinstance(color, QColor):
            self.ambient_color = np.array((color.redF(), color.greenF(), color.blueF()))

    def illuminate(self, surface, material:Material, transform:np.ndarray=None)->np.ndarray:
        if surface.shape[:2] != material.diffuse_map.shape[:2]:
            raise Exception("currently not support resample, surface: ", surface.shape[:2], "diffuse_map: ",material.diffuse_map.shape[:2])
        I_diffuse = np.zeros((material.size()[0], material.size()[1], 3))
        I_specular = np.zeros(shape=I_diffuse.shape)
        for source in self.lighting_list:
            source_pos = source.position.copy()
            source_drt = source.direction.copy()
            if transform is not None:
                source_pos[2] = 1
                source_pos = transform @ source_pos
                source_pos[2] = source.position[2]
                
                source_drt[2] = 0
                source_drt = transform @ source_drt
                source_drt[2] = source.direction[2]

            match source.type:
                case LightSource.Type.Parallel:
                    if material.normal_map is not None:
                        n_l = np.dot(material.normal_map, -source.direction)
                        lambert = np.maximum(n_l, 0)
                        reflection = material.normal_map * n_l[:, :, np.newaxis] * 2 + source.direction[np.newaxis, np.newaxis, :]
                        reflection = np.maximum(reflection, 0)
                        phong = np.dot(reflection, self.view) ** material.metalness
                    else:
                        lambert = np.ones(I_diffuse.shape[:2])
                        phong = np.ones(I_specular.shape[:2]) ** material.metalness
                    I_diffuse_i = source.intensity * lambert
                    I_specular_i = source.intensity * self.k_glossy * phong

                case LightSource.Type.Spot:
                    # light intensity
                    spot2surface = (surface - source_pos)
                    distance = np.sqrt(np.sum(spot2surface**2,axis=-1))
                    spot2surface_unit = spot2surface/np.expand_dims(distance, -1)
                    distance_factor = 1.0 / (self.f_a * distance**2 + self.f_b * distance + self.f_c)
                    spread_factor = np.dot(spot2surface_unit, source.direction) ** source.spread
                    intensity = source.intensity * distance_factor * spread_factor
                    # diffuse
                    if material.normal_map is not None:
                        n_l = np.sum(material.normal_map * -spot2surface_unit, axis=-1)
                        lambert = np.maximum(n_l, 0)
                        reflection = material.normal_map * n_l[:, :, np.newaxis] * 2 + spot2surface_unit
                        reflection = np.maximum(reflection, 0)
                        phong = np.dot(reflection, self.view) ** material.metalness
                    else:
                        lambert = np.ones(I_diffuse.shape[:2])
                        phong = np.ones(I_specular.shape[:2]) ** material.metalness
                    I_diffuse_i = intensity * lambert
                    I_specular_i = intensity * self.k_glossy * phong
            I_diffuse_i = I_diffuse_i[:, :, np.newaxis]
            I_specular_i = I_specular_i[:, :, np.newaxis]
            I_diffuse += (I_diffuse_i * source.color)
            I_specular += (I_specular_i * source.color)
        diffuse = material.diffuse_map * I_diffuse
        ambient = material.diffuse_map * self.ambient_color * self.ambient_intensity
        specular = material.smoothness * I_specular * 255
        illuminated = np.minimum(diffuse + ambient + specular, 255)
        return np.concatenate((illuminated, material.alpha_map), axis=-1)
