import os
import pytest
from torchhydro.configs.config import cmd, default_config_file, update_cfg
from torchhydro import SETTING
from torchhydro.trainers.trainer import train_and_evaluate

def run_camelsdplsac(train_period=None, valid_period=None, test_period=None):
    """
    Use attr and forcing as input for dPL model

    Parameters
    ----------
    config

    Returns
    -------

    """

    if train_period is None:
        train_period = ["1985-10-01", "1995-10-01"]
    if valid_period is None:
        valid_period = ["1995-10-01", "2000-10-01"]
    if test_period is None:
        test_period = ["2000-10-01", "2010-10-01"]
    config = default_config_file()
    # return cmd(
    args = cmd(
        sub=os.path.join("test_camels", "expdpl4sac"),
        source_cfgs={
            "source_name": "camels_us",
            "source_path": os.path.join(
                SETTING["local_data_path"]["datasets-origin"], "camels", "camels_us"
            ),
        },
        ctx=[-1],
        model_name="DplLstmSac",
        model_hyperparam={  # reference to run_camelsdplxaj_experiments.rundplxaj
            "n_input_features": 25,  # ?
            "n_output_features": 21,  # 输入21个参数
            "n_hidden_states": 256,
            "warmup_length": 10,
            "param_limit_func": "clamp",
            "param_test_way": "final"
        },
        loss_func="RMSESum",
        dataset="DplDataset",
        scaler="DapengScaler",
        scaler_params={
            "prcp_norm_cols": ["streamflow"],
            "gamma_norm_cols": [
                "prcp",
                "pr",
                "total_precipitation",
                "potential_evaporation",
                "ET",
                "PET",
                "ET_sum",
                "ssm",
            ],
            "pbm_norm": True,
        },
        gage_id=[  # 10 ?
            "01013500",
            "01022500",
            "01030500",
            "01031500",
            "01047000",
            "01052500",
            "01054200",
            "01055000",
            "01057000",
            "01170100",
        ],
        train_period=train_period,
        valid_period=valid_period,
        test_period=test_period,
        batch_size=20,  # train 20 basin ?
        forecast_history=0,
        forecast_length=30,
        var_t=[
            "prcp",
            "PET",
            "dayl",
            "srad",
            "swe",
            "tmax",
            "tmin",
            "vp",
        ],
        var_out=["streamflow"],
        target_as_input=0,
        constant_only=0,
        train_epoch=2,
        model_loader={
            "load_way": "specified",
            "test_epoch": 20,
        },
        warmup_length=10,
        opt="Adadelta",
        which_first_tensor="sequence",
    )
    update_cfg(config, args)
    train_and_evaluate(config)


run_camelsdplsac(
    train_period=["1985-10-01", "1986-10-01"],
    valid_period=["1986-10-01", "1987-10-01"],
    test_period=["1987-10-01", "1988-10-01"],
)

