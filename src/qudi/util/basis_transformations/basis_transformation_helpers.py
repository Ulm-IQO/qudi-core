import numpy as np
from numpy.typing import NDArray

def random_vectors(shape):
    vectors = np.random.rand(*shape)
    return vectors

def random_points(scale:float, offset:float=0.0, dim:int=3)->np.ndarray:
    return scale * np.random.rand(dim) + offset

def computational_basis(dim:int)->NDArray:
    return np.diag(np.ones(dim))

def scalar_product_along_axis(mat:NDArray[np.floating])->NDArray[np.floating]:
    return np.apply_along_axis(lambda x: np.dot(x, x), 0, mat)

def gram_schmidt_columns(X):
    Q, _ = np.linalg.qr(X)
    return Q

def assert_np_square_mat(mat:NDArray)->None:
    assert type(mat) == np.ndarray, "Input should be of type np.ndarray"
    assert len(mat.shape) == 2, "Input should be a two D matrix"
    assert mat.shape[0] == mat.shape[1], "Input has to be a square matrix"

