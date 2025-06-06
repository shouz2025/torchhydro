"""
Author: Wenyu Ouyang
Date: 2024-04-08 18:17:44
LastEditTime: 2024-11-05 09:21:24
LastEditors: Wenyu Ouyang
Description: normalize the data
FilePath: \torchhydro\torchhydro\datasets\data_scalers.py
Copyright (c) 2024-2024 Wenyu Ouyang. All rights reserved.
"""

import os
import pickle as pkl
import shutil
from typing import Optional
import pint_xarray  # noqa: F401
import xarray as xr
import numpy as np
from sklearn.preprocessing import (
    StandardScaler,
    RobustScaler,
    MinMaxScaler,
    MaxAbsScaler,
)

from torchhydro.datasets.data_utils import (
    wrap_t_s_dict,
)
from torchhydro.datasets.scalers import (
    DapengScaler,
    SlidingWindowScaler,
)

SCALER_DICT = {
    "StandardScaler": StandardScaler,
    "RobustScaler": RobustScaler,
    "MinMaxScaler": MinMaxScaler,
    "MaxAbsScaler": MaxAbsScaler,
}
TORCHHYDRO_SCALER_DICT = {
    "DapengScaler": DapengScaler,
    "SlidingWindowScaler": SlidingWindowScaler,
}

class ScalerHub(object):
    """
    A class for Scaler
    """

    def __init__(
        self,
        target_vars: np.ndarray,
        relevant_vars: np.ndarray,
        constant_vars: Optional[np.ndarray] = None,
        other_vars: Optional[dict] = None,
        data_cfgs: Optional[dict] = None,
        is_tra_val_te: Optional[str] = None,
        data_source: object = None,
        **kwargs,
    ):
        """
        Perform normalization

        Parameters
        ----------
        target_vars
            output variables
        relevant_vars
            dynamic input variables
        constant_vars
            static input variables
        other_vars
            other required variables
        data_cfgs
            configs for reading data
        is_tra_val_te
            train, valid or test
        kwargs
            other optional parameters for ScalerHub
        """
        self.data_cfgs = data_cfgs
        norm_keys = ["target_vars", "relevant_vars", "constant_vars", "other_vars"]  # y, x, c
        scaler_type = data_cfgs["scaler"]
        if scaler_type in TORCHHYDRO_SCALER_DICT.keys():
            scaler = TorchhydroScalers(
                scaler_type=scaler_type,
                target_vars=target_vars,
                relevant_vars=relevant_vars,
                constant_vars=constant_vars,
                data_cfgs=data_cfgs,
                is_tra_val_te=is_tra_val_te,
                other_vars=other_vars,
                data_source=data_source,
            )
            x, y, c, d = scaler.normalize()
            self.target_scaler = scaler
        elif scaler_type in SCALER_DICT.keys():
            scaler = SklearnScalers(
                scaler_type=scaler_type,
                target_vars=target_vars,
                relevant_vars=relevant_vars,
                constant_vars=constant_vars,
                data_cfgs=data_cfgs,
                is_tra_val_te=is_tra_val_te,
                norm_keys=norm_keys,
                other_vars=other_vars,
                data_source=data_source,
            )
            x, y, c, d = scaler.normalize()
            self.target_scaler = scaler
        else:
            raise NotImplementedError(
                "We don't provide this Scaler now!!! Please choose another one: DapengScaler or key in SCALER_DICT"
            )
        print("Finish Normalization\n")
        self.x = x
        self.y = y
        self.c = c
        self.d = d


class SklearnScalers(object):
    """
    a scaler set in sklearn
    The normalization and denormalization methods from Sklearn package.
    """
    def __init__(
        self,
        scaler_type: str,
        target_vars: np.ndarray,
        relevant_vars: np.ndarray,
        constant_vars: np.ndarray,
        data_cfgs: dict,
        is_tra_val_te: str,
        norm_keys: list,
        other_vars: Optional[dict] = None,
        data_source: object = None,
    ):
        """
        initialize a SklearnScalers object.

        Parameters
        ----------
        scaler_type
            scaler type in Sklearn package
        target_vars
            output variables
        relevant_vars
            input dynamic variables
        constant_vars
            input static variables
        data_cfgs
            data parameter config in data source
        is_tra_val_te
            train/valid/test
        other_vars
            if more input are needed, list them in other_vars
        data_source
            data source
        """
        self.scaler = SCALER_DICT[scaler_type]()
        self.data_target = target_vars
        self.data_forcing = relevant_vars
        self.data_attr = constant_vars
        self.data_cfgs = data_cfgs
        self.t_s_dict = wrap_t_s_dict(data_cfgs, is_tra_val_te)
        self.is_tra_val_te = is_tra_val_te
        self.norm_keys = norm_keys
        self.data_other = other_vars
        self.data_source = data_source
        self.pbm_norm = None

    def normalize(self):
        """ """
        all_vars = [self.data_target, self.data_forcing, self.data_attr, self.data_other]  # y, x, c
        norm_dict = {}
        for i in range(len(all_vars)):
            data_tmp = all_vars[i]   # normalize along xr.DataSet
            scaler = self.scaler
            if data_tmp is None:
                data_norm = None
            elif data_tmp.ndim == 3:
                # for forcings, outputs and other data(trend, season and residuals decomposed from streamflow)
                num_instances, num_time_steps, num_features = data_tmp.transpose(
                    "basin", "time", "variable"
                ).shape
                data_tmp = data_tmp.to_numpy().reshape(-1, num_features)
                save_file = os.path.join(
                    self.data_cfgs["test_path"], f"{self.norm_keys[i]}_scaler.pkl"
                )
                if self.is_tra_val_te == "train" and self.data_cfgs["stat_dict_file"] is None:  # help="for testing sometimes such as pub cases, we need stat_dict_file from trained dataset"  Predictions in Ungauged Basins (PUB)
                    data_norm = scaler.fit_transform(data_tmp)
                    # Save scaler in test_path for valid/test
                    with open(save_file, "wb") as outfile:
                        pkl.dump(scaler, outfile)
                else:
                    if self.data_cfgs["stat_dict_file"] is not None:
                        shutil.copy(self.data_cfgs["stat_dict_file"], save_file)
                    if not os.path.isfile(save_file):
                        raise FileNotFoundError(
                            "Please genereate xx_scaler.pkl file"
                        )
                    with open(save_file, "rb") as infile:
                        scaler = pkl.load(infile)
                        data_norm = scaler.transform(data_tmp)
                data_norm = data_norm.reshape(
                    num_instances, num_time_steps, num_features
                )
            else:
                # for attributes
                save_file = os.path.join(
                    self.data_cfgs["test_path"], f"{self.norm_keys[i]}_scaler.pkl"
                )
                if self.is_tra_val_te == "train" and self.data_cfgs["stat_dict_file"] is None:
                    data_norm = scaler.fit_transform(data_tmp)
                    data_norm = np.transpose(data_norm)
                    # Save scaler in test_path for valid/test
                    with open(save_file, "wb") as outfile:
                        pkl.dump(scaler, outfile)
                else:
                    if self.data_cfgs["stat_dict_file"] is not None:
                        shutil.copy(self.data_cfgs["stat_dict_file"], save_file)
                    assert os.path.isfile(save_file)
                    with open(save_file, "rb") as infile:
                        scaler = pkl.load(infile)
                        data_norm = scaler.transform(data_tmp)   # normalize
                        data_norm = np.transpose(data_norm)
            norm_dict[self.norm_keys[i]] = data_norm
        x_ = norm_dict["relevant_vars"]  # forcing
        y_ = norm_dict["target_vars"]  # streamflow
        c_ = norm_dict["constant_vars"]  # attr
        d_ = norm_dict["other_vars"]  # trend, season, residuals

        x = xr.DataArray(
            x_,
            coords={
                "basin": self.data_forcing.coords["basin"],
                "time": self.data_forcing.coords["time"],
                "variable": self.data_cfgs["relevant_cols"]
            },
            dims=["basin", "time", "variable"],
        )
        y = xr.DataArray(
            y_,
            coords={
                "basin": self.data_target.coords["basin"],
                "time": self.data_target.coords["time"],
                "variable": self.data_target.coords["variable"],
            },
            dims=["basin", "time", "variable"],
        )
        if c_ is None:
            c = None
        else:
            c = xr.DataArray(
                c_,
                coords={
                    "basin": self.data_attr.coords["basin"],
                    "variable": self.data_attr.coords["variable"],
                },
                dims=["basin", "variable"],
            )
        if d_ is None:
            d = None
        else:
            d = xr.DataArray(
                d_,
                coords={
                    "basin": self.data_other.coords["basin"],
                    "time": self.data_other.coords["time"],
                    "variable": self.data_other.coords["variable"],
                },
                dims=["basin", "time", "variable"],
            )

        return x, y, c, d

    def inverse_transform(self, x):
        """
        Denormalization for output variables
        Parameters
        ----------
        x
            data to be denormalized

        Returns
        -------
        np.array
        denormalized data
        """
        if self.data_cfgs["b_decompose"]:   # todo:
            target_cols = self.data_cfgs["decomposed_item"]
            attrs = self.data_other.attrs
        else:
            target_cols = self.data_cfgs["target_cols"]
            attrs = self.data_target.attrs
        out = xr.full_like(x, np.nan)
        for i in range(len(target_cols)):
            item = target_cols[i]
            x_item = x.sel(variable=item)
            x_item = self.scaler.fit_transform(x_item)
            out.loc[dict(variable=item)] = self.scaler.inverse_transform(x_item)

        # add attrs for units
        out.attrs.update(attrs)
        return out.to_dataset(dim="variable")


class TorchhydroScalers(object):
    """
    a scaler set in torchhydro, only DapengScaler now.
    The normalization and denormalization methods in torchhydro.
    """
    def __init__(
        self,
        scaler_type: str,
        target_vars: np.ndarray,
        relevant_vars: np.ndarray,
        constant_vars: np.ndarray,
        data_cfgs: dict,
        is_tra_val_te: str,
        other_vars: Optional[dict] = None,
        data_source: object = None,
    ):
        """
        initialize a TorchhydroScalers object.

        Parameters
        ----------
        scaler_type
            scaler type in Sklearn package
        target_vars
            output variables
        relevant_vars
            input dynamic variables
        constant_vars
            input static variables
        data_cfgs
            data parameter config in data source
        is_tra_val_te
            train/valid/test
        other_vars
            if more input are needed, list them in other_vars
        data_source
             data source
        """
        # self.scaler = None  #
        self.data_target = target_vars
        self.data_forcing = relevant_vars
        self.data_attr = constant_vars
        self.data_cfgs = data_cfgs
        self.t_s_dict = wrap_t_s_dict(data_cfgs, is_tra_val_te)
        self.is_tra_val_te = is_tra_val_te
        self.data_other = other_vars
        self.data_source = data_source
        self.scaler = TORCHHYDRO_SCALER_DICT[scaler_type](
            self.data_target,
            self.data_forcing,
            self.data_attr,
            self.data_cfgs,
            self.is_tra_val_te,
            self.data_other,
            data_source=self.data_source,
        )
        self.pbm_norm = self.scaler.pbm_norm

    def normalize(self):
        """ """
        x, y, c, d = self.scaler.transform()
        return x, y, c, d

    def inverse_transform(self, x):
        """
        Denormalization for output variables
        Parameters
        ----------
        x
            data to be denormalized

        Returns
        -------
        np.array
        denormalized data
        """
        out = self.scaler.inverse_transform(x)
        return out
