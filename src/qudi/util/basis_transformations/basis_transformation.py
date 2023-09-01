import numpy as np

from qudi.util.math import normalize

def det_changing_axes(points: np.ndarray) -> np.ndarray:
    num_axes = len(points[0])
    axes_changing_p = np.zeros(num_axes, dtype=np.bool_)
    # substract each
    for axis in range(num_axes):
        elements = points[:, axis]
        for ii, element in enumerate(points[:, axis]):
            d_elements = np.abs(element - elements[ii+1:])
            if np.any(d_elements > 0):
                axes_changing_p[axis] = True
                break
    return axes_changing_p

def compute_reduced_vectors(points: np.ndarray) -> np.ndarray:
    axes_changing_p = det_changing_axes(points)
    return points[:, axes_changing_p]

def compute_rotation_mat_rodriguez(v0: np.ndarray, v1: np.ndarray, v2: np.ndarray) -> np.ndarray:
    if len(v0) != 3 or len(v1) != 3 or len(v2) != 3:
        raise ValueError('The support vectors should have a length of 3.')
    s0 = v1 - v0
    s1 = v2 - v0
    ez = np.asarray([0,0,1])

    normal_plane_vec = normalize(np.cross(s0, s1))[0]
    rot_axis = normalize(np.cross(normal_plane_vec, ez))[0]

    kx, ky, kz = rot_axis[0], rot_axis[1], rot_axis[2]
    k_mat = np.array([[0.0, -kz, ky], [kz, 0.0, -kx], [-ky, kx, 0.0]])

    theta = -np.arccos(np.dot(normal_plane_vec, ez))
    if theta > np.pi/2 or theta < -np.pi/2:
        theta = -(np.pi-theta)

    # See the math here: https://en.wikipedia.org/wiki/Rodrigues'_rotation_formula
    return np.eye(3) + np.sin(theta) * k_mat + (1 - np.cos(theta)) * np.matmul(k_mat, k_mat)
