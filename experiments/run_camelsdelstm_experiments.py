"""
Author: Wenyu Ouyang
Date: 2022-09-09 14:47:42
LastEditTime: 2024-11-11 18:33:10
LastEditors: Wenyu Ouyang
Description: a script to run experiments for LSTM - CAMELS
FilePath: \torchhydro\experiments\run_camelslstm_experiments.py
Copyright (c) 2023-2024 Wenyu Ouyang. All rights reserved.
"""

import os

from torchhydro import SETTING
from torchhydro.configs.config import cmd, default_config_file, update_cfg
from torchhydro.trainers.trainer import train_and_evaluate

VAR_C_CHOSEN_FROM_CAMELS_DE = [
    "elev_mean",
    "slope_fdc",
    "area",
    "forests_and_seminatural_areas_perc",
    "artificial_surfaces_perc",
    "agricultural_areas_perc",
    "wetlands_perc",
    "water_bodies_perc",
    "clay_30_100cm_mean",
    "soil_organic_carbon_30_100cm_mean",
    "silt_0_30cm_mean",
    "sand_0_30cm_mean",
    "bulk_density_0_30cm_mean",
    "geochemical_rocktype_silicate_perc",
    "geochemical_rocktype_carbonatic_perc",
    "cavity_pores_perc",
    "geochemical_rocktype_silicate_perc",
]
VAR_T_CHOSEN_FROM_DE = [
    "precipitation_mean",
    "precipitation_min",
    "precipitation_median",
    "precipitation_max",
    "precipitation_stdev",
    "water_level",
    "humidity_mean",
    "humidity_min",
    "humidity_median",
    "humidity_max",
    "humidity_stdev",
    "radiation_global_mean",
    "radiation_global_min",
    "radiation_global_median",
    "radiation_global_max",
    "radiation_global_stdev",
    "temperature_mean",
    "temperature_min",
    "temperature_max",
]


def run_normal_dl(
    project_name,
    gage_id_file,
    var_c=VAR_C_CHOSEN_FROM_CAMELS_DE,
    var_t=VAR_T_CHOSEN_FROM_DE,
    train_period=None,
    valid_period=None,
    test_period=None,
):
    if train_period is None:  # camels-de time_range: ["1951-01-01", "2020-12-31"]
        train_period = ["2017-10-01", "2018-10-01"]
    if valid_period is None:
        valid_period = ["2018-10-01", "2019-10-01"]
    if test_period is None:
        test_period = ["2019-10-01", "2020-10-01"]
    config_data = default_config_file()
    args = cmd(
        sub=project_name,
        source_cfgs={
            "source_name": "camels_de",
            "source_path": os.path.join(
                SETTING["local_data_path"]["datasets-origin"], "camels", "camels_de"
            ),
        },
        ctx=[-1],
        # model_name="KuaiLSTM",
        model_name="CpuLSTM",
        model_hyperparam={
            "n_input_features": len(var_c) + len(var_t),  # 17 + 19 = 36
            "n_output_features": 1,
            "n_hidden_states": 256,
        },
        loss_func="RMSESum",
        sampler="KuaiSampler",
        dataset="StreamflowDataset",
        scaler="DapengScaler",
        batch_si0ze=50,
        forecast_history=0,
        forecast_length=366,
        var_t=var_t,
        var_c=var_c,
        var_out=["streamflow"],
        train_period=train_period,
        valid_period=valid_period,
        test_period=test_period,
        opt="Adadelta",
        rs=1234,
        train_epoch=1,
        save_epoch=1,
        model_loader={
            "load_way": "specified",
            "test_epoch": 1,
        },
        gage_id_file=gage_id_file,
        which_first_tensor="sequence",
    )
    update_cfg(config_data, args)
    train_and_evaluate(config_data)
    print("All processes are finished!")


# the gage_id.txt file is set by the user, it must be the format like:
# GAUGE_ID
# 01013500
# 01022500
# ......
# Then it can be read by pd.read_csv(gage_id_file, dtype={0: str}).iloc[:, 0].values to get the gage_id list
run_normal_dl(os.path.join("test_camels", "lstm_camelsde"), "D:\\minio\\waterism\\datasets-origin\\camels\\camels_de\\gage_id.txt")
