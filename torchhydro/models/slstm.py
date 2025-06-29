"""
Author: Lili Yu
Date: 2025-05-10 18:00:00
LastEditTime: 2025-05-10 18:00:00
LastEditors: Lili Yu
Description: slstm model
https://kns.cnki.net/kcms2/article/abstract?v=fSCzX0TVvUiDbeilzEuM5TPhvRQk3Nr469oz_JZL3gbqkM9vTyUmexHRP3CZT8QHoqTVKe8k9W2WcDLX44gw-bjEfsxo5uvZHO2GGIuz1-QN37JGanTEcQ4d5YzPW5jNgN2u-dQAgSbBV7yBKyo2X45ZtZkH9YJgDSoP6XbWuPsvLxPrDQmOJg==&uniplatform=NZKPT&language=CHS
"""

import math
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import Tensor
from torch.nn import Module, Parameter

from torchhydro.models.ann import SimpleAnn
from torchhydro.models.dropout import DropMask, create_mask

class sLSTM(nn.Module):
    """
    stacked lstm model.
    """
    def __init__(
        self,
        input_size: int,
        output_size: int,
        hidden_size: int,
        num_layers: int = 10,
        dropout: float = 0.0,
    ):
        """

        Parameters
        ----------
        input_size
        output_size
        hidden_size
        num_layers
        dropout
        device
        dtype
        """
        super(sLSTM, self).__init__()
        self.linearIn = nn.Linear(input_size, hidden_size)
        self.lstm = nn.LSTM(
            hidden_size,
            hidden_size,
            num_layers,
            dropout=dropout,
        )
        self.linearOut = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        x0 = F.relu(self.linearIn(x))
        out_lstm, (hn, cn) = self.lstm(x0)
        out = self.linearOut(out_lstm)
        return out


class pcLSTMCell(Module):
    r"""
    single step pcLSTM cell.
    .. math::
        \begin{array}{ll} \\
            i_t = \sigma(W_{ii} x_t + b_{ii} + W_{hi} h_{t-1} + b_{hi} + W_{ci} c_{t-1}) \\  input gate
            f_t = \sigma(W_{if} x_t + b_{if} + W_{hf} h_{t-1} + b_{hf} + W_{cf} c_{t-1}) \\  forget gate
            g_t = \tanh(W_{ig} x_t + b_{ig} + W_{hg} h_{t-1} + b_{hg}) \\  input operate
            o_t = \sigma(W_{io} x_t + b_{io} + W_{ho} h_{t-1} + b_{ho} + W_{co} c_{t-1}) \\  output gate
            c_t = f_t \odot c_{t-1} + i_t \odot g_t \\  output, cell state
            h_t = o_t \odot \tanh(c_t) \\  output, hidden state
        \end{array}
    """
    def __init__(
        self,
        input_size: int,
        hidden_size: int,
        bias: bool = True,
        dropout: float = 0.0,
    ) -> None:
        """

        Parameters
        ----------
        input_size
        hidden_size
        num_layers
        bias
        dropout
        """
        super(pcLSTMCell, self).__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.bias = bias
        self.dropout = dropout

        # input to hidden weights
        self.w_xi = Parameter(Tensor(hidden_size, input_size))
        self.w_xf = Parameter(Tensor(hidden_size, input_size))
        self.w_xo = Parameter(Tensor(hidden_size, input_size))
        self.w_xc = Parameter(Tensor(hidden_size, input_size))
        # hidden to hidden weights
        self.w_hi = Parameter(Tensor(hidden_size, hidden_size))
        self.w_hf = Parameter(Tensor(hidden_size, hidden_size))
        self.w_ho = Parameter(Tensor(hidden_size, hidden_size))
        self.w_hc = Parameter(Tensor(hidden_size, hidden_size))
        # bias terms
        self.b_i = Tensor(hidden_size).fill_(0)
        self.b_f = Tensor(hidden_size).fill_(0)
        self.b_o = Tensor(hidden_size).fill_(0)
        self.b_c = Tensor(hidden_size).fill_(0)
        # cell stat weight
        self.c_i = Parameter(Tensor(hidden_size, input_size))
        self.c_f = Parameter(Tensor(hidden_size, hidden_size))
        self.c_o = Parameter(Tensor(hidden_size, hidden_size))

        # Wrap biases as parameters if desired, else as variables without gradients
        W = Parameter if bias else (lambda x: Parameter(x, requires_grad=False))
        self.b_i = W(self.b_i)
        self.b_f = W(self.b_f)
        self.b_o = W(self.b_o)
        self.b_c = W(self.b_c)
        self.reset_parameters()

    def reset_parameters(self):
        std = 1.0 / math.sqrt(self.hidden_size)
        for w in self.parameters():
            w.data.uniform_(-std, std)  # uniform distribution

    def forward(self, x: Tensor, hx: Tensor) -> Tensor:
        """
        forward function
        Parameters
        ----------
        input
            input time series
        hx
            hidden state
        Returns
        -------
        neural network
        weight spac, data space in python
        parameter space
        h, b
        data space

        """
        batch_size = x.size(0)
        h, c = hx
        if h is None:
            h = torch.zeros(  # hidden space
                batch_size,
                self.hidden_size,
                dtype=x.dtype,
                device=x.device,
                requires_grad=False
            )
            c = torch.zeros(  # cell space
                batch_size,
                self.hidden_size,
                dtype=x.dtype,
                device=x.device,
                requires_grad=False,
            )
        h = h.view(h.size(0), -1)
        c = c.view(h.size(0), -1)
        x = x.view(x.size(0), -1)
        # forget gate
        f_t = torch.mm(x, self.w_xf) + torch.mm(h, self.w_hf) + torch.mm(c, self.c_f) + self.b_f
        f_t.sigmoid_()
        # input gate
        i_t = torch.mm(x, self.w_xi) + torch.mm(h, self.w_hi) + torch.mm(c, self.c_i) + self.b_i
        i_t.sigmoid_()
        # cell computations
        g_t = torch.mm(x, self.w_xc) + torch.mm(h, self.w_hc) + self.b_c
        g_t.tanh_()
        c_t = torch.mul(c, f_t) + torch.mul(i_t, g_t)
        # output gate
        o_t = torch.mm(x, self.w_xo) + torch.mm(h, self.w_ho) + torch.mm(c_t, self.c_o) + self.b_o
        o_t.sigmoid_()
        h_t = torch.mul(o_t, torch.tanh(c_t))    # hidden state update
        # Reshape for compatibility
        h_t = h_t.view(h_t.size(0), 1, -1)
        c_t = c_t.view(c_t.size(0), 1, -1)
        if self.dropout > 0.0:
            F.dropout(h_t, p=self.dropout, training=self.training, inplace=True)

        h_t = torch.squeeze(h_t, dim=1)
        c_t = torch.squeeze(c_t, dim=1)

        return h_t, c_t

class pcLSTM(Module):
    """
    stacked pcLSTM model.  peephole connections.
    """
    def __init__(
        self,
        input_size: int,
        output_size: int,
        hidden_size: int,
        num_layers: int = 10,
        bias: bool = True,
        dropout: float = 0.0,
    ):
        super(pcLSTM, self).__init__()
        self.nx = input_size
        self.ny = output_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.bias = bias
        self.dropout = dropout
        self.linearIn = torch.nn.Linear(self.nx, self.hidden_size)
        self.lstm = [
            pcLSTMCell(
                input_size=self.hidden_size,
                hidden_size=self.hidden_size,
                dropout=self.dropout,
            )
        ] * self.num_layers
        self.linearOut = torch.nn.Linear(self.hidden_size, self.ny)

    def forward(self, x):
        nt, ngrid, nx = x.shape
        out = torch.zeros(nt, ngrid, self.ny)
        ht = None
        ct = None
        for t in range(nt):
            xt = x[t, :, :]
            xt = torch.where(torch.isnan(xt), torch.full_like(xt, 0), xt)
            x0 = F.relu(self.linearIn(xt))
            for i in range(self.num_layers):
                if i == 0:
                    ht, ct = self.lstm[i](x=x0, hx=(ht, ct))
                else:
                    ht, ct = self.lstm[i](x=ht, hx=(ht, ct))
            yt = self.linearOut(ht)
            out[t, :, :] = yt
        return out


class biLSTM(nn.Module):
    """
    Bi-directional lstm model.
    """
    def __init__(
        self,
        input_size: int,
        output_size: int,
        hidden_size: int,
        dropout: float = 0.0,
        bidirectional: bool = True,
    ):
        """

        Parameters
        ----------
        input_size
        output_size
        hidden_size
        dropout
        bidirectional
        """
        super(biLSTM, self).__init__()
        num_directions = 2 if bidirectional else 1
        self.linearIn = nn.Linear(input_size, hidden_size)
        self.lstm = nn.LSTM(
            hidden_size,
            hidden_size,
            dropout=dropout,
            bidirectional=bidirectional,
        )
        self.linearOut = nn.Linear(hidden_size * num_directions, output_size)

    def forward(self, x):
        x0 = F.relu(self.linearIn(x))
        out_lstm, (hn, cn) = self.lstm(x0)
        out = self.linearOut(out_lstm)
        return out


class sGRU(nn.Module):
    """
    Stacked Gate Recurrent Unit model, GRU.
    """
    def __init__(
        self,
        input_size: int,
        output_size: int,
        hidden_size: int,
        num_layers: int = 10,
        dropout: float = 0.0,
    ) -> None:
        """
        initialize gate recurrent unit, gru.
        Parameters
        ----------
        input_size
        output_size
        hidden_size
        num_layers
        dropout
        """
        super(sGRU, self).__init__()
        self.linearIn = nn.Linear(input_size, hidden_size)
        self.gru = nn.GRU(
            hidden_size,
            hidden_size,
            num_layers,
            dropout=dropout,
        )
        self.linearOut = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        x0 = F.relu(self.linearIn(x))
        out_gru, hn = self.gru(x0)
        out = self.linearOut(out_gru)
        return out


class GRUCell(Module):
    r"""
    single step GRU cell.
    .. math::
        \begin{array}{ll}
            r_t = \sigma(W_{ir} x_t + b_{ir} + W_{hr} h_{(t-1)} + b_{hr}) \\
            z_t = \sigma(W_{iz} x_t + b_{iz} + W_{hz} h_{(t-1)} + b_{hz}) \\
            n_t = \tanh(W_{in} x_t + b_{in} + r_t \odot (W_{hn} h_{(t-1)}+ b_{hn})) \\
            h_t = (1 - z_t) \odot n_t + z_t \odot h_{(t-1)}
        \end{array}
    """
    def __init__(
        self,
        input_size: int,
        hidden_size: int,
        bias: bool = True,
        dropout: float = 0.0,
    ) -> None:
        """
        Gated Recurrent Unit
        Parameters
        ----------
        input_size
        hidden_size
        bias
        dropout
        """
        super(GRUCell, self).__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.bias = bias
        self.dropout = dropout

        # input to hidden weights
        self.w_ir = Parameter(Tensor(hidden_size, input_size))
        self.w_hr = Parameter(Tensor(hidden_size, input_size))
        self.w_iz = Parameter(Tensor(hidden_size, input_size))
        self.w_hz = Parameter(Tensor(hidden_size, input_size))
        # hidden to hidden weights
        self.w_in = Parameter(Tensor(hidden_size, hidden_size))
        self.w_hn = Parameter(Tensor(hidden_size, hidden_size))
        # bias terms
        self.b_r = Tensor(hidden_size).fill_(0)
        self.b_z = Tensor(hidden_size).fill_(0)
        self.b_n = Tensor(hidden_size).fill_(0)

        # Wrap biases as parameters if desired, else as variables without gradients
        W = Parameter if bias else (lambda x: Parameter(x, requires_grad=False))
        self.b_r = W(self.b_r)
        self.b_z = W(self.b_z)
        self.b_n = W(self.b_n)
        self.reset_parameters()

    def reset_parameters(self):
        std = 1.0 / math.sqrt(self.hidden_size)
        for w in self.parameters():
            w.data.uniform_(-std, std)  # uniform distribution

    def forward(self, x: Tensor, hx: Tensor) -> Tensor:
        """
        forward function
        Parameters
        ----------
        input
            input time series
        hx
            hidden state
        Returns
        h_t


        """
        batch_size = x.size(0)
        h = hx
        if h is None:
            h = torch.zeros(  # hidden space
                batch_size,
                self.hidden_size,
                dtype=x.dtype,
                device=x.device,
                requires_grad=False
            )
        h = h.view(h.size(0), -1)
        x = x.view(x.size(0), -1)
        # r, reset gate
        r_t = torch.mm(x, self.w_ir) + torch.mm(h, self.w_hr)+ self.b_r
        r_t.sigmoid_()
        # z, update gate
        z_t = torch.mm(x, self.w_iz) + torch.mm(h, self.w_hz) + self.b_z
        z_t.sigmoid_()
        # n, new gate
        rh = torch.mul(r_t, h)
        n_t = torch.mm(x, self.w_in) + torch.mm(rh, self.w_hn) + self.b_n
        n_t.tanh_()
        # h, hidden state update
        h_t = torch.mul((1 - z_t), h) + torch.mul(z_t, n_t)
        # Reshape for compatibility
        h_t = h_t.view(h_t.size(0), 1, -1)
        if self.dropout > 0.0:
            F.dropout(h_t, p=self.dropout, training=self.training, inplace=True)

        h_t = torch.squeeze(h_t, dim=1)

        return h_t

class stackedGRU(Module):
    """
    stacked GRU model.
    """
    def __init__(
        self,
        input_size: int,
        output_size: int,
        hidden_size: int,
        num_layers: int = 10,
        bias: bool = True,
        dropout: float = 0.0,
    ):
        super(stackedGRU, self).__init__()
        self.nx = input_size
        self.ny = output_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.bias = bias
        self.dropout = dropout
        self.linearIn = torch.nn.Linear(self.nx, self.hidden_size)
        self.gru = [
                GRUCell(
                    input_size=self.hidden_size,
                    hidden_size=self.hidden_size,
                    dropout=self.dropout,
                )
        ]*self.num_layers
        # print("grucell model list")
        # for i in range(self.num_layers):
        #     print(self.gru[i])
        self.linearOut = torch.nn.Linear(self.hidden_size, self.ny)

    def forward(self, x):
        nt, ngrid, nx = x.shape
        out = torch.zeros(nt, ngrid, self.ny)
        ht = None
        for t in range(nt):
            xt = x[t, :, :]
            xt = torch.where(torch.isnan(xt), torch.full_like(xt, 0), xt)
            x0 = F.relu(self.linearIn(xt))
            for i in range(self.num_layers):
                if i == 0:
                    ht = self.gru[i](x=x0, hx=ht)
                else:
                    ht = self.gru[i](x=ht, hx=ht)
            yt = self.linearOut(ht)
            out[t, :, :] = yt
        return out


class GruCellTied(nn.Module):
    """
    GruCellTied model
    """

    def __init__(
        self,
        *,
        input_size,
        hidden_size,
        mode="train",
        dr=0.5,
        dr_method="drX+drW+drH",
        gpu=1
    ):
        super(GruCellTied, self).__init__()

        self.inputSize = input_size
        self.hiddenSize = hidden_size
        self.dr = dr

        # r, z
        self.w_irz = Parameter(torch.Tensor(hidden_size * 2, input_size))
        self.w_hrz = Parameter(torch.Tensor(hidden_size * 2, input_size))
        self.b_irz = Parameter(torch.Tensor(hidden_size * 2))
        self.b_hrz = Parameter(torch.Tensor(hidden_size * 2))
        # n
        self.w_in = Parameter(torch.Tensor(hidden_size, hidden_size))
        self.w_hn = Parameter(torch.Tensor(hidden_size, hidden_size))
        self.b_in = Parameter(torch.Tensor(hidden_size))
        self.b_hn = Parameter(torch.Tensor(hidden_size))

        self.drMethod = dr_method.split("+")
        self.gpu = gpu
        self.mode = mode
        if mode == "train":
            self.train(mode=True)
        elif mode in ["test", "drMC"]:
            self.train(mode=False)
        if gpu >= 0:
            self = self.cuda()
            self.is_cuda = True
        else:
            self.is_cuda = False
        self.reset_parameters()

    def reset_parameters(self):
        stdv = 1.0 / math.sqrt(self.hiddenSize)
        for weight in self.parameters():
            weight.data.uniform_(-stdv, stdv)

    def reset_mask(self, x, h):
        self.mask_x = create_mask(x, self.dr)
        self.mask_h = create_mask(h, self.dr)
        self.mask_w_irz = create_mask(self.w_irz, self.dr)
        self.mask_w_hrz = create_mask(self.w_hrz, self.dr)
        self.mask_w_in = create_mask(self.w_in, self.dr)
        self.mask_w_hn = create_mask(self.w_hn, self.dr)

    def forward(self, x, hidden, *, do_reset_mask=True, do_drop_mc=False):
        do_drop = self.dr > 0 and (do_drop_mc is True or self.training is True)
        batch_size = x.size(0)
        h0 = hidden
        if h0 is None:
            h0 = x.new_zeros(batch_size, self.hiddenSize, requires_grad=False)

        if self.dr > 0 and self.training is True and do_reset_mask is True:
            self.reset_mask(x, h0)

        if do_drop and "drH" in self.drMethod:
            h0 = DropMask.apply(h0, self.mask_h, True)

        if do_drop and "drX" in self.drMethod:
            x = DropMask.apply(x, self.mask_x, True)

        if do_drop and "drW" in self.drMethod:
            w_irz = DropMask.apply(self.w_irz, self.mask_w_irz, True)
            w_hrz = DropMask.apply(self.w_hrz, self.mask_w_hrz, True)
            w_in = DropMask.apply(self.w_in, self.mask_w_in, True)
            w_hn = DropMask.apply(self.w_hn, self.mask_w_hn, True)
        else:
            # self.w are parameters, while w are not
            w_irz = self.w_irz
            w_hrz = self.w_hrz
            w_in = self.w_in
            w_hn = self.w_hn

        # r,z gate
        gates_rz = F.linear(x, w_irz, self.b_irz) + F.linear(h0, w_hrz, self.b_hrz)
        gate_r, gate_z = gates_rz.chunk(2, 1)
        gate_r = torch.sigmoid(gate_r)
        gate_z = torch.sigmoid(gate_z)

        # n gate
        rh = torch.mul(gate_r, h0)
        gate_n = F.linear(x, w_in, self.b_in) + F.linear(rh, w_hn, self.b_hn)
        gate_n = torch.tanh(gate_n)

        # hidden state update
        h1 = torch.mul((1-gate_z), gate_n) + torch.mul(gate_z, h0)

        return h1

class CpuGruModel(nn.Module):
    """
    Cpu version of CudnnGruModel
    """
    def __init__(
            self,
            *,
            input_size,
            output_size,
            hidden_size,
            dr=0.5,
    ):
        super(CpuGruModel, self).__init__()
        self.nx = input_size
        self.ny = output_size
        self.hiddenSize = hidden_size
        self.nLayer = 1
        self.linearIn = torch.nn.Linear(input_size, hidden_size)
        self.gru = GruCellTied(
            input_size=hidden_size,
            hidden_size=hidden_size,
            dr=dr,
            dr_method="drW",
            gpu=-1,
        )
        self.linearOut = torch.nn.Linear(hidden_size, output_size)
        self.gpu = -1

    def forward(self, x, do_drop_mc=False):
        # x0 = F.relu(self.linearIn(x))
        # outGRU, hn = self.gru(x0, do_drop_mc=do_drop_mc)
        # out = self.linearOut(outGRU)
        # return out
        nt, ngrid, nx = x.shape
        out = torch.zeros(nt, ngrid, self.ny)
        ht = None
        reset_mask = True
        for t in range(nt):
            xt = x[t, :, :]
            xt = torch.where(torch.isnan(xt), torch.full_like(xt, 0), xt)
            x0 = F.relu(self.linearIn(xt))
            ht = self.gru(x0, hidden=ht, do_reset_mask=reset_mask)
            yt = self.linearOut(ht)
            reset_mask = False
            out[t, :, :] = yt
        return out


class CudnnGru(nn.Module):
    """
    Only run in GPU; the CPU version is GruCellTied in this file
    """
    def __init__(self, *, input_size, hidden_size, dr=0.5):
        """

        Parameters
        ----------
        input_size
            number of neurons in input layer
        hidden_size
            number of neurons in hidden layer
        dr
            dropout rate
        """
        super(CudnnGru, self).__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.dr = dr

        # r,z gate
        self.w_irz = Parameter(torch.Tensor(hidden_size * 2, input_size))
        self.w_hrz = Parameter(torch.Tensor(hidden_size * 2, hidden_size))
        self.b_irz = Parameter(torch.Tensor(hidden_size * 2))
        self.b_hrz = Parameter(torch.Tensor(hidden_size * 2))
        # n gate
        # n
        self.w_in = Parameter(torch.Tensor(hidden_size, hidden_size))
        self.w_hn = Parameter(torch.Tensor(hidden_size, hidden_size))
        self.b_in = Parameter(torch.Tensor(hidden_size))
        self.b_hn = Parameter(torch.Tensor(hidden_size))

        self._all_weights = [["w_irz", "w_hrz", "w_in", "w_hn", "b_irz", "b_hrz", "b_in", "b_hn"]]
        # self.cuda()
        # set the mask
        self.reset_mask()
        # initialize the weights and bias of the model
        self.reset_parameters()

    def _apply(self, fn):
        """just use the default _apply function

        Parameters
        ----------
        fn : function
            _description_

        Returns
        -------
        _type_
            _description_
        """
        # _apply is always recursively applied to all submodules and the module itself such as move all to GPU
        return super()._apply(fn)

    def __setstate__(self, d):
        """a python magic function to set the state of the object used for deserialization

        Parameters
        ----------
        d : _type_
            _description_
        """
        super().__setstate__(d)
        # set a default value for _data_ptrs
        self.__dict__.setdefault("_data_ptrs", [])
        if "all_weights" in d:
            self._all_weights = d["all_weights"]
        if isinstance(self._all_weights[0][0], str):
            return
        self._all_weights = [["w_irz", "w_hrz", "w_in", "w_hn", "b_irz", "b_hrz", "b_in", "b_hn"]]

    def reset_mask(self):
        """generate mask for dropout"""
        self.mask_w_irz = create_mask(self.w_irz, self.dr)
        self.mask_w_hrz = create_mask(self.w_hrz, self.dr)
        self.mask_w_in = create_mask(self.w_in, self.dr)
        self.mask_w_hn = create_mask(self.w_hn, self.dr)

    def reset_parameters(self):
        """initialize the weights and bias of the model using Xavier initialization"""
        stdv = 1.0 / math.sqrt(self.hidden_size)
        for weight in self.parameters():
            # uniform distribution between -stdv and stdv for the weights and bias initialization
            weight.data.uniform_(-stdv, stdv)

    def forward(self, input, hx=None,do_drop_mc=False, dropout_false=False):
        # dropout_false: it will ensure do_drop is false, unless do_drop_mc is true
        if dropout_false and (not do_drop_mc):
            do_drop = False
        elif self.dr > 0 and (do_drop_mc is True or self.training is True):
            # if train mode and set self.dr > 0, then do_drop is true
            # so each time the model forward function is called, the dropout is applied
            do_drop = True
        else:
            do_drop = False
        # input must be a tensor with shape (seq_len, batch, input_size)
        batch_size = input.size(1)

        if hx is None:
            hx = input.new_zeros(1, batch_size, self.hidden_size, requires_grad=False)

        # handle = torch.backends.cudnn.get_handle()
        if do_drop is True:
            # cuDNN backend - disabled flat weight
            # NOTE: each time the mask is newly generated, so for each batch the mask is different
            self.reset_mask()
            # apply the mask to the weights
            weight = [
                DropMask.apply(self.w_irz, self.mask_w_irz, True),
                DropMask.apply(self.w_hrz, self.mask_w_hrz, True),
                DropMask.apply(self.w_in, self.mask_w_in, True),
                DropMask.apply(self.w_hn, self.mask_w_hn, True),
                self.b_irz,
                self.b_hrz,
                self.b_in,
                self.b_hn,
            ]
        else:
            weight = [self.w_irz, self.w_hrz, self.w_in, self.w_hn, self.b_irz, self.b_hrz, self.b_in, self.b_hn]
        if torch.__version__ < "1.8":
            output, hy, cy, reserve, new_weight_buf = torch._cudnn_rnn(
                input,
                weight,
                2,
                None,
                hx,
                None,
                3,  # 3 means GRU
                self.hidden_size,
                1,
                False,
                0,
                self.training,
                False,
                (),
                None,
            )
        else:
            output, hy, cy, reserve, new_weight_buf = torch._cudnn_rnn(
                input,
                weight,
                2,
                None,
                hx,
                None,
                3,  # 3 means GRU
                self.hidden_size,
                0,
                1,
                False,
                0,
                self.training,
                False,
                (),
                None,
            )
        return output, hy

    @property
    def all_weights(self):
        """return all weights and bias of the model as a list"""
        # getattr() is used to get the value of an object's attribute
        return [
            [getattr(self, weight) for weight in weights]
            for weights in self._all_weights
        ]

class CudnnGruModel(nn.Module):
    def __init__(self, input_size, output_size, hidden_size, dr=0.5):
        """
        only gpu version Gru Model

        Parameters
        ----------
        input_size
            the number of input features
        output_size
            the number of output features
        hidden_size
            the number of hidden features
        dr
            dropout rate and its default is 0.5
        """
        super(CudnnGruModel, self).__init__()
        self.nx = input_size
        self.ny = output_size
        self.hidden_size = hidden_size
        self.nLayer = 1
        self.linearIn = torch.nn.Linear(self.nx, self.hidden_size)
        self.gru = CudnnGru(
            input_size=self.hidden_size, hidden_size=self.hidden_size, dr=dr
        )
        self.linearOut = torch.nn.Linear(self.hidden_size, self.ny)

    def forward(self, x, do_drop_mc=False, dropout_false=False, return_h=False):
        x0 = F.relu(self.linearIn(x))
        out_lstm, hn = self.gru(
            x0, do_drop_mc=do_drop_mc, dropout_false=dropout_false
        )
        out = self.linearOut(out_lstm)
        return (out, hn) if return_h else out


class CudnnGruModelGruKernel(nn.Module):
    """use a trained/un-trained CudnnGru as a kernel generator before another CudnnGru."""

    def __init__(
        self,
        input_size,
        output_size,
        hidden_size,
        nk=None,
        hidden_size_later=None,
        cut=False,
        dr=0.5,
        delta_s=False,
    ):
        """delta_s means we will use the difference of the first gru's output and the second's as the final output"""
        super(CudnnGruModelGruKernel, self).__init__()
        # These three layers are same with CudnnGruModel to be used for transfer learning or just vanilla-use
        self.linearIn = torch.nn.Linear(input_size, hidden_size)
        self.gru = CudnnGru(input_size=hidden_size, hidden_size=hidden_size, dr=dr)
        self.linearOut = torch.nn.Linear(hidden_size, output_size)
        # if cut is True, we will only select the final index in nk, and repeat it, then concatenate with x
        self.cut = cut
        # the second gru has more input than the previous
        if nk is None:
            nk = output_size
        if hidden_size_later is None:
            hidden_size_later = hidden_size
        self.linear_in_later = torch.nn.Linear(input_size + nk, hidden_size_later)
        self.gru_later = CudnnGru(
            input_size=hidden_size_later, hidden_size=hidden_size_later, dr=dr
        )
        self.linear_out_later = torch.nn.Linear(hidden_size_later, output_size)

        self.delta_s = delta_s
        # when delta_s is true, cut cannot be true, because they have to have same number params
        assert not (cut and delta_s)

    def forward(self, x, do_drop_mc=False, dropout_false=False):
        x0 = F.relu(self.linearIn(x))
        out_gru1, hn1 = self.gru(
            x0, do_drop_mc=do_drop_mc, dropout_false=dropout_false
        )
        gen = self.linearOut(out_gru1)
        if self.cut:
            gen = gen[-1, :, :].repeat(x.shape[0], 1, 1)
        x1 = torch.cat((x, gen), dim=len(gen.shape) - 1)
        x2 = F.relu(self.linear_in_later(x1))
        out_gru2, hn2 = self.gru_later(
            x2, do_drop_mc=do_drop_mc, dropout_false=dropout_false
        )
        out = self.linear_out_later(out_gru2)
        return gen - out if self.delta_s else (out, gen)
    

class CudnnGruModelMultiOutput(nn.Module):
    def __init__(
        self,
        n_input_features,
        n_output_features,
        n_hidden_states,
        layer_hidden_size=(128, 64),
        dr=0.5,
        dr_hidden=0.0,
    ):
        """
        Multiple output CudnnGRU.

        It has multiple output layers, each for one output, so that we can easily freeze any output layer.

        Parameters
        ----------
        n_input_features
            the size of input features
        n_output_features
            the size of output features; in this model, we set different nonlinear layer for each output
        n_hidden_states
            the size of GRU's hidden features
        layer_hidden_size
            hidden_size for multi-layers
        dr
            dropout rate
        dr_hidden
            dropout rates of hidden layers
        """
        super(CudnnGruModelMultiOutput, self).__init__()
        multi_layers = torch.nn.ModuleList()
        for i in range(n_output_features):
            multi_layers.add_module(
                "layer%d" % (i + 1),
                SimpleAnn(n_hidden_states, 1, layer_hidden_size, dr=dr_hidden),
            )
        self.multi_layers = multi_layers
        self.linearIn = torch.nn.Linear(n_input_features, n_hidden_states)
        self.gru = CudnnGru(
            input_size=n_hidden_states, hidden_size=n_hidden_states, dr=dr
        )

    def forward(self, x, do_drop_mc=False, dropout_false=False, return_h=False):
        x0 = F.relu(self.linearIn(x))
        out_gru, hn = self.gru(
            x0, do_drop_mc=do_drop_mc, dropout_false=dropout_false
        )
        outs = [mod(out_gru) for mod in self.multi_layers]
        final = torch.cat(outs, dim=-1)
        return (final, hn) if return_h else final