import ase
import torch
from metatensor.torch import Labels
from metatensor.torch.atomistic import (
    MetatensorAtomisticModel,
    ModelCapabilities,
    ModelEvaluationOptions,
    ModelMetadata,
    ModelOutput,
    systems_to_torch,
)
from pet.hypers import Hypers
from pet.pet import PET

from metatensor.models.experimental.pet import PET as WrappedPET
from metatensor.models.utils.architectures import get_default_hypers
from metatensor.models.utils.data import DatasetInfo, TargetInfo
from metatensor.models.utils.neighbor_lists import get_system_with_neighbor_lists


DEFAULT_HYPERS = get_default_hypers("experimental.pet")


def test_prediction():
    """Tests that the model runs without errors."""

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
    model = WrappedPET(DEFAULT_HYPERS["model"], dataset_info)
    ARCHITECTURAL_HYPERS = Hypers(model.hypers)
    raw_pet = PET(ARCHITECTURAL_HYPERS, 0.0, len(model.atomic_types))
    model.set_trained_model(raw_pet)

    structure = ase.Atoms("O2", positions=[[0.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
    system = systems_to_torch(structure)
    system = get_system_with_neighbor_lists(system, model.requested_neighbor_lists())

    evaluation_options = ModelEvaluationOptions(
        length_unit=dataset_info.length_unit,
        outputs={"energy": ModelOutput()},
    )

    capabilities = ModelCapabilities(
        length_unit="Angstrom",
        atomic_types=model.atomic_types,
        outputs={
            "energy": ModelOutput(
                quantity="energy",
                unit="eV",
            )
        },
        interaction_range=DEFAULT_HYPERS["model"]["N_GNN_LAYERS"]
        * DEFAULT_HYPERS["model"]["R_CUT"],
        dtype="float32",
        supported_devices=["cpu", "cuda"],
    )

    model = MetatensorAtomisticModel(model.eval(), ModelMetadata(), capabilities)
    model(
        [system],
        evaluation_options,
        check_consistency=True,
    )


def test_per_atom_predictions_functionality():
    """Tests that the model can do predictions in
    per-atom mode."""

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
    model = WrappedPET(DEFAULT_HYPERS["model"], dataset_info)
    ARCHITECTURAL_HYPERS = Hypers(model.hypers)
    raw_pet = PET(ARCHITECTURAL_HYPERS, 0.0, len(model.atomic_types))
    model.set_trained_model(raw_pet)

    structure = ase.Atoms("O2", positions=[[0.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
    system = systems_to_torch(structure)
    system = get_system_with_neighbor_lists(system, model.requested_neighbor_lists())

    evaluation_options = ModelEvaluationOptions(
        length_unit=dataset_info.length_unit,
        outputs={"energy": ModelOutput()},
    )

    capabilities = ModelCapabilities(
        length_unit="Angstrom",
        atomic_types=model.atomic_types,
        outputs={
            "energy": ModelOutput(
                quantity="energy",
                unit="eV",
                per_atom=True,
            )
        },
        interaction_range=DEFAULT_HYPERS["model"]["N_GNN_LAYERS"]
        * DEFAULT_HYPERS["model"]["R_CUT"],
        dtype="float32",
        supported_devices=["cpu", "cuda"],
    )

    model = MetatensorAtomisticModel(model.eval(), ModelMetadata(), capabilities)
    model(
        [system],
        evaluation_options,
        check_consistency=True,
    )


def test_selected_atoms_functionality():
    """Tests that the model can do predictions for a selected
    subset of the atoms in the system."""

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
    model = WrappedPET(DEFAULT_HYPERS["model"], dataset_info)
    ARCHITECTURAL_HYPERS = Hypers(model.hypers)
    raw_pet = PET(ARCHITECTURAL_HYPERS, 0.0, len(model.atomic_types))
    model.set_trained_model(raw_pet)

    structure = ase.Atoms("O2", positions=[[0.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
    system = systems_to_torch(structure)
    system = get_system_with_neighbor_lists(system, model.requested_neighbor_lists())

    evaluation_options = ModelEvaluationOptions(
        length_unit=dataset_info.length_unit,
        outputs={"energy": ModelOutput()},
    )

    capabilities = ModelCapabilities(
        length_unit="Angstrom",
        atomic_types=model.atomic_types,
        outputs={
            "energy": ModelOutput(
                quantity="energy",
                unit="eV",
            )
        },
        interaction_range=DEFAULT_HYPERS["model"]["N_GNN_LAYERS"]
        * DEFAULT_HYPERS["model"]["R_CUT"],
        dtype="float32",
        supported_devices=["cpu", "cuda"],
    )

    selected_atoms = Labels(
        ["system", "atom"],
        torch.tensor([[0, a] for a in range(len(system)) if a % 2 == 0]),
    )

    evaluation_options = ModelEvaluationOptions(
        length_unit=capabilities.length_unit,
        outputs=capabilities.outputs,
        selected_atoms=selected_atoms,
    )

    model = MetatensorAtomisticModel(model.eval(), ModelMetadata(), capabilities)
    model(
        [system],
        evaluation_options,
        check_consistency=True,
    )
