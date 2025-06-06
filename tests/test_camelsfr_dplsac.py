"""
Author: Lili Yu
Date: 2025-03-10 18:00:00
LastEditTime: 2025-03-10 18:00:00
LastEditors: Lili Yu
Description:
"""
from torchhydro.configs.config import cmd, default_config_file, update_cfg
from torchhydro import SETTING
from torchhydro.trainers.trainer import train_and_evaluate
import pytest

@pytest.fixture
def var_c():
    return [
        "top_altitude_mean",
        "top_slo_mean",
        "sta_area_snap",
        "top_drainage_density",
        "clc_2018_lvl1_1",
        "clc_2018_lvl2_11",
        "clc_2018_lvl3_111",
        "clc_1990_lvl1_1",
        "clc_2018_lvl1_2",
        "top_slo_ori_n",
        "top_slo_ori_ne",
        "top_slo_ori_e",
        "top_slo_flat",
        "top_slo_gentle",
        "top_slo_moderate",
        "top_slo_ori_se",
        "geo_py",
        "geo_pa",
    ]

@pytest.fixture
def var_t():
    return [
        "tsd_prec",
        "tsd_pet_ou",
        "tsd_prec_solid_frac",
        "tsd_temp",
        "tsd_pet_pe",
        "tsd_pet_pm",
        "tsd_wind",
        "tsd_humid",
        "tsd_rad_dli",
        "tsd_rad_ssi",
        "tsd_swi_gr",
        "tsd_swi_isba",
        "tsd_swe_isba",
        "tsd_temp_min",
        "tsd_temp_max",
    ]

@pytest.fixture
def camelsfrdplsac_arg(var_c, var_t):
    """
    Use attr and forcing as input for dPL model

    Parameters
    ----------
    config

    Returns
    -------

    """
    # camels-fr time_range: ["1970-01-01", "2022-01-01"]
    train_period = ["2012-10-01", "2013-10-01"]
    valid_period = ["2013-10-01", "2014-10-01"]
    test_period = ["2014-10-01", "2015-10-01"]
    config = default_config_file()
    args = cmd(
        sub=os.path.join("test_camels", "dpllstmsac_camelsfr"),
        # sub=os.path.join("test_camels", "dplannsac_camelsfr"),
        source_cfgs={
            "source_name": "camels_fr",
            "source_path": os.path.join(
                SETTING["local_data_path"]["datasets-origin"], "camels", "camels_fr"
            ),
        },
        ctx=[-1],
        model_name="DplLstmSac",
        # model_name="DplAnnSac",
        model_hyperparam={
            "n_input_features": len(var_c)+len(var_t),
            "n_output_features": 21,
            "n_hidden_states": 256,
            "warmup_length": 10,
        },
        loss_func="RMSESum",
        dataset="DplDataset",
        scaler="DapengScaler",
        scaler_params={
            "prcp_norm_cols": [
                "streamflow",
            ],
            "gamma_norm_cols": [
                "tsd_prec",
                "pr",
                "total_precipitation",
                "potential_evaporation",
                "ET",
                "tsd_pet_ou",
                "ET_sum",
                "ssm",
            ],
            "pbm_norm": True,
        },
        gage_id=[
            "A105003001",
            "A107020001",
            "A112020001",
            "A116003002",
            "A140202001",
            "A202030001",
            "A204010101",
            "A211030001",
            "A212020002",
            "A231020001",
            "A234021001",
            "A251020001",
            "A270011001",
            "A273011002",
            "A284020001",
            "A330010001",
            "A361011001",
            "A369011001",
            "A373020001",
            "A380020001",
        ],
        train_period=train_period,
        valid_period=valid_period,
        test_period=test_period,
        batch_size=20,
        forecast_history=0,
        forecast_length=30,
        var_t=var_t,
        var_c=var_c,
        var_out=["streamflow"],
        target_as_input=0,
        constant_only=0,
        train_epoch=10,
        save_epoch=1,
        model_loader={
            "load_way": "specified",
            "test_epoch": 10,
        },
        warmup_length=10,
        opt="Adadelta",
        which_first_tensor="sequence",
    )
    update_cfg(config, args)
    return config

def test_camelsfrdplsac(camelsfrdplsac_arg):
    train_and_evaluate(camelsfrdplsac_arg)
    print("All processes are finished!")
