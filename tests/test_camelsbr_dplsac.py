import os
from torchhydro.configs.config import cmd, default_config_file, update_cfg
from torchhydro import SETTING
from torchhydro.trainers.trainer import train_and_evaluate
import pytest

@pytest.fixture
def var_c():
    return [
        "elev_mean",
        "slope_mean",
        "area",
        "forest_perc",
        "crop_perc",
        "shrub_perc",
        "dom_land_cover_perc",
        "dom_land_cover",
        "org_carbon_content",
        "clay_perc",
        "sand_perc",
        "silt_perc",
        "water_table_depth",
        "geol_class_1st",
        "geol_class_2nd",
        "geol_porosity",
        "geol_permeability",
    ]

@pytest.fixture
def var_t():
    return [
        "precipitation_chirps",
        "evapotransp_mgb",
        "precipitation_mswep",
        "precipitation_cpc",
        "evapotransp_gleam",
        "potential_evapotransp_gleam",
        "temperature_min_cpc",
        "temperature_mean_cpc",
        "temperature_max_cpc",
    ]

@pytest.fixture
def camelsbrdplsac_arg(var_c,var_t):
    """
    Use attr and forcing as input for dPL model

    Parameters
    ----------
    config

    Returns
    -------

    """
    # camels-br time_range: ["1995-01-01", "2015-01-01"]
    train_period = ["2011-10-01", "2012-10-01"]
    valid_period = ["2012-10-01", "2013-10-01"]
    test_period = ["2013-10-01", "2014-10-01"]
    config = default_config_file()
    args = cmd(
        sub=os.path.join("test_camels", "dpllstmsac_camelsbr"),
        # sub=os.path.join("test_camels", "dplannsac_camelsbr"),
        source_cfgs={
            "source_name": "camels_br",
            "source_path": os.path.join(
                SETTING["local_data_path"]["datasets-origin"], "camels", "camels_br"
            ),
        },
        ctx=[-1],
        model_name="DplLstmSac",
        # model_name="DplAnnSac",
        model_hyperparam={
            "n_input_features": len(var_c)+len(var_t),  # 9 + 17 = 26
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
                "precipitation_chirps",
                "pr",
                "total_precipitation",
                "potential_evaporation",
                "ET",
                "evapotransp_mgb",
                "ET_sum",
                "ssm",
            ],
            "pbm_norm": True,
        },
        gage_id=[
            "10500000",
            "11400000",
            "11500000",
            "12370000",
            "12500000",
            "12520000",
            "12700000",
            "13150000",
            "13470000",
            "13600002",
            "13710001",
            "13750000",
            "13870000",
            "13880000",
            "14100000",
            "14110000",
            "14230000",
            "14250000",
            "14260000",
            "14280001",
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

def test_camelsbrdplsac(camelsbrdplsac_arg):
    train_and_evaluate(camelsbrdplsac_arg)
    print("All processes are finished!")

