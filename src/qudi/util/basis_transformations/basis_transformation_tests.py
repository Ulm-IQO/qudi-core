 # Testing framework for the math functions in QuDi
import unittest

from qudi.util.math import normalize
import numpy as np

from basis_transformation_helpers import computational_basis, random_vectors, scalar_product_along_axis
from basis_transformation import is_orthogonal_basis 

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

if __name__ == '__main__':
 #   my_test = TransformTests()
    print('in name')
    unittest.main()
