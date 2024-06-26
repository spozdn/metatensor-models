from pathlib import Path

import pytest
import torch
from metatensor.torch import Labels, TensorBlock, TensorMap

from metatensor.models.utils.loss import TensorMapDictLoss, TensorMapLoss


RESOURCES_PATH = Path(__file__).parents[1] / "resources"


@pytest.fixture
def tensor_map_with_grad_1():
    block = TensorBlock(
        values=torch.tensor([[1.0], [2.0], [3.0]]),
        samples=Labels.range("samples", 3),
        components=[],
        properties=Labels("energy", torch.tensor([[0]])),
    )
    block.add_gradient(
        "gradient",
        TensorBlock(
            values=torch.tensor([[1.0], [2.0], [3.0]]),
            samples=Labels.range("sample", 3),
            components=[],
            properties=Labels("energy", torch.tensor([[0]])),
        ),
    )
    tensor_map = TensorMap(keys=Labels.single(), blocks=[block])
    return tensor_map


@pytest.fixture
def tensor_map_with_grad_2():
    block = TensorBlock(
        values=torch.tensor([[1.0], [1.0], [3.0]]),
        samples=Labels.range("samples", 3),
        components=[],
        properties=Labels("energy", torch.tensor([[0]])),
    )
    block.add_gradient(
        "gradient",
        TensorBlock(
            values=torch.tensor([[1.0], [0.0], [3.0]]),
            samples=Labels.range("sample", 3),
            components=[],
            properties=Labels("energy", torch.tensor([[0]])),
        ),
    )
    tensor_map = TensorMap(keys=Labels.single(), blocks=[block])
    return tensor_map


@pytest.fixture
def tensor_map_with_grad_3():
    block = TensorBlock(
        values=torch.tensor([[0.0], [1.0], [3.0]]),
        samples=Labels.range("samples", 3),
        components=[],
        properties=Labels("energy", torch.tensor([[0]])),
    )
    block.add_gradient(
        "gradient",
        TensorBlock(
            values=torch.tensor([[1.0], [0.0], [3.0]]),
            samples=Labels.range("sample", 3),
            components=[],
            properties=Labels("energy", torch.tensor([[0]])),
        ),
    )
    tensor_map = TensorMap(keys=Labels.single(), blocks=[block])
    return tensor_map


@pytest.fixture
def tensor_map_with_grad_4():
    block = TensorBlock(
        values=torch.tensor([[0.0], [1.0], [3.0]]),
        samples=Labels.range("samples", 3),
        components=[],
        properties=Labels("energy", torch.tensor([[0]])),
    )
    block.add_gradient(
        "gradient",
        TensorBlock(
            values=torch.tensor([[1.0], [0.0], [2.0]]),
            samples=Labels.range("sample", 3),
            components=[],
            properties=Labels("energy", torch.tensor([[0]])),
        ),
    )
    tensor_map = TensorMap(keys=Labels.single(), blocks=[block])
    return tensor_map


def test_tmap_loss_no_gradients():
    """Test that the loss is computed correctly when there are no gradients."""
    loss = TensorMapLoss()

    tensor_map_1 = TensorMap(
        keys=Labels.single(),
        blocks=[
            TensorBlock(
                values=torch.tensor([[1.0], [2.0], [3.0]]),
                samples=Labels.range("samples", 3),
                components=[],
                properties=Labels("energy", torch.tensor([[0]])),
            )
        ],
    )
    tensor_map_2 = TensorMap(
        keys=Labels.single(),
        blocks=[
            TensorBlock(
                values=torch.tensor([[0.0], [2.0], [3.0]]),
                samples=Labels.range("samples", 3),
                components=[],
                properties=Labels("energy", torch.tensor([[0]])),
            )
        ],
    )

    loss_value = loss(tensor_map_1, tensor_map_1)
    torch.testing.assert_close(loss_value, torch.tensor(0.0))

    # Expected result: 1.0
    loss_value = loss(tensor_map_1, tensor_map_2)
    torch.testing.assert_close(loss_value, torch.tensor(1.0))


def test_tmap_loss_with_gradients(tensor_map_with_grad_1, tensor_map_with_grad_2):
    """Test that the loss is computed correctly when there are gradients."""
    loss = TensorMapLoss(gradient_weights={"gradient": 0.5})

    loss_value = loss(tensor_map_with_grad_1, tensor_map_with_grad_1)
    torch.testing.assert_close(loss_value, torch.tensor(0.0))

    # Expected result: 1.0 + 0.5 * 4.0
    loss_value = loss(tensor_map_with_grad_1, tensor_map_with_grad_2)
    torch.testing.assert_close(
        loss_value,
        torch.tensor(1.0 + 0.5 * 4.0),
    )


def test_tmap_dict_loss(
    tensor_map_with_grad_1,
    tensor_map_with_grad_2,
    tensor_map_with_grad_3,
    tensor_map_with_grad_4,
):
    """Test that the dict loss is computed correctly."""

    loss = TensorMapDictLoss(
        weights={
            "output_1": 0.6,
            "output_2": 1.0,
            "output_1_gradient_gradients": 0.5,
            "output_2_gradient_gradients": 0.5,
        }
    )

    output_dict = {
        "output_1": tensor_map_with_grad_1,
        "output_2": tensor_map_with_grad_2,
    }

    target_dict = {
        "output_1": tensor_map_with_grad_3,
        "output_2": tensor_map_with_grad_4,
    }

    expected_result = (
        0.6
        * (
            tensor_map_with_grad_1.block().values
            - tensor_map_with_grad_3.block().values
        )
        .pow(2)
        .sum()
        + 0.5
        * (
            tensor_map_with_grad_1.block().gradient("gradient").values
            - tensor_map_with_grad_3.block().gradient("gradient").values
        )
        .pow(2)
        .sum()
        + 1.0
        * (
            tensor_map_with_grad_2.block().values
            - tensor_map_with_grad_4.block().values
        )
        .pow(2)
        .sum()
        + 0.5
        * (
            tensor_map_with_grad_2.block().gradient("gradient").values
            - tensor_map_with_grad_4.block().gradient("gradient").values
        )
        .pow(2)
        .sum()
    )

    loss_value = loss(output_dict, target_dict)
    torch.testing.assert_close(loss_value, expected_result)


def test_tmap_dict_loss_subset(tensor_map_with_grad_1, tensor_map_with_grad_3):
    """Test that the dict loss is computed correctly when only a subset
    of the possible targets is present both in outputs and targets."""

    loss = TensorMapDictLoss(
        weights={
            "output_1": 1.0,
            "output_2": 1.0,
            "output_1_gradient_gradients": 0.5,
            "output_2_gradient_gradients": 0.5,
        }
    )

    output_dict = {
        "output_1": tensor_map_with_grad_1,
    }

    target_dict = {
        "output_1": tensor_map_with_grad_3,
    }

    expected_result = (
        1.0
        * (
            tensor_map_with_grad_1.block().values
            - tensor_map_with_grad_3.block().values
        )
        .pow(2)
        .sum()
        + 0.5
        * (
            tensor_map_with_grad_1.block().gradient("gradient").values
            - tensor_map_with_grad_3.block().gradient("gradient").values
        )
        .pow(2)
        .sum()
    )

    loss_value = loss(output_dict, target_dict)
    torch.testing.assert_close(loss_value, expected_result)
