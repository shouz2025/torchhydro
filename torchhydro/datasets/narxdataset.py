"""narx model dataset"""

import sys
import numpy as np
import torch
from tqdm import tqdm

from torchhydro.datasets.data_sets import BaseDataset
from torchhydro.datasets.data_utils import (
    wrap_t_s_dict,
)
from torchhydro.models.basintree import BasinTree
from torchhydro.datasets.data_scalers import ScalerHub

class NarxDataset(BaseDataset):
    """
    a dataset for Narx model.
    """
    def __init__(self, data_cfgs: dict, is_tra_val_te: str):
        """
        Initialize the Narx dataset.  for fr in camels.
        narx model is more suitable for nested catchment flood prediction,
        while only fr have the nestedness information in camels, so choose fr to make dataset.
        Parameters
        ----------
        data_cfgs: data configures, setting via console.
        is_tra_val_te: three mode, train, validate and test.
        """
        super(NarxDataset, self).__init__(data_cfgs, is_tra_val_te)
        self.data_cfgs = data_cfgs
        if is_tra_val_te in {"train", "valid", "test"}:
            self.is_tra_val_te = is_tra_val_te
        else:
            raise ValueError(
                "'is_tra_val_te' must be one of 'train', 'valid' or 'test' "
            )
        self.b_nestedness = self.data_cfgs["b_nestedness"]
        # load and preprocess data
        self._load_data()

    def __getitem__(self, item: int):
        """
        DataLoader load data from here and deliver into model.
        deal with data order
        how to implement changeable batch size
        fetch and deliver into model
        Parameters
        ----------
        item: batch/basins

        Returns
        -------

        """
        if not self.train_mode:  # not train mode
            x = self.x[item, :, :]  # forcing data   [batch(basin), sequence, features]
            y = self.y[item, :, :]  # var_out, streamflow
            if self.c is None or self.c.shape[-1] == 0:  # attributions
                return torch.from_numpy(x).float(), torch.from_numpy(y).float()
            c = self.c[item, :]
            c = np.repeat(c, x.shape[0], axis=0).reshape(c.shape[0], -1).T
            xc = np.concatenate((x, c), axis=1)
            return torch.from_numpy(xc).float(), torch.from_numpy(y).float()
        basin, idx = self.lookup_table[item]  # 
        warmup_length = self.warmup_length  #
        x = self.x[basin, idx - warmup_length: idx + self.rho + self.horizon, :]
        y = self.y[basin, idx: idx + self.rho + self.horizon, :]
        if self.c is None or self.c.shape[-1] == 0:
            return torch.from_numpy(x).float(), torch.from_numpy(y).float()
        c = self.c[basin, :]
        c = np.repeat(c, x.shape[0], axis=0).reshape(c.shape[0], -1).T  # repeat the attributes for each tim-step.
        xc = np.concatenate((x, c), axis=1)  # incorporate, as the input of model.
        return torch.from_numpy(xc).float(), torch.from_numpy(y).float()  # deliver into model prcp, pet, attributes and streamflow etc.

    def __len__(self):
        """
            expected to return the size of the dataset by many:class:`torch.utils.data.Sampler` implementations and 
            the default options of :class:`torch.utils.data.DataLoader`.
        """
        return self.num_samples if self.train_mode else self.ngrid  # ngrid means nbasin

    def _pre_load_data(self):
        """preload data.
        some arguments setting.
        """
        self.train_mode = self.is_tra_val_te == "train"
        self.t_s_dict = wrap_t_s_dict(self.data_cfgs, self.is_tra_val_te)
        self.rho = self.data_cfgs["forecast_history"]  # the length of the history data for forecasting, the rho in LSTM.
        self.warmup_length = self.data_cfgs["warmup_length"]  # For physics-based models, we need warmup; default is 0 as DL models generally don't need it
        self.horizon = self.data_cfgs["forecast_length"]
        self.b_nestedness = self.data_cfgs["b_nestedness"]

    def _load_data(self):
        """load data to make dataset.
        
        """
        self._pre_load_data()
        self._read_xyc()
        # normalization
        norm_x, norm_y, norm_c = self._normalize()
        self.x, self.y, self.c = self._kill_nan(norm_x, norm_y, norm_c)  # deal with nan value
        self._trans2nparr()
        self._create_lookup_table()  #

    def _trans2nparr(self):
        """To make __getitem__ more efficient,
        we transform x, y, c to numpy array with shape (nsample, nt, nvar).    means [batch(basin), time, features]
        """
        self.x = self.x.transpose("basin", "time", "variable").to_numpy()  # tanspose, 变换顺序, 转置。 may means T.  batch first here
        self.y = self.y.transpose("basin", "time", "variable").to_numpy()
        if self.c is not None and self.c.shape[-1] > 0:
            self.c = self.c.transpose("basin", "variable").to_numpy()
            self.c_origin = self.c_origin.transpose("basin", "variable").to_numpy()
        self.x_origin = self.x_origin.transpose("basin", "time", "variable").to_numpy()
        self.y_origin = self.y_origin.transpose("basin", "time", "variable").to_numpy()

    def _normalize(self):
        """normalize
            target_vars, streamflow.
            relevant_vars, forcing, e.g. prcp, pet, srad, etc.
            constant_vars, attributes, e.g. area, slope, elev, etc.
        """
        scaler_hub = ScalerHub(
            self.y_origin,
            self.x_origin,
            self.c_origin,
            data_cfgs=self.data_cfgs,
            is_tra_val_te=self.is_tra_val_te,
            data_source=self.data_source,
        )
        self.target_scaler = scaler_hub.target_scaler
        return scaler_hub.x, scaler_hub.y, scaler_hub.c
    
    def _read_xyc(self):
        """Read x, y, c data from data source

        Returns
        -------
        tuple[xr.Dataset, xr.Dataset, xr.Dataset]
            x, y, c data. forcing, target(streamflow), attributions.
        """
        
        start_date = self.t_s_dict["t_final_range"][0]
        end_date = self.t_s_dict["t_final_range"][1]
        self._read_xyc_specified_time(start_date, end_date)

    def _read_xyc_specified_time(self, start_date, end_date):
        """Read x, y, c data from data source with specified time range
        We set this function as sometimes we need adjust the time range for some specific dataset,
        such as seq2seq dataset (it needs one more period for the end of the time range)

        Parameters
        ----------
        start_date : str
            start time
        end_date : str
            end time
        """
        if not self.b_nestedness:
            raise ValueError("naxrdataset needs nestedness information.")
        else:
            nestedness_info = self.data_source.read_nestedness_csv()
            basin_tree_ = BasinTree(nestedness_info, self.t_s_dict["sites_id"])
            # return all related basins, cal_order and basin tree
            # make forcing dataset containing nested basin streamflow for each input gauge.
            # cal_order
            basin_tree, max_order = basin_tree_.get_basin_trees()
            basins = basin_tree   #
            basin_order = basin_tree_.set_cal_order()   # 
            # n   nestedness  streamflow  a forcing type
            # x
            data_forcing_ds_ = self.data_source.read_ts_xrdataset(
                basins,
                [start_date, end_date],
                self.data_cfgs["relevant_cols"],  # forcing data
            )
            # y
            data_nested_output_ds_ = self.data_source.read_ts_xrdataset(
                basins,
                [start_date, end_date],
                self.data_cfgs["target_cols"],  # target data, streamflow.
            )
            #
            if isinstance(data_nested_output_ds_, dict) or isinstance(data_forcing_ds_, dict):  # turn dict into list
                data_forcing_ds_ = data_forcing_ds_[list(data_forcing_ds_.keys())[0]]
                data_nested_output_ds_ = data_nested_output_ds_[list(data_nested_output_ds_.keys())[0]]
            data_forcing_ds, data_output_ds = self._check_ts_xrds_unit(
                data_forcing_ds_, data_nested_output_ds_
            )

            self.x_origin, self.y_origin, self.c_origin = self._to_dataarray_with_unit(
                data_forcing_ds, data_nested_output_ds_,
            )
            

    def _create_lookup_table(self):
        """
        
        Returns
        -------

        """
        lookup = []
        # list to collect basins ids of basins without a single training sample
        basin_coordinates = len(self.t_s_dict["sites_id"])
        rho = self.rho
        warmup_length = self.warmup_length
        horizon = self.horizon
        max_time_length = self.nt
        for basin in tqdm(range(basin_coordinates), file=sys.stdout, disable=False):
            if self.is_tra_val_te != "train":
                lookup.extend(
                    (basin, f)
                    for f in range(warmup_length, max_time_length - rho - horizon + 1)
                )
            else:
                # some dataloader load data with warmup period, so leave some periods for it
                # [warmup_len] -> time_start -> [rho] -> [horizon]
                nan_array = np.isnan(self.y[basin, :, :])
                lookup.extend(
                    (basin, f)
                    for f in range(warmup_length, max_time_length - rho - horizon + 1)
                    if not np.all(nan_array[f + rho : f + rho + horizon])
                )
        self.lookup_table = dict(enumerate(lookup))
        self.num_samples = len(self.lookup_table)
