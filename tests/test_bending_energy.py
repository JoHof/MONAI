# Copyright 2020 - 2021 MONAI Consortium
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest

import numpy as np
import torch
from parameterized import parameterized

from monai.losses.deform import BendingEnergyLoss

TEST_CASES = [
    [
        {},
        {"input": torch.ones((1, 3, 5, 5, 5))},
        0.0,
    ],
    [
        {},
        {"input": torch.arange(0, 5)[None, None, None, None, :].expand(1, 3, 5, 5, 5)},
        0.0,
    ],
    [
        {},
        {"input": torch.arange(0, 5)[None, None, None, None, :].expand(1, 3, 5, 5, 5) ** 2},
        4.0,
    ],
    [
        {},
        {"input": torch.arange(0, 5)[None, None, None, :].expand(1, 3, 5, 5) ** 2},
        4.0,
    ],
    [
        {},
        {"input": torch.arange(0, 5)[None, None, :].expand(1, 3, 5) ** 2},
        4.0,
    ],
]


class TestBendingEnergy(unittest.TestCase):
    @parameterized.expand(TEST_CASES)
    def test_shape(self, input_param, input_data, expected_val):
        result = BendingEnergyLoss(**input_param).forward(**input_data)
        np.testing.assert_allclose(result.detach().cpu().numpy(), expected_val, rtol=1e-5)

    def test_ill_shape(self):
        loss = BendingEnergyLoss()
        # not in 3-d, 4-d, 5-d
        with self.assertRaisesRegex(AssertionError, ""):
            loss.forward(torch.ones((1, 3)))
        with self.assertRaisesRegex(AssertionError, ""):
            loss.forward(torch.ones((1, 3, 5, 5, 5, 5)))
        # spatial_dim < 5
        with self.assertRaisesRegex(AssertionError, ""):
            loss.forward(torch.ones((1, 3, 4, 5, 5)))
        with self.assertRaisesRegex(AssertionError, ""):
            loss.forward(torch.ones((1, 3, 5, 4, 5)))
        with self.assertRaisesRegex(AssertionError, ""):
            loss.forward(torch.ones((1, 3, 5, 5, 4)))

    def test_ill_opts(self):
        input = torch.rand(1, 3, 5, 5, 5)
        with self.assertRaisesRegex(ValueError, ""):
            BendingEnergyLoss(reduction="unknown")(input)
        with self.assertRaisesRegex(ValueError, ""):
            BendingEnergyLoss(reduction=None)(input)


if __name__ == "__main__":
    unittest.main()
