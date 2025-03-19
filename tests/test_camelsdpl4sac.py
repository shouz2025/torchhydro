import os
import pytest
from torchhydro.configs.config import cmd, default_config_file, update_cfg
from torchhydro import SETTING
from torchhydro.trainers.trainer import train_and_evaluate

VAR_C_CHOSEN_FROM_CAMELS_US = [
    "area_gages2",
]
VAR_T_CHOSEN_FROM_DAYMET = [
    # NOTE: prcp must be the first variable
    "prcp",
    "dayl",
    "srad",
    "swe",
    "tmax",
    "tmin",
    "vp",
]

def run_camelsdplsac(
    gage_id_file,
    var_c=VAR_C_CHOSEN_FROM_CAMELS_US,
    var_t=VAR_T_CHOSEN_FROM_DAYMET,
    train_period=None,
    valid_period=None,
    test_period=None
):
    """
    Use attr and forcing as input for dPL model

    Parameters
    ----------
    config

    Returns
    -------

    """
    if train_period is None:
        train_period = ["2006-10-01", "2008-10-01"]
    if valid_period is None:
        valid_period = ["2008-10-01", "2009-10-01"]
    if test_period is None:
        test_period = ["2009-10-01", "2010-10-01"]
    config = default_config_file()
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
        model_hyperparam={
            "n_input_features": 21,  # 21 parameter of sac model
            "n_output_features": 21,  # 输入21个参数
            "n_hidden_states": 256,
            "warmup_length": 365,
        },
        loss_func="RMSESum",
        # sampler="KuaiSampler",
        # dataset="StreamflowDataset",
        dataset="DplDataset",   # todo:
        scaler="DapengScaler",
        scaler_params={  # todo:
            "prcp_norm_cols": [
                "prcp",
            ],
            "gamma_norm_cols": [
                "prcp",
                "ET",
            ],
            "pbm_norm": True,
        },
        train_period=train_period,
        valid_period=valid_period,
        test_period=test_period,
        batch_size=50,
        forecast_length=365,
        var_c=var_c,
        var_t=var_t,
        var_out=["streamflow", "PET"],  # todo:
        n_output=2,
        target_as_input=0,
        constant_only=0,
        train_epoch=1,
        save_epoch=1,
        model_loader={
            "load_way": "specified",
            "test_epoch": 1,
        },
        warmup_length=365,
        opt="Adadelta",
        gage_id_file=gage_id_file,
        which_first_tensor="sequence",
    )
    update_cfg(config, args)
    train_and_evaluate(config)
    print("All processes are finished!")


run_camelsdplsac(
    "D:\\minio\\waterism\\datasets-origin\\camels\\camels_us\\gage_id.txt",
)

