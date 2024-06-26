import ase
import metatensor.torch
import torch
from metatensor.torch.atomistic import ModelOutput, systems_to_torch

from metatensor.models.experimental.soap_bpnn import SoapBpnn
from metatensor.models.utils.data import DatasetInfo, TargetInfo

from . import MODEL_HYPERS


def test_prediction_subset_elements():
    """Tests that the model can predict on a subset of the elements it was trained
    on."""

    dataset_info = DatasetInfo(
        length_unit="Angstrom",
        atomic_types={1, 6, 7, 8},
        targets={
            "energy": TargetInfo(
                quantity="energy",
                unit="eV",
            )
        },
    )

    model = SoapBpnn(MODEL_HYPERS, dataset_info)

    system = ase.Atoms("O2", positions=[[0.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
    model(
        [systems_to_torch(system)],
        {"energy": model.outputs["energy"]},
    )


def test_prediction_subset_atoms():
    """Tests that the model can predict on a subset
    of the atoms in a system."""

    dataset_info = DatasetInfo(
        length_unit="Angstrom",
        atomic_types={1, 6, 7, 8},
        targets={
            "energy": TargetInfo(
                quantity="energy",
                unit="eV",
            )
        },
    )

    model = SoapBpnn(MODEL_HYPERS, dataset_info)

    # Since we don't yet support atomic predictions, we will test this by
    # predicting on a system with two monomers at a large distance

    system_monomer = ase.Atoms(
        "NO2", positions=[[0.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, 0.0, 2.0]]
    )

    energy_monomer = model(
        [systems_to_torch(system_monomer)],
        {"energy": ModelOutput(per_atom=False)},
    )

    system_far_away_dimer = ase.Atoms(
        "N2O4",
        positions=[
            [0.0, 0.0, 0.0],
            [0.0, 50.0, 0.0],
            [0.0, 0.0, 1.0],
            [0.0, 0.0, 2.0],
            [0.0, 51.0, 0.0],
            [0.0, 42.0, 0.0],
        ],
    )

    selection_labels = metatensor.torch.Labels(
        names=["system", "atom"],
        values=torch.tensor([[0, 0], [0, 2], [0, 3]]),
    )

    energy_dimer = model(
        [systems_to_torch(system_far_away_dimer)],
        {"energy": ModelOutput(per_atom=False)},
    )

    energy_monomer_in_dimer = model(
        [systems_to_torch(system_far_away_dimer)],
        {"energy": ModelOutput(per_atom=False)},
        selected_atoms=selection_labels,
    )

    assert not metatensor.torch.allclose(
        energy_monomer["energy"], energy_dimer["energy"]
    )

    assert metatensor.torch.allclose(
        energy_monomer["energy"], energy_monomer_in_dimer["energy"]
    )


def test_output_last_layer_features():
    """Tests that the model can output its last layer features."""
    dataset_info = DatasetInfo(
        length_unit="Angstrom",
        atomic_types={1, 6, 7, 8},
        targets={
            "energy": TargetInfo(
                quantity="energy",
                unit="eV",
            )
        },
    )

    model = SoapBpnn(MODEL_HYPERS, dataset_info)

    system = ase.Atoms(
        "CHON",
        positions=[[0.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, 0.0, 2.0], [0.0, 0.0, 3.0]],
    )

    # last-layer features per atom:
    ll_output_options = ModelOutput(
        quantity="",
        unit="",
        per_atom=True,
    )
    outputs = model(
        [systems_to_torch(system, dtype=torch.get_default_dtype())],
        {
            "energy": model.outputs["energy"],
            "mtm::aux::last_layer_features": ll_output_options,
        },
    )
    assert "energy" in outputs
    assert "mtm::aux::last_layer_features" in outputs
    last_layer_features = outputs["mtm::aux::last_layer_features"].block()
    assert last_layer_features.samples.names == [
        "system",
        "atom",
    ]
    assert last_layer_features.values.shape == (
        4,
        128,
    )
    assert last_layer_features.properties.names == [
        "properties",
    ]

    # last-layer features per system:
    ll_output_options = ModelOutput(
        quantity="",
        unit="",
        per_atom=False,
    )
    outputs = model(
        [systems_to_torch(system, dtype=torch.get_default_dtype())],
        {
            "energy": model.outputs["energy"],
            "mtm::aux::last_layer_features": ll_output_options,
        },
    )
    assert "energy" in outputs
    assert "mtm::aux::last_layer_features" in outputs
    assert outputs["mtm::aux::last_layer_features"].block().samples.names == ["system"]
    assert outputs["mtm::aux::last_layer_features"].block().values.shape == (
        1,
        128,
    )
    assert outputs["mtm::aux::last_layer_features"].block().properties.names == [
        "properties",
    ]


def test_output_per_atom():
    """Tests that the model can output per-atom quantities."""
    dataset_info = DatasetInfo(
        length_unit="Angstrom",
        atomic_types={1, 6, 7, 8},
        targets={
            "energy": TargetInfo(
                quantity="energy",
                unit="eV",
            )
        },
    )

    model = SoapBpnn(MODEL_HYPERS, dataset_info)

    system = ase.Atoms(
        "CHON",
        positions=[[0.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, 0.0, 2.0], [0.0, 0.0, 3.0]],
    )

    outputs = model(
        [systems_to_torch(system, dtype=torch.get_default_dtype())],
        {"energy": model.outputs["energy"]},
    )

    assert outputs["energy"].block().samples.names == ["system", "atom"]
    assert outputs["energy"].block().values.shape == (4, 1)
