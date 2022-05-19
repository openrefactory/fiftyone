"""
FiftyOne v0.15.2 revision.

| Copyright 2017-2022, Voxel51, Inc.
| `voxel51.com <https://voxel51.com/>`_
|
"""


def up(db, dataset_name):
    match_d = {"name": dataset_name}
    dataset_dict = db.datasets.find_one(match_d)

    if "groups" not in dataset_dict:
        dataset_dict["groups"] = {}

    if "default_group_names" not in dataset_dict:
        dataset_dict["default_group_names"] = {}

    db.datasets.replace_one(match_d, dataset_dict)


def down(db, dataset_name):
    match_d = {"name": dataset_name}
    dataset_dict = db.datasets.find_one(match_d)

    groups = dataset_dict.pop("groups", None)
    default_group_names = dataset_dict.pop("default_group_names", None)

    if groups or default_group_names:
        raise ValueError(
            "Cannot migrate dataset '%s' with group fields %s below v0.15.2 "
            "because groups were not supported before this release"
            % (dataset_name, list(groups.keys()))
        )

    db.datasets.replace_one(match_d, dataset_dict)