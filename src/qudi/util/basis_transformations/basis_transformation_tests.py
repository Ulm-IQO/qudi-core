 # Testing framework for the math functions in QuDi
import unittest

from qudi.util.math import normalize
import numpy as np

from basis_transformation_helpers import computational_basis, random_vectors, scalar_product_along_axis
from basis_transformation import is_orthogonal_basis, compute_rotation_mat_rodriguez 

class TransformTests(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TransformTests, self).__init__(*args, **kwargs)
        # some basic objects need for testing
        self.gen_stubs() 

    def gen_stubs(self):
        "This function is to introduce some fixed attributes to the Test."
        self._example_vectors = np.array([[1.0, 1.0, 0.0],
                                          [0.0, 1.0, 1.0],
                                          [1.0, 0.0, 1.0]])
        self._random_vectors = random_vectors((3, 3))

    def test_normalization(self):
        print('Normalization Test')
        norm_example_vectors = np.apply_along_axis(normalize, 0, self._example_vectors)[0]
        res = scalar_product_along_axis(norm_example_vectors)
        self.assertTrue(np.all(np.isclose(res, 1)))

    def test_is_orthogonal_basis(self):
        print("Test `is_orthogonal_basis`")
        # first test computational orthogonal basis
        self.assertTrue(is_orthogonal_basis(computational_basis(3)))
        print("Test if `is_orthogonal_basis` correctly identifies non orthogonal basis")
        self.assertTrue(not is_orthogonal_basis(self._example_vectors))

    def test_basis_from_points(self):
        print('Basis from points test')

    def test_rodriguez_rotation(self):
        """
        Just some functionality tests of the computation of
        the 3D rotation matrix from support vectors.
        """
        # If all points are in the z-plane then the resulting transformation should not
        # change the z position of any point
        p0, p1, p2 = np.array([1, 0, 0]),  np.array([0, 1, 0]), np.array([3,2,0])
        rot_mat = compute_rotation_mat_rodriguez(p0, p1, p2)
        p_rnd = np.random.rand(3)
        z_rnd = p_rnd[2]
        p_rnd_transformed = np.matmul(rot_mat, p_rnd)
        z_rnd_transformed = p_rnd_transformed[2]
        self.assertTrue(z_rnd == z_rnd_transformed)

if __name__ == '__main__':
 #   my_test = TransformTests()
    print('in name')
    unittest.main()
