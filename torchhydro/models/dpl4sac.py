import numpy as np
from typing import Union
import torch
from torch import nn
from torch import Tensor
from torch.nn import functional as F
from torchhydro.configs.model_config import MODEL_PARAM_DICT, MODEL_PARAM_TEST_WAY
from torchhydro.models.simple_lstm import SimpleLSTM
from torchhydro.models.ann import SimpleAnn

PRECISION = 1e-5


class SingleStepSacramento(nn.Module):
    """
    single step sacramento model
    """
    def __init__(
        self,
        device: Union[str, torch.device],
        hydrodt: int = 1,
        # area: float = None,
        para: Tensor = None,
        intervar: Tensor = None,
        rivernumber: np = None,
        mq: Tensor = None,
    ):
        """
        Initial a single-step sacramento model
        Parameters
        -----------
        device: Union[str, torch.device]
            cpu or gpu device
        hydrodt:
            the time step of hydrodata, default to one day.
        para: Tensor
            parameters of sac model, 21.
        intervar: Tensor
            the inter variables in model, 11.
            generate runoff
            auztw, the upper layer tension water accumulation on the alterable impervious area, mm.
            alztw, the lower layer tension water accumulation on the alterable impervious area, mm.
            uztw, tension water accumulation in the upper layer, mm.
            uzfw, free water accumulation in the upper layer, mm.
            lztw, tension water accumulation in the lower layer, mm.
            lzfs, speed free water accumulation in the lower layer, mm.
            lzfp, slow free water accumulation in the lower layer, mm.
            routing
            qs0, the flow of surface at the start of timestep.
            qi0, the flow of interflow at the start of timestep.
            qgs0, the flow of speed groundwater at the start of timestep.
            qgp0, the flow of slow groundwater at the start of timestep.
        rivernumber: Tensor
            the river sections number
        mq: Tensor
            the routing space of the Muskingum routing method
        """
        super(SingleStepSacramento, self).__init__()
        self.name = 'SingleStepSacramento'
        self.device = device
        # self.area = area
        self.hydrodt = hydrodt
        self.para = para
        self.intervar = intervar.detach()
        self.rivernumber = rivernumber
        self.mq = mq.detach()  # Muskingum routing space

    def cal_runoff(
        self,
        prcp: Tensor = None,
        pet: Tensor = None,
    ):
        """
        single step evaporation and generating runoff
        Parameters
        -----------
        prcp : Tensor
            precipitation, mm/d.
        pet : Tensor
            evaporation, mm/d.

        Returns
        -------
        et
            the total evaporation, mm.
        roimp, adsur, ars, rs, ri, rgs, rgp,
            the runoff of various water source, mm.
        self.intervar[:, :6]
            the inter variables, 7.
        """
        # assign values to the parameters
        kc = self.para[:, 0]
        pctim = self.para[:, 1]
        adimp = self.para[:, 2]
        uztwm = self.para[:, 3]
        uzfwm = self.para[:, 4]
        lztwm = self.para[:, 5]
        lzfsm = self.para[:, 6]
        lzfpm = self.para[:, 7]
        rserv = self.para[:, 8]
        pfree = self.para[:, 9]
        riva = self.para[:, 10]
        zperc = self.para[:, 11]
        rexp = self.para[:, 12]
        uzk = self.para[:, 13]
        lzsk = self.para[:, 14]
        lzpk = self.para[:, 15]
        # middle variables, at the start of timestep.
        auztw0 = self.intervar[:, 0].detach()
        alztw0 = self.intervar[:, 1].detach()
        uztw0 = self.intervar[:, 2].detach()
        uzfw0 = self.intervar[:, 3].detach()
        lztw0 = self.intervar[:, 4].detach()
        lzfs0 = self.intervar[:, 5].detach()
        lzfp0 = self.intervar[:, 6].detach()

        # evaporation
        ep = kc * pet  # average evaporation of basin
        roimp = prcp * pctim  # runoff of the permanent impervious area
        ae2 = pctim * ep  # evaporation of the permanent impervious area
        # evaporation of the alterable impervious area
        ae1 = torch.min(auztw0, ep * (auztw0 / uztwm))  # upper layer
        ae3_ = (ep - ae1) * (alztw0 / (uztwm + lztwm))  # lower layer
        ae3 = torch.clamp(ae3_, min=0.0)
        pav = torch.clamp(prcp - (uztwm - (auztw0 - ae1)), min=0.0)
        adsur_ = pav * ((alztw0 - ae3) / lztwm)
        adsur = torch.clamp(adsur_, min=0.0)
        ars = torch.clamp(((pav - adsur) + (alztw0 - ae3)) - lztwm, min=0.0)
        auztw_ = torch.min(uztwm, (auztw0 - ae1) + prcp)
        auztw = torch.clamp(auztw_, min=0.0)
        alztw_ = torch.min(lztwm, (pav - adsur) + (alztw0 - ae3))
        alztw = torch.clamp(alztw_, min=0.0)
        # evaporation of the permeable area
        e1 = torch.min(uztw0, ep * (uztw0 / uztwm))  # upper layer
        e2_ = torch.min(uzfw0, ep - e1)  # lower layer
        e2 = torch.clamp(e2_, min=0.0)
        e3_ = (ep - e1 - e2) * (lztw0 / (uztwm + lztwm))  # deeper layer
        e3 = torch.clamp(e3_, min=0.0)
        lt1_ = lztw0 - e3
        lt1 = torch.clamp(lt1_, min=0.0)
        e4 = riva * ep  # river net, lakes and hydrophyte
        # total evaporation
        et = ae2 + ae1 + ae3 + e1 + e2 + e3 + e4  # the total evaporation

        # generate runoff
        # runoff of the alterable impervious area
        adsur_adimp = adsur * adimp
        ars_adimp = ars * adimp
        # runoff of the permeable area
        parea = 1 - pctim - adimp
        rs = torch.clamp(prcp + (uztw0 + uzfw0 - e1 - e2) - (uztwm + uzfwm), min=0.0) * parea
        ut_ = torch.min(uztwm, uztw0 - e1 + prcp)
        ut = torch.clamp(ut_, min=0.0)
        uf_ = torch.min(uzfwm, prcp + (uztw0 + uzfw0 - e1 - e2) - ut)
        uf = torch.clamp(uf_, min=0.0)
        ri = uf * uzk  # interflow
        uf_ = uf - ri
        uf = torch.clamp(uf_, min=0.0)
        # the infiltrated water
        pbase = lzfsm * lzsk + lzfpm * lzpk
        defr_ = 1 - (lzfs0 + lzfp0 + lt1) / (lzfsm + lzfpm + lztwm)
        defr = torch.clamp(defr_, min=0.0)
        perc = pbase * (1 + zperc * pow(defr, rexp)) * uf / uzfwm
        rate_ = torch.min(perc, (lzfsm + lzfpm + lztwm) - (lzfs0 + lzfp0 + lt1))
        rate = torch.clamp(rate_, min=0.0)
        # assign the infiltrate water
        fx_ = torch.min(lzfsm + lzfpm - (lzfs0 + lzfp0), torch.max(rate - (lztwm - lt1), rate * pfree))
        fx = torch.clamp(fx_, min=0.0)
        perct_ = rate - fx
        perct = torch.clamp(perct_, min=0.0)
        coef_ = (lzfpm / (lzfsm + lzfpm)) * (2 * (1 - lzfp0 / lzfpm) / ((1 - lzfp0 / lzfpm) + (1 - lzfsm / lzfsm)))
        coef = torch.clamp(coef_, min=0.0, max=1.0)
        percp_ = torch.min(lzfpm - lzfp0, torch.max(fx - (lzfsm - lzfs0), coef * fx))
        percp = torch.clamp(percp_, min=0.0)
        percs_ = fx - percp
        percs = torch.clamp(percs_, min=0.0)
        # update the soil moisture accumulation
        lt2 = lt1 + perct
        ls = lzfs0 + percs
        lp = lzfp0 + percp
        # generate groundwater runoff
        rgs = ls * lzsk
        ls2_ = ls - rgs
        ls2 = torch.clamp(ls2_, min=0.0)
        rgp = lp * lzpk
        lp2_ = lp - rgp
        lp2 = torch.clamp(lp2_, min=0.0)
        # water balance check
        utr = ut / uztwm
        ufr = uf / uzfwm
        utfr = (ut + uf) / (uztwm + uzfwm)
        uztw = torch.where(utr < ufr, uztwm * utfr, ut)
        uzfw = torch.where(utr < ufr, uzfwm * utfr, uf)
        saved = rserv * (lzfsm + lzfpm)
        ratio_ = (ls + lp - saved + lt2) / (lzfsm + lzfpm - saved + lztwm)
        ratio = torch.clamp(ratio_, min=0.0)
        ltr = lt2 / lztwm
        lztw = torch.where(ltr < ratio, lztwm * ratio, lt2)
        lzfs = torch.where(ltr < ratio, torch.clamp(ls - (lztw - lt2), min=0.0), ls2)
        lzfp = torch.where(ltr < ratio, lp - torch.clamp((lztw - lt2) - ls, min=0.0), lp2)
        # if lt / lztwm < ratio:
        #     lztw = lztwm * ratio
        #     del_ = lztw - lt
        #     lzfs = torch.clamp(ls - del_, min=0.0)
        #     lzfp = lp - torch.clamp(del_ - ls, min=0.0)
        # else:
        #     lztw = lt
        #     lzfs = ls
        #     lzfp = lp

        # rs = roimp + (adsur + ars) + rs  # the total surface runoff

        # middle variables, at the end of timestep.
        self.intervar[:, 0] = auztw.detach()
        self.intervar[:, 1] = alztw.detach()
        self.intervar[:, 2] = uztw.detach()
        self.intervar[:, 3] = uzfw.detach()
        self.intervar[:, 4] = lztw.detach()
        self.intervar[:, 5] = lzfs.detach()
        self.intervar[:, 6] = lzfp.detach()

        return et, roimp, adsur_adimp, ars_adimp, rs, ri, rgs, rgp, self.intervar[:, :7]

    def cal_routing(
        self,
        roimp: Tensor = None,
        adsur: Tensor = None,
        ars: Tensor = None,
        rs: Tensor = None,
        ri: Tensor = None,
        rgs: Tensor = None,
        rgp: Tensor = None,
    ):
        """
        single step routing

        Parameters
        ----------
        roimp: Tensor
            runoff of the permanent impervious area, mm.
        adsur: Tensor
            runoff of the alterable impervious area, mm.
        ars: Tensor
            runoff of the alterable impervious area, mm.
        rs: Tensor
            surface runoff of the permeable area, mm.
        ri: Tensor
            runoff of interflow, mm.
        rgs: Tensor
            runoff of speed groundwater, mm.
        rgp: Tensor
            runoff of slow groundwater, mm.
        Returns
        -------
        q_sim: Tensor
            the outflow at the end of timestep, m^3/s.
        self.intervar[:, 7:]
            the inter variables of routing part, m^3/s, 4.
        """
        n_basin, _ = self.intervar.size()
        # parameters
        pctim = self.para[:, 1]
        adimp = self.para[:, 2]
        ci = self.para[:, 16]
        cgs = self.para[:, 17]
        cgp = self.para[:, 18]
        ke = self.para[:, 19]
        xe = self.para[:, 20]
        # middle variables, at the start of timestep.
        qs0 = self.intervar[:, 7].detach()  #
        qi0 = self.intervar[:, 8].detach()
        qgs0 = self.intervar[:, 9].detach()
        qgp0 = self.intervar[:, 10].to(self.device)

        # routing
        parea = 1 - pctim - adimp
        # parea = torch.clamp(parea_, min=0.0)
        u = parea * 1000 # * self.area   # daily coefficient, no need conversion.  # todo: area
        # slope routing, use the linear reservoir method
        qs = (roimp + (adsur + ars) * adimp + rs * parea) * 1000.0  # * self.area  # todo: area
        qi = ci * qi0 + (1 - ci) * ri * u
        # qi = torch.clamp(qi_, min=0.0)
        qgs = cgs * qgs0 + (1 - cgs) * rgs * u
        # qgs = torch.clamp(qgs_, min=0.0)
        qgp = torch.add(torch.mul(cgp, qgp0), torch.mul((1 - cgp), torch.mul(rgp, u)))  # modified by an inplace operation https://www.cnblogs.com/jiangkejie/p/13390377.html
        qgp = torch.clamp(qgp, min=0.0)
        q_sim_ = (qs.clone() + qi.clone() + qgs.clone() + qgp.clone())  # time|basin, two dimension tensor
        # middle variable, at the end of timestep.
        self.intervar[:, 7] = qs.detach()
        self.intervar[:, 8] = qi.detach()
        self.intervar[:, 9] = qgs.detach()
        self.intervar[:, 10] = qgp.detach()

        # river routing, use the Muskingum routing method
        ke_ = torch.full(ke.size(),0.0).detach()
        q_sim_0 = (qs0 + qi0 + qgs0 + qgp0).detach()
        for i in range(n_basin):
            if self.rivernumber[i] > 0:
                dt = self.hydrodt * 24.0 / 2.0
                xo = xe[i].detach()
                ke_[i] = (ke[i] * 24.0).detach()  # KE is hourly coefficient, need convert to daily.
                ko = (ke_[i] / self.rivernumber[i]).detach()
                c1 = (max(ko * (1.0 - xo) + dt, 0.0)).detach()
                c2 = (max((-ko * xo + dt) / c1, 0.0)).detach()
                c3 = max((ko * (1.0 - xo) - dt) / c1, 0.0)
                c1_ = ((ko * xo + dt) / c1).detach()
                i1 = q_sim_0[i].detach()  # flow at the start of timestep, inflow.
                i2 = q_sim_[i].detach()  # flow at the end of timestep, outflow.
                for j in range(self.rivernumber[i]):
                    q_sim_0[i] = self.mq[i, j]  # basin|rivernumber
                    i2_ = (c1_ * i1 + c2 * i2 + c3 * q_sim_0[i]).detach()
                    self.mq[i, j] = i2_
                    i1 = q_sim_0[i].detach()
                    i2 = i2_.detach()
            q_sim_[i] = i2  # todo: a problem

        return q_sim_, self.intervar[:, 7:]  # qs, qi, qgs, qgp,

class Sac4Dpl(nn.Module):
    """
    Sacramento model for differential Parameter learning module
    """
    def __init__(
        self,
        warmup_length: int,
        source_book="HF",
    ):
        """
        Initiate a Sacramento model instance.
        Parameters
        ----------
        warmup_length
            the length of warmup periods 预热期
            sac needs a warmup period to generate reasonable initial state values 需要预热，形成初始条件
        nn_dropout
            the dropout rate of neural network 神经网络中间层神经元的暂退率，(0.3, 0.5)，提高模型的稳健性。暂时退出、暂时不参与模拟计算的概率。什么时候重回计算呢？动态暂退？
        param_test_way
            the way to test the model parameters, final. 模型参数测试方式，取final式。
        """
        super(Sac4Dpl, self).__init__()
        self.name = "Sacramento"
        self.params_names = MODEL_PARAM_DICT["sac"]["param_name"]
        param_range = MODEL_PARAM_DICT["sac"]["param_range"]
        self.kc_scale = param_range["KC"]
        self.pctim_scale = param_range["PCTIM"]
        self.adimp_scale = param_range["ADIMP"]
        self.uztwm_scale = param_range["UZTWM"]
        self.uzfwm_scale = param_range["UZFWM"]
        self.lztwm_scale = param_range["LZTWM"]
        self.lzfsm_scale = param_range["LZFSM"]
        self.lzfpm_scale = param_range["LZFPM"]
        self.rserv_scale = param_range["RSERV"]
        self.pfree_scale = param_range["PFREE"]
        self.riva_scale = param_range["RIVA"]
        self.zperc_scale = param_range["ZPERC"]
        self.rexp_scale = param_range["REXP"]
        self.uzk_scale = param_range["UZK"]
        self.lzsk_scale = param_range["LZSK"]
        self.lzpk_scale = param_range["LZPK"]
        self.ci_scale = param_range["CI"]
        self.cgs_scale = param_range["CGS"]
        self.cgp_scale = param_range["CGP"]
        self.ke_scale = param_range["KE"]
        self.xe_scale = param_range["XE"]

        self.warmup_length = warmup_length
        self.feature_size = 2       # there are 2 input variables in Sac, P and PET. P and Pet are two feature in nn model.
        self.source_book = source_book

    def forward(
        self,
        p_and_e: Tensor,
        parameters: Tensor,
        return_state: bool = False,
    ):
        """
        sac model
        forward transmission

        Parameters
        ----------
        p_and_e: Tensor
            time|basin|p_and_e
        prcp
            basin mean precipitation, mm/d.
        pet
            potential evapotranspiration, mm/d.
        parameters: Tensor
            model parameters, 21.
        return_state: bool
            whether to return model state or not.
        --model parameters--
        kc
            coefficient of potential evapotranspiration to reference crop evaporation generally
        pctim
            ratio of the permanent impervious area to total area of the basin
        uztwm
            tension water capacity in the upper layer, mm.
        lztwm
            tension water capacity in the lower layer, mm.
        riva
            ratio of river net, lakes and hydrophyte area to total area of the basin
        area
            basin area, km^2.
        rivernumber
            the river sections number
        rs
            surface runoff, mm.
        ri
            interflow runoff, mm.
        rgs
            speedy groundwater runoff, mm.
        rgp
            slow groundwater runoff, mm.
        q_sim_0

        Returns
        -------
        q_sim : torch.Tensor
        the simulated flow, Q(m^3/s).
        e_sim : torch.Tensor
            the simulated evaporation, E(mm/d).
        """
        sac_device = p_and_e.device
        n_basin, n_para = parameters.size()

        # para = torch.full((kc.size(),parameters.shap(1)),[kc, pctim, adimp, uztwm, uzfwm, lztwm, lzfsm, lzfpm, rserv, pfree, riva, zperc, rexp, uzk, lzsk, lzpk, ci, cgs, cgp, ke, xe],)
        # area = [2252.7, 573.6, 3676.17, 769.05, 909.1, 383.82, 180.98, 250.64, 190.92, 31.3]     # dpl4sac_args camelsus [gage_id.area]  # todo: 线性水库汇流需要用到流域面积将产流runoff的mm乘以面积的m^2将平面径流转化为流量的m^3/s
        rsnpb = 1  # river sections number per basin
        mq = torch.full((n_basin, rsnpb),0.0).detach()  # Muskingum routing space   basin|rivernumber   note: the column number of mp must equle to the column number of rivernumber   todo: ke, river section number
        if self.warmup_length > 0:  # if warmup_length>0, use warmup to calculate initial state.
            # set no_grad for warmup periods
            with torch.no_grad():
                p_and_e_warmup = p_and_e[0:self.warmup_length, :, :]  # time|basin|p_and_e
                cal_init_sac4dpl = Sac4Dpl(
                    # warmup_length must be 0 here
                    warmup_length=0,
                )
                if cal_init_sac4dpl.warmup_length > 0:
                    raise RuntimeError("Please set init model's warmup length to 0!!!")
                _, _, intervar = cal_init_sac4dpl(  # note: parameter should be the parameters before de-normalizing.
                    p_and_e_warmup, parameters, return_state=True
                )
        else:  # if no, set a small value directly.
            # intervar = torch.full((n_basin, 11), 0.1).detach()  # basin|inter_variables
            auztw = (torch.zeros(n_basin, dtype=torch.float32) + 0.01).to(sac_device)
            alztw = (torch.zeros(n_basin, dtype=torch.float32) + 0.01).to(sac_device)
            uztw = (torch.zeros(n_basin, dtype=torch.float32) + 0.01).to(sac_device)
            uzfw = (torch.zeros(n_basin, dtype=torch.float32) + 0.01).to(sac_device)
            lztw = (torch.zeros(n_basin, dtype=torch.float32) + 0.01).to(sac_device)
            lzfs = (torch.zeros(n_basin, dtype=torch.float32) + 0.01).to(sac_device)
            lzfp = (torch.zeros(n_basin, dtype=torch.float32) + 0.01).to(sac_device)
            qs0 = self.intervar[:, 7].detach()  #
            qi0 = self.intervar[:, 8].detach()
            qgs0 = self.intervar[:, 9].detach()
            qgp0 = self.intervar[:, 10].to(self.device)
            mq = torch.full((n_basin, rsnpb), 0.01).detach()  # Muskingum routing space   basin|rivernumber   note: the column number of mp must equle to the column number of rivernumber   todo: ke, river section number
        rivernumber = np.full(n_basin, 1)  # set only one river section.   basin|river_section

        # parameters
        para = torch.full((n_basin, n_para), 0.0)
        kc = self.kc_scale[0] + parameters[:, 0] * (self.kc_scale[1] - self.kc_scale[0])    # parameters[:, 0]是个二维张量， 流域|参数  kc是个一维张量，不同流域的参数。  basin first
        pctim = self.pctim_scale[0] + parameters[:, 1] * (self.pctim_scale[1] - self.pctim_scale[0])
        adimp = self.adimp_scale[0] + parameters[:, 2] * (self.adimp_scale[1] - self.adimp_scale[0])
        uztwm = self.uztwm_scale[0] + parameters[:, 3] * (self.uztwm_scale[1] - self.uztwm_scale[0])
        uzfwm = self.uzfwm_scale[0] + parameters[:, 4] * (self.uzfwm_scale[1] - self.uzfwm_scale[0])
        lztwm = self.lztwm_scale[0] + parameters[:, 5] * (self.lztwm_scale[1] - self.lztwm_scale[0])
        lzfsm = self.lzfsm_scale[0] + parameters[:, 6] * (self.lzfsm_scale[1] - self.lzfsm_scale[0])
        lzfpm = self.lzfpm_scale[0] + parameters[:, 7] * (self.lzfpm_scale[1] - self.lzfpm_scale[0])
        rserv = self.rserv_scale[0] + parameters[:, 8] * (self.rserv_scale[1] - self.rserv_scale[0])
        pfree = self.pfree_scale[0] + parameters[:, 9] * (self.pfree_scale[1] - self.pfree_scale[0])
        riva = self.riva_scale[0] + parameters[:, 10] * (self.riva_scale[1] - self.riva_scale[0])
        zperc = self.zperc_scale[0] + parameters[:, 11] * (self.zperc_scale[1] - self.zperc_scale[0])
        rexp = self.rexp_scale[0] + parameters[:, 12] * (self.rexp_scale[1] - self.rexp_scale[0])
        uzk = self.uzk_scale[0] + parameters[:, 13] * (self.uzk_scale[1] - self.uzk_scale[0])
        lzsk = self.lzsk_scale[0] + parameters[:, 14] * (self.lzsk_scale[1] - self.lzsk_scale[0])
        lzpk = self.lzpk_scale[0] + parameters[:, 15] * (self.lzpk_scale[1] - self.lzpk_scale[0])
        ci = self.ci_scale[0] + parameters[:, 16] * (self.ci_scale[1] - self.ci_scale[0])
        cgs = self.cgs_scale[0] + parameters[:, 17] * (self.cgs_scale[1] - self.cgs_scale[0])
        cgp = self.cgp_scale[0] + parameters[:, 18] * (self.cgp_scale[1] - self.cgp_scale[0])
        ke = self.ke_scale[0] + parameters[:, 19] * (self.ke_scale[1] - self.ke_scale[0])
        xe = self.xe_scale[0] + parameters[:, 20] * (self.xe_scale[1] - self.xe_scale[0])

        prcp = p_and_e[self.warmup_length:, :, 0]  # time|basin
        pet = p_and_e[self.warmup_length:, :, 1]  # time|basin
        n_step, n_basin = prcp.size()
        singlesac = SingleStepSacramento(sac_device, 1, para, intervar, rivernumber, mq)  # todo: hydrodt
        e_sim_ = torch.full((n_step, n_basin), 0.0).to(sac_device)
        q_sim_ = torch.full((n_step, n_basin), 0.0).to(sac_device)
        # qs_ = torch.full((n_step, n_basin), 0.0).to(sac_device)  #
        # qi_ = torch.full((n_step, n_basin), 0.0).to(sac_device)
        # qgs_ = torch.full((n_step, n_basin), 0.0).to(sac_device)
        # qgp_ = torch.full((n_step, n_basin), 0.0).to(sac_device)
        roimp_ = torch.full((n_step, n_basin), 0.0).to(sac_device)
        adsur_ = torch.full((n_step, n_basin), 0.0).to(sac_device)
        ars_ = torch.full((n_step, n_basin), 0.0).to(sac_device)
        rs_ = torch.full((n_step, n_basin), 0.0).to(sac_device)
        ri_ = torch.full((n_step, n_basin), 0.0).to(sac_device)
        rgs_ = torch.full((n_step, n_basin), 0.0).to(sac_device)
        rgp_ = torch.full((n_step, n_basin), 0.0).to(sac_device)
        for i in range(n_step):
            p = torch.clamp(prcp[i, :], min=0.0)
            e_ = torch.nan_to_num(pet[i, :], nan=0.0, posinf=0.0, neginf=0.0)
            e = torch.clamp(e_, min=0.0)
            # evaporation
            ep = kc * e  # average evaporation of basin
            roimp = pctim * p  # runoff of the permanent impervious area
            ae2 = pctim * ep  # evaporation of the permanent impervious area
            # evaporation of the alterable impervious area
            ae1 = torch.min(auztw, ep * (auztw / uztwm))  # upper layer
            ae3_ = (ep - ae1) * (alztw / (uztwm + lztwm))  # lower layer
            ae3 = torch.clamp(ae3_, min=0.0)
            pav = torch.clamp(prcp - (uztwm - (auztw - ae1)), min=0.0)
            adsur_ = pav * ((alztw - ae3) / lztwm)
            adsur = torch.clamp(adsur_, min=0.0)
            ars = torch.clamp(((pav - adsur) + (alztw - ae3)) - lztwm, min=0.0)
            auztw_ = torch.min(uztwm, (auztw - ae1) + prcp)
            auztw = torch.clamp(auztw_, min=0.0)
            alztw_ = torch.min(lztwm, (pav - adsur) + (alztw - ae3))
            alztw = torch.clamp(alztw_, min=0.0)
            # evaporation of the permeable area
            e1 = torch.min(uztw, ep * (uztw / uztwm))  # upper layer
            e2_ = torch.min(uzfw, ep - e1)  # lower layer
            e2 = torch.clamp(e2_, min=0.0)
            e3_ = (ep - e1 - e2) * (lztw / (uztwm + lztwm))  # deeper layer
            e3 = torch.clamp(e3_, min=0.0)
            lt1_ = lztw - e3
            lt1 = torch.clamp(lt1_, min=0.0)
            e4 = riva * ep  # river net, lakes and hydrophyte
            # total evaporation
            et = ae2 + ae1 + ae3 + e1 + e2 + e3 + e4  # the total evaporation

            # generate runoff
            # runoff of the alterable impervious area
            adsur_adimp = adsur * adimp
            ars_adimp = ars * adimp
            # runoff of the permeable area
            parea = 1 - pctim - adimp
            rs = torch.clamp(prcp + (uztw + uzfw - e1 - e2) - (uztwm + uzfwm), min=0.0) * parea
            ut_ = torch.min(uztwm, uztw - e1 + prcp)
            ut = torch.clamp(ut_, min=0.0)
            uf_ = torch.min(uzfwm, prcp + (uztw + uzfw - e1 - e2) - ut)
            uf = torch.clamp(uf_, min=0.0)
            ri = uf * uzk  # interflow
            uf_ = uf - ri
            uf = torch.clamp(uf_, min=0.0)
            # the infiltrated water
            pbase = lzfsm * lzsk + lzfpm * lzpk
            defr_ = 1 - (lzfs + lzfp + lt1) / (lzfsm + lzfpm + lztwm)
            defr = torch.clamp(defr_, min=0.0)
            perc = pbase * (1 + zperc * pow(defr, rexp)) * uf / uzfwm
            rate_ = torch.min(perc, (lzfsm + lzfpm + lztwm) - (lzfs + lzfp + lt1))
            rate = torch.clamp(rate_, min=0.0)
            # assign the infiltrate water
            fx_ = torch.min(lzfsm + lzfpm - (lzfs + lzfp), torch.max(rate - (lztwm - lt1), rate * pfree))
            fx = torch.clamp(fx_, min=0.0)
            perct_ = rate - fx
            perct = torch.clamp(perct_, min=0.0)
            coef_ = (lzfpm / (lzfsm + lzfpm)) * (2 * (1 - lzfp / lzfpm) / ((1 - lzfp / lzfpm) + (1 - lzfsm / lzfsm)))
            coef = torch.clamp(coef_, min=0.0, max=1.0)
            percp_ = torch.min(lzfpm - lzfp, torch.max(fx - (lzfsm - lzfs), coef * fx))
            percp = torch.clamp(percp_, min=0.0)
            percs_ = fx - percp
            percs = torch.clamp(percs_, min=0.0)
            # update the soil moisture accumulation
            lt2 = lt1 + perct
            ls = lzfs + percs
            lp = lzfp + percp
            # generate groundwater runoff
            rgs = ls * lzsk
            ls2_ = ls - rgs
            ls2 = torch.clamp(ls2_, min=0.0)
            rgp = lp * lzpk
            lp2_ = lp - rgp
            lp2 = torch.clamp(lp2_, min=0.0)
            # water balance check
            utr = ut / uztwm
            ufr = uf / uzfwm
            utfr = (ut + uf) / (uztwm + uzfwm)
            uztw = torch.where(utr < ufr, uztwm * utfr, ut)
            uzfw = torch.where(utr < ufr, uzfwm * utfr, uf)
            saved = rserv * (lzfsm + lzfpm)
            ratio_ = (ls + lp - saved + lt2) / (lzfsm + lzfpm - saved + lztwm)
            ratio = torch.clamp(ratio_, min=0.0)
            ltr = lt2 / lztwm
            lztw = torch.where(ltr < ratio, lztwm * ratio, lt2)
            lzfs = torch.where(ltr < ratio, torch.clamp(ls - (lztw - lt2), min=0.0), ls2)
            lzfp = torch.where(ltr < ratio, lp - torch.clamp((lztw - lt2) - ls, min=0.0), lp2)

            e_sim_[i] = et
            roimp_[i] = roimp
            adsur_[i] = adsur_adimp
            ars_[i] = ars_adimp
            rs_[i] = rs
            ri_[i] = ri
            rgs_[i] = rgs
            rgp_[i] = rgp

        for i in range(n_step):
            # routing
            parea = 1 - pctim - adimp
            # parea = torch.clamp(parea_, min=0.0)
            u = parea * 1000  # * self.area   # daily coefficient, no need conversion.  # todo: area
            # slope routing, use the linear reservoir method
            qs = (roimp + (adsur + ars) * adimp + rs * parea) * 1000.0  # * self.area  # todo: area
            qi = ci * qi0 + (1 - ci) * ri * u
            # qi = torch.clamp(qi_, min=0.0)
            qgs = cgs * qgs0 + (1 - cgs) * rgs * u
            # qgs = torch.clamp(qgs_, min=0.0)
            qgp = torch.add(torch.mul(cgp, qgp0), torch.mul((1 - cgp), torch.mul(rgp,
                                                                                 u)))  # modified by an inplace operation https://www.cnblogs.com/jiangkejie/p/13390377.html
            qgp = torch.clamp(qgp, min=0.0)
            q_sim_ = (qs.clone() + qi.clone() + qgs.clone() + qgp.clone())  # time|basin, two dimension tensor
            # middle variable, at the end of timestep.
            self.intervar[:, 7] = qs.detach()
            self.intervar[:, 8] = qi.detach()
            self.intervar[:, 9] = qgs.detach()
            self.intervar[:, 10] = qgp.detach()

            # river routing, use the Muskingum routing method
            ke_ = torch.full(ke.size(), 0.0).detach()
            q_sim_0 = (qs0 + qi0 + qgs0 + qgp0).detach()
            for i in range(n_basin):
                if self.rivernumber[i] > 0:
                    dt = self.hydrodt * 24.0 / 2.0
                    xo = xe[i].detach()
                    ke_[i] = (ke[i] * 24.0).detach()  # KE is hourly coefficient, need convert to daily.
                    ko = (ke_[i] / self.rivernumber[i]).detach()
                    c1 = (max(ko * (1.0 - xo) + dt, 0.0)).detach()
                    c2 = (max((-ko * xo + dt) / c1, 0.0)).detach()
                    c3 = max((ko * (1.0 - xo) - dt) / c1, 0.0)
                    c1_ = ((ko * xo + dt) / c1).detach()
                    i1 = q_sim_0[i].detach()  # flow at the start of timestep, inflow.
                    i2 = q_sim_[i].detach()  # flow at the end of timestep, outflow.
                    for j in range(self.rivernumber[i]):
                        q_sim_0[i] = self.mq[i, j]  # basin|rivernumber
                        i2_ = (c1_ * i1 + c2 * i2 + c3 * q_sim_0[i]).detach()
                        self.mq[i, j] = i2_
                        i1 = q_sim_0[i].detach()
                        i2 = i2_.detach()
                q_sim_[i] = i2  # todo: a problem

            return q_sim_, self.intervar[:, 7:]  # qs, qi, qgs, qgp,
            q_sim_[i], intervar[:, 7:] = singlesac.cal_routing(roimp_[i], adsur_[i], ars_[i], rs_[i], ri_[i], rgs_[i], rgp_[i])
            singlesac.intervar[:, 7:] = intervar[:, 7:].detach()  # update inter variabls at end of per time-step

        # seq, batch, feature
        e_sim = torch.unsqueeze(e_sim_, dim=-1)  # add a dimension,  todo: why?
        q_sim = torch.unsqueeze(q_sim_, dim=-1)
        if return_state:
            return q_sim, e_sim, intervar
        return q_sim, e_sim


class DplAnnSac(nn.Module):
    """
    Sacramento differential parameter learning - neural network model
    """
    def __init__(
        self,
        n_input_features,
        n_output_features,
        n_hidden_states,
        warmup_length,
        param_limit_func="clamp",   # 参数限制函数 限制在[0,1]
        param_test_way="final",
        source_book="HF",
    ):
        """
        Differential Parameter learning model only with attributes as DL model's input: ANN -> Param -> SAC

        The principle can be seen here: https://doi.org/10.1038/s41467-021-26107-z

        Parameters
        ----------
        n_input_features
            the number of input features of ANN
        n_output_features
            the number of output features of ANN, and it should be equal to the number of learning parameters in SAC
        n_hidden_states
            the number of hidden features of ANN; it could be Union[int, tuple, list]
        warmup_length
            the length of warmup periods;
            hydrologic models need a warmup period to generate reasonable initial state values
        param_limit_func
            function used to limit the range of params; now it is sigmoid or clamp function
        param_test_way
            how we use parameters from dl model when testing;
            now we have three ways:
            1. "final" -- use the final period's parameter for each period
            2. "mean_time" -- Mean values of all periods' parameters is used
            3. "mean_basin" -- Mean values of all basins' final periods' parameters is used
        """
        super(DplAnnSac, self).__init__()
        self.dl_model = SimpleAnn(n_input_features, n_output_features, n_hidden_states)
        self.pb_model = Sac4Dpl(
            warmup_length,
            source_book=source_book,
        )
        self.param_func = param_limit_func
        self.param_test_way = param_test_way

    def forward(self, x, z):
        """
        Differential parameter learning

        z (normalized input) -> ANN -> param -> + x (not normalized) -> sac -> q
        Parameters will be denormalized in sac model  在sac模型中参数会去正则化，即展开。

        Parameters
        ----------
        x
            not normalized data used for physical model, a sequence-first 3-dim tensor. [sequence, batch, feature]  非正则数据，序列优先的三维张量，用于物理模型。 [序列，批次，特征]  [时间|批次划分|特征（降雨、蒸发）]  流域？
            # todo: 批次划分作为一个维度？ 那是如何划分的？ 划分的过程在哪？
        z
            normalized data used for DL model, a 2-dim tensor. [batch, feature]  正则化后的数据，二维张量，用于DL模型。 [批次，特征]  [批次划分|参数]？

        Returns
        -------
        torch.Tensor
            one time forward result 单步前向传播结果？
        """
        gen = self.dl_model(z)  # SimpleAnn   使用 nn 进化参数  计算各参数对目标值损失的梯度？   传出来的是参数，经过激活函数后传到物理模型中，去正则化，进行洪水演算，模拟径流。
        if torch.isnan(gen).any():
            raise ValueError("Error: NaN values detected. Check your data firstly!!!")
        # we set all params' values in [0, 1] and will scale them when forwarding
        if self.param_func == "sigmoid":  # activation function
            params = F.sigmoid(gen)   # 参数是通过nn模型算出来的数据，然后传进下面的物理模型中，算出 降雨 和 蒸发。 # todo: ?
        elif self.param_func == "clamp":
            params = torch.clamp(gen, min=0.0, max=1.0)  #将输入input张量每个元素的范围限制到区间[min，max], 返回一个新张量。
        else:
            raise NotImplementedError(
                "We don't provide this way to limit parameters' range!! Please choose sigmoid or clamp"
            )
        # just get one-period values, here we use the final period's values,
        # when the MODEL_PARAM_TEST_WAY is not time_varing, we use the last period's values.
        if self.param_test_way != MODEL_PARAM_TEST_WAY["time_varying"]:
            params = params[-1, :, :]   # todo: added a dimension?    basin|parameters
        # Please put p in the first location and pet in the second
        q, e = self.pb_model(x[:, :, : self.pb_model.feature_size], params)   # 再将参数代入物理模型计算径流，然后使用实测数据比对、计算目标值。反复迭代优化，计算目标值损失量。    第三维是数据项/属性项，降雨和蒸发数据   时间|流域|特征（降雨蒸发）
        # return torch.cat([q, e], dim=-1)  # catenate, 拼接 q 和 e，按列。 [0,1]
        return q


class DplLstmSac(nn.Module):
    """
    Sacramento differential parameter learning - Long short-term memory neural network model
    """
    def __init__(
        self,
        n_input_features,
        n_output_features,
        n_hidden_states,
        warmup_length,
        param_limit_func="clamp",
        param_test_way="final",
        source_book="HF",
    ):
        """
        Differential Parameter learning model: LSTM -> Param -> SAC

        The principle can be seen here: https://doi.org/10.1038/s41467-021-26107-z

        Parameters
        ----------
        n_input_features
            the number of input features of LSTM
        n_output_features
            the number of output features of LSTM, and it should be equal to the number of learning parameters in SAC
        n_hidden_states
            the number of hidden features of LSTM
        warmup_length
            the length of warmup periods;
            hydrologic models need a warmup period to generate reasonable initial state values
        param_limit_func
            function used to limit the range of params; now it is sigmoid or clamp function
        param_test_way
            how we use parameters from dl model when testing;
            now we have three ways:
            1. "final" -- use the final period's parameter for each period
            2. "mean_time" -- Mean values of all periods' parameters is used
            3. "mean_basin" -- Mean values of all basins' final periods' parameters is used
            but remember these ways are only for non-variable parameters
        """
        super(DplLstmSac, self).__init__()
        self.dl_model = SimpleLSTM(n_input_features, n_output_features, n_hidden_states)  # config.cmd.model_hyperparam.(n_input_features,n_output_features,n_hidden_states)
        self.pb_model = Sac4Dpl(
            warmup_length,
            source_book=source_book,
        )
        self.param_func = param_limit_func
        self.param_test_way = param_test_way

    def forward(self, x, z):  # where are the inputs of x and z data.
        """
        Differential parameter learning 微分参数学习

        z (normalized input) -> lstm -> param -> + x (not normalized) -> sac -> q
        正则化的输入（model_hyperparam.n_input_features） -> 到 lstm 模型中 -> 输出参数（model_hyperparam.n_output_features -> 加上未正则化的x(降雨蒸发)数据 -> 到 sac 模型中 -> 模拟出径流q
        Parameters will be denormalized in sac model

        Parameters
        ----------
        x
            not normalized data used for physical model; a sequence-first 3-dim tensor. [sequence, batch, feature]
        z
            normalized data used for DL model; a sequence-first 3-dim tensor. [sequence, batch, feature]
            21 parameters of sac model, normalized.

        Returns
        -------
        torch.Tensor
            one time forward result
        """
        gen = self.dl_model(z)  # SimpleLSTM   先使用lstm优化参数，计算各参数对目标值损失函数的梯度
        if torch.isnan(gen).any():
            raise ValueError("Error: NaN values detected. Check your data firstly!!!")
        # we set all params' values in [0, 1] and will scale them when forwarding
        if self.param_func == "sigmoid":
            params = F.sigmoid(gen)
        elif self.param_func == "clamp":
            params = torch.clamp(gen, min=0.0, max=1.0)
        else:
            raise NotImplementedError(
                "We don't provide this way to limit parameters' range!! Please choose sigmoid or clamp"
            )
        # just get one-period values, here we use the final period's values,
        # when the MODEL_PARAM_TEST_WAY is not time_varing, we use the last period's values.
        if self.param_test_way != MODEL_PARAM_TEST_WAY["time_varying"]:
            params = params[-1, :, :]  # todo: why the parameters are three-dimension?   matrix operation added the dimensionalities
        # Please put p in the first location and pet in the second
        q, e = self.pb_model(x[:, :, : self.pb_model.feature_size], params)  # 再将参数代入物理模型计算径流，然后使用实测数据比对、计算目标值。反复迭代优化，计算目标值损失量。  时间|批次（流域）|特征（降雨蒸发）
        # return torch.cat([q, e], dim=-1)  # -1 means column  按列拼接 q 和 e
        return q
