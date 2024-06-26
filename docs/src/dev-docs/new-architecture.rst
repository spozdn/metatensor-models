.. _adding-new-architecture:

Adding a new architecture
=========================

To work with` metatensor-models` any architecture has to follow the same public API to
be called correctly within the :py:func:`metatensor.models.cli.train` function to
process the user's options. In brief, the core of the ``train`` function looks similar
to these lines

.. code-block:: python

    from architecture import __model__ as Model
    from architecture import __trainer__ as Trainer

    hypers = {}
    dataset_info = DatasetInfo()

    if "continue_from":
        model = Model.load_checkpoint("path")
        model = model.restart(dataset_info)
    else:
        model = Model(hypers["architecture"], dataset_info)

    trainer = Trainer(hypers["training"])

    trainer.train(
        model=model,
        devices=[],
        train_datasets=[],
        validation_datasets=[],
        checkpoint_dir="path",
    )

    model.save_checkpoint("model.ckpt")

    mts_atomistic_model = model.export()
    mts_atomistic_model.export("model.pt", collect_extensions="extensions/")


In order to follow this, a new architectures has two define two classes

- a ``Model`` class, defining the core of the architecture. This class must implement
  the interface documented below in :py:class:`ModelInterface`
- a ``Trainer`` class, used to train an architecture and produce a model that can be
  evaluated and exported. This class must implement the interface documented below in
  :py:class:`TrainerInterface`.

The ``ModelInterface`` is the main model class and must implement a
``save_checkpoint()``, ``load_checkpoint()``  as well as a ``restart()`` and
``export()`` method.

.. code-block:: python

    class ModelInterface:

        __supported_devices__ = ["cuda", "cpu"]
        __supported_dtypes__ = [torch.float64, torch.float32]

        def __init__(self, model_hypers, dataset_info: DatasetInfo):
            self.hypers = model_hypers
            self.dataset_info = dataset_info

        def save_checkpoint(self, path: Union[str, Path]):
            pass

        @classmethod
        def load_checkpoint(cls, path: Union[str, Path]) -> "ModelInterface":
            pass

        def restart(cls, dataset_info: DatasetInfo) -> "ModelInterface":
            """Restart training.

            This function is called whenever training restarts, with the same or a
            different dataset.

            It enables transfer learning (changing the targets), and fine tuning (same
            targets, different dataset)
            """
            pass

        def export(self) -> MetatensorAtomisticModel:
            pass

Note that the ``ModelInterface`` does not necessary inherit from
:py:class:`torch.nn.Module` since training can be performed in any way.
``__supported_devices__`` and ``__supported_dtypes__`` can be defined to set the
capabilities of the model. These two lists should be sorted in order of preference since
`metatensor-models` will use these to determine, based on the user request and
machines's availability, the optimal `dtype` and `device` for training.

The ``export()`` method is required to transform a trained model into a standalone file
to be used in combination with molecular dynamic engines to run simulations. We provide
a helper function :py:func:`metatensor.models.utils.export.export` to export a torch
model to an :py:class:`MetatensorAtomisticModel
<metatensor.torch.atomistic.MetatensorAtomisticModel>`.

The ``TrainerInterface`` class should have the following signature with a required
methods for ``train()``.

.. code-block:: python

    class TrainerInterface:
        def __init__(self, train_hypers):
            self.hypers = train_hypers

        def train(
            self,
            model: ModelInterface,
            devices: List[torch.device],
            train_datasets: List[Union[Dataset, torch.utils.data.Subset]],
            validation_datasets: List[Union[Dataset, torch.utils.data.Subset]],
            checkpoint_dir: str,
        ): ...

The names of the ``ModelInterface`` and the ``TrainerInterface`` are free to choose but
should be linked to constants in the ``__init__.py`` of each architecture. On top of
these two constants the ``__init__.py`` must contain constants for the original
`__authors__` and current `__maintainers__` of the architecture.

.. code-block:: python

    from .model import CustomSOTAModel
    from .trainer import Trainer

    __model__ = CustomSOTAModel
    __trainer__ = Trainer

    __authors__ = [
        ("Jane Roe <jane.roe@myuniversity.org>", "@janeroe"),
        ("John Doe <john.doe@otheruniversity.edu>", "@johndoe"),
    ]

    __maintainers__ = [("Joe Bloggs <joe.bloggs@sotacompany.com>", "@joebloggs")]


:param __model__: Mapping of the custom ``ModelInterface`` to a general one to be loaded
    by metatensor-models
:param __trainer__: Same as ``__MODEL_CLASS__`` but the Trainer class.
:param __authors__: Tuple denoting the original authors with email address and Github
    handle of an architecture. These do not necessary be in charge of maintaining the
    the architecture
:param __maintainers__: Tuple denoting the current maintainers of the architecture. Uses
    the same style as the ``__authors__`` constant.
