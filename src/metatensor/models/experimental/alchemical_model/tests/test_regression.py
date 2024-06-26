import random

import ase.io
import numpy as np
import torch
from metatensor.torch.atomistic import ModelEvaluationOptions, systems_to_torch
from omegaconf import OmegaConf

from metatensor.models.experimental.alchemical_model import AlchemicalModel, Trainer
from metatensor.models.utils.data import Dataset, DatasetInfo, TargetInfo
from metatensor.models.utils.data.readers import read_systems, read_targets
from metatensor.models.utils.neighbor_lists import get_system_with_neighbor_lists

from . import DATASET_PATH, DEFAULT_HYPERS, MODEL_HYPERS


# reproducibility
random.seed(0)
np.random.seed(0)
torch.manual_seed(0)


def test_regression_init():
    """Perform a regression test on the model at initialization"""

    dataset_info = DatasetInfo(
        length_unit="Angstrom",
        atomic_types={1, 6, 7, 8},
        targets={
            "mtm::U0": TargetInfo(
                quantity="energy",
                unit="eV",
            )
        },
    )
    model = AlchemicalModel(MODEL_HYPERS, dataset_info)

    # Predict on the first five systems
    systems = ase.io.read(DATASET_PATH, ":5")
    systems = [systems_to_torch(system) for system in systems]
    systems = [
        get_system_with_neighbor_lists(system, model.requested_neighbor_lists())
        for system in systems
    ]

    evaluation_options = ModelEvaluationOptions(
        length_unit=model.dataset_info.length_unit,
        outputs=model.outputs,
    )

    exported = model.export()

    output = exported(systems, evaluation_options, check_consistency=True)

    expected_output = torch.tensor(
        [
            [-11.203639984131],
            [4.095238208771],
            [-4.632149219513],
            [-13.758152008057],
            [-2.430717945099],
        ]
    )

    # if you need to change the hardcoded values:
    # torch.set_printoptions(precision=12)
    # print(output["mtm::U0"].block().values)

    torch.testing.assert_close(
        output["mtm::U0"].block().values,
        expected_output,
    )


def test_regression_train():
    """Perform a regression test on the model when
    trained for 2 epoch on a small dataset"""

    systems = read_systems(DATASET_PATH)

    conf = {
        "mtm::U0": {
            "quantity": "energy",
            "read_from": DATASET_PATH,
            "file_format": ".xyz",
            "key": "U0",
            "unit": "eV",
            "forces": False,
            "stress": False,
            "virial": False,
        }
    }
    targets, target_info_dict = read_targets(OmegaConf.create(conf))
    dataset = Dataset({"system": systems, "mtm::U0": targets["mtm::U0"]})

    hypers = DEFAULT_HYPERS.copy()

    dataset_info = DatasetInfo(
        length_unit="Angstrom", atomic_types={1, 6, 7, 8}, targets=target_info_dict
    )
    model = AlchemicalModel(MODEL_HYPERS, dataset_info)

    systems = [
        get_system_with_neighbor_lists(system, model.requested_neighbor_lists())
        for system in systems
    ]

    hypers["training"]["num_epochs"] = 1
    trainer = Trainer(hypers["training"])
    trainer.train(model, [torch.device("cpu")], [dataset], [dataset], ".")

    # Predict on the first five systems
    evaluation_options = ModelEvaluationOptions(
        length_unit=dataset_info.length_unit,
        outputs=model.outputs,
    )

    exported = model.export()

    output = exported(systems[:5], evaluation_options, check_consistency=True)

    expected_output = torch.tensor(
        [
            [-40.133975982666],
            [-56.344772338867],
            [-76.740966796875],
            [-77.038444519043],
            [-92.812789916992],
        ]
    )

    # if you need to change the hardcoded values:
    # torch.set_printoptions(precision=12)
    # print(output["mtm::U0"].block().values)

    torch.testing.assert_close(
        output["mtm::U0"].block().values,
        expected_output,
    )
