import numpy as np
from qudi.util.basis_transformations.basis_transformation_helpers import assert_np_square_mat, \
    gram_schmidt_columns, computational_basis
from qudi.util.math import normalize

def basis_from_points(points:np.ndarray)->np.ndarray:
    """
    Points is a N x N numpy ndarray. Points should be given like so np.array([p0, p1, p2, ..., pn-1])
    """
    assert_np_square_mat(points)
    # first we built the vectors that define the new "plane"
    # then we make them one after another orthogonal to each other
    # at last we insert the first point and make it orthogonal with all the rest.
    no_vecs = np.copy(points - points[0])
    no_vecs[-1,:] = np.copy(points[0])
    o_vecs = gram_schmidt_columns(no_vecs)
    return o_vecs

def point_in_new_basis(components:np.ndarray, old_basis:np.ndarray, new_basis:np.ndarray)->np.ndarray:
    """
    Given the components in `old_basis` return the components in the `new_basis`.
    """
    old_vec = components * old_basis
    # need to project the input vector onto all the axes
    overlaps = np.array([np.dot(basis_vec_new, basis_vec_old) for basis_vec_new, basis_vec_old
                         in zip(new_basis, old_basis)])
    new_components = np.array([sum([old_component * np.dot(old_vec, new_vec) for old_vec,
                       old_component in zip(components, old_basis)])
                       for new_vec in new_basis])
    return new_components

def is_orthogonal_basis(basis:np.ndarray)->np.bool_:
    """
    we want to check if the matrix consisting of the basis vectors [b0, b1, ... ,bn-1]
    gives the kronecker delta
    upon matrix multiplication.
    """
    assert_np_square_mat(basis)
    res = np.matmul(basis.T, basis)
    expected_result = computational_basis(basis.shape[0])
    print(type(np.all(res==expected_result)))
    return np.all(res==expected_result)

def point_in_new_basis_shifted(components:np.ndarray, old_basis:np.ndarray, new_basis:np.ndarray,
                               shift:np.ndarray)->np.ndarray:
    new_components = point_in_new_basis(components, old_basis, new_basis)
    return new_components + shift

def det_changing_axes(points: np.ndarray) -> np.ndarray:
    """
    Determine the axes that are changing.
    @param numpy ndarray points: [[p00, p01, p02 ...], [p10, p11, ...], ...]
    The second indice describes the axis, whereas the first one describes the points.
    To further illustrate: points[point, component_of_point_along_axis]

    If there is $|p_ij - pkj| > 0$ then
    bj will hold the value "True"
    @return numpy ndarray: [b0, b1, ..., bj, ...]
    """
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
    """
    Given input
    @param numpy ndarray points: [[p00, p01, p02 ...], [p10, p11, ...], ...]
    with dimensions n x m this will return a vectors n x m_r with m_r the
    axes that are not the same for all axes among the different points.
    """
    axes_changing_p = det_changing_axes(points)
    return points[:, axes_changing_p]

# code for 3D rotation matrix, roughly following chat GPT
def compute_rotation_mat_rodriguez(v0: np.ndarray, v1: np.ndarray, v2: np.ndarray) -> np.ndarray:
    if len(v0) != 3 or len(v1) != 3 or len(v2) != 3:
        raise ValueError('The support vectors should have a length of 3.')
    s0 = v1 - v0
    s1 = v2 - v0
    print("function updated")
    rot_axis = normalize(np.cross(s0, s1))[0]

    kx, ky, kz = rot_axis
    k_mat = np.array([[0.0, -kz, ky], [kz, 0.0, -kx], [-ky, kx, 0.0]])
    # See the math here: https://en.wikipedia.org/wiki/Rodrigues'_rotation_formula
    theta = np.arccos(np.dot(rot_axis, np.array([0, 0, 1])))
    return np.eye(3) + np.sin(theta) * k_mat + (1 - np.cos(theta)) * np.matmul(k_mat, k_mat)
