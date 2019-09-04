__author__ = 'max'

import math
import copy
import numpy as np
from enum import Enum
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.autograd import Variable
from ..nn import TreeCRF, VarMaskedGRU, VarMaskedRNN, VarMaskedLSTM, VarMaskedFastLSTM
from ..nn import SkipConnectFastLSTM, SkipConnectGRU, SkipConnectLSTM, SkipConnectRNN
from ..nn import Embedding
from ..nn import BiAAttention, BiLinear
from neuronlp2.tasks import parser
from ..transformer import TransformerEncoder
from ..nn.modules.attention_aug import AugFeatureHelper, AugBiAAttention


class PriorOrder(Enum):
    DEPTH = 0
    INSIDE_OUT = 1
    LEFT2RIGTH = 2


class BiRecurrentConvBiAffine(nn.Module):
    def __init__(self, word_dim, num_words, char_dim, num_chars, pos_dim, num_pos, num_filters, kernel_size, rnn_mode,
                 hidden_size, num_layers, num_labels, arc_space, type_space,
                 embedd_word=None, embedd_char=None, embedd_pos=None, p_in=0.33, p_out=0.33, p_rnn=(0.33, 0.33),
                 biaffine=True, pos=True, char=True,
                 train_position=False, use_con_rnn=True, trans_hid_size=1028, d_k=64, d_v=64, multi_head_attn=True,
                 num_head=8, enc_use_neg_dist=False, enc_clip_dist=0, position_dim=50, max_sent_length=200,
                 use_gpu=False, no_word=False,
                 ):
        super(BiRecurrentConvBiAffine, self).__init__()
        self.word_embedd = Embedding(num_words, word_dim, init_embedding=embedd_word)
        self.pos_embedd = Embedding(num_pos, pos_dim, init_embedding=embedd_pos) if pos else None
        self.char_embedd = Embedding(num_chars, char_dim, init_embedding=embedd_char) if char else None
        self.conv1d = nn.Conv1d(char_dim, num_filters, kernel_size, padding=kernel_size - 1) if char else None
        self.dropout_in = nn.Dropout2d(p=p_in)
        self.dropout_out = nn.Dropout2d(p=p_out)
        self.num_labels = num_labels
        self.pos = pos
        self.char = char
        self.no_word = no_word
        #
        self.use_con_rnn = use_con_rnn
        self.multi_head_attn = multi_head_attn
        self.use_gpu = use_gpu
        self.position_dim = position_dim

        if rnn_mode == 'RNN':
            RNN = VarMaskedRNN
        elif rnn_mode == 'LSTM':
            RNN = VarMaskedLSTM
        elif rnn_mode == 'FastLSTM':
            RNN = VarMaskedFastLSTM
        elif rnn_mode == 'GRU':
            RNN = VarMaskedGRU
        else:
            raise ValueError('Unknown RNN mode: %s' % rnn_mode)

        dim_enc = 0
        if not no_word:
            dim_enc = word_dim
        if pos:
            dim_enc += pos_dim
        if char:
            dim_enc += num_filters

        #
        self.encoder_layers = num_layers
        if self.use_con_rnn:
            self.rnn = RNN(dim_enc, hidden_size, num_layers=self.encoder_layers, batch_first=True,
                                       bidirectional=True, dropout=p_rnn)
            enc_output_dim = 2 * hidden_size
        else:
            if self.multi_head_attn:
                pos_emb_size = position_dim
                d_model = pos_emb_size + dim_enc
                if position_dim > 0:
                    self.position_embedding = nn.Embedding(max_sent_length, pos_emb_size)
                    if not train_position:
                        self.position_embedding.weight.requires_grad = False  # turn off pos embedding training
                        ######################### init positional embedding ##########################
                        # keep dim 0 for padding token position encoding zero vector
                        position_enc = np.array([[pos / np.power(10000, 2 * (j // 2) / pos_emb_size) for j in
                                                  range(pos_emb_size)] if pos != 0 else np.zeros(pos_emb_size) for pos in
                                                 range(max_sent_length)])
                        position_enc[1:, 0::2] = np.sin(position_enc[1:, 0::2])  # dim 2i
                        position_enc[1:, 1::2] = np.cos(position_enc[1:, 1::2])  # dim 2i+1
                        self.position_embedding.weight.data.copy_(torch.from_numpy(position_enc).type(torch.FloatTensor))
                        ##############################################################################
                #
                self.transformer = TransformerEncoder(self.encoder_layers,
                                                      d_model=d_model,
                                                      heads=num_head,
                                                      d_ff=trans_hid_size,
                                                      d_k=d_k,
                                                      d_v=d_v,
                                                      attn_drop=p_rnn[0],
                                                      relu_drop=p_rnn[1],
                                                      res_drop=p_rnn[2],
                                                      clip_dist=enc_clip_dist,
                                                      use_neg_dist=enc_use_neg_dist)

                enc_output_dim = d_model
            else:
                raise NotImplementedError()

        # self.rnn = RNN(dim_enc, hidden_size, num_layers=num_layers, batch_first=True, bidirectional=True, dropout=p_rnn)

        out_dim = enc_output_dim
        self.arc_h = nn.Linear(out_dim, arc_space)
        self.arc_c = nn.Linear(out_dim, arc_space)
        self.attention = BiAAttention(arc_space, arc_space, 1, biaffine=biaffine)

        self.type_h = nn.Linear(out_dim, type_space)
        self.type_c = nn.Linear(out_dim, type_space)
        self.bilinear = BiLinear(type_space, type_space, self.num_labels)

    def _get_rnn_output(self, input_word, input_char, input_pos, mask=None, length=None, hx=None):
        input = None

        if not self.no_word:
            # [batch, length, word_dim]
            word = self.word_embedd(input_word)
            # apply dropout on input
            word = self.dropout_in(word)

            input = word

        if self.char:
            # [batch, length, char_length, char_dim]
            char = self.char_embedd(input_char)
            char_size = char.size()
            # first transform to [batch *length, char_length, char_dim]
            # then transpose to [batch * length, char_dim, char_length]
            char = char.view(char_size[0] * char_size[1], char_size[2], char_size[3]).transpose(1, 2)
            # put into cnn [batch*length, char_filters, char_length]
            # then put into maxpooling [batch * length, char_filters]
            char, _ = self.conv1d(char).max(dim=2)
            # reshape to [batch, length, char_filters]
            char = torch.tanh(char).view(char_size[0], char_size[1], -1)
            # apply dropout on input
            char = self.dropout_in(char)
            # concatenate word and char [batch, length, word_dim+char_filter]
            input = char if input is None else torch.cat([input, char], dim=2)

        if self.pos:
            # [batch, length, pos_dim]
            pos = self.pos_embedd(input_pos)
            # # apply dropout on input
            # pos = self.dropout_in(pos)
            input = pos if input is None else torch.cat([input, pos], dim=2)

        # # output from rnn [batch, length, hidden_size]
        # output, hn = self.rnn(input, mask, hx=hx)

        if self.use_con_rnn:
            output, hn = self.rnn(input, mask, hx=hx)
        else:
            if self.multi_head_attn:
                src_encoding = input
                if self.position_dim > 0:
                    position_encoding = Variable(torch.arange(start=0, end=src_encoding.size(1)).type(torch.LongTensor))
                    # ----- modified by zs
                    if self.use_gpu:
                        position_encoding = position_encoding.cuda()
                    # -----
                    position_encoding = position_encoding.expand(*src_encoding.size()[:-1])
                    position_encoding = self.position_embedding(position_encoding)
                    # src_encoding = src_encoding + position_encoding
                    src_encoding = torch.cat([src_encoding, position_encoding], dim=2)
                src_encoding = self.transformer(src_encoding)
                output, hn = src_encoding, None
            else:
                raise NotImplementedError()

        # apply dropout for output
        # [batch, length, hidden_size] --> [batch, hidden_size, length] --> [batch, length, hidden_size]
        output = self.dropout_out(output.transpose(1, 2)).transpose(1, 2)

        # output size [batch, length, arc_space]
        arc_h = F.elu(self.arc_h(output))
        arc_c = F.elu(self.arc_c(output))

        # output size [batch, length, type_space]
        type_h = F.elu(self.type_h(output))
        type_c = F.elu(self.type_c(output))

        # apply dropout
        # [batch, length, dim] --> [batch, 2 * length, dim]
        arc = torch.cat([arc_h, arc_c], dim=1)
        type = torch.cat([type_h, type_c], dim=1)

        arc = self.dropout_out(arc.transpose(1, 2)).transpose(1, 2)
        arc_h, arc_c = arc.chunk(2, 1)

        type = self.dropout_out(type.transpose(1, 2)).transpose(1, 2)
        type_h, type_c = type.chunk(2, 1)
        type_h = type_h.contiguous()
        type_c = type_c.contiguous()

        return (arc_h, arc_c), (type_h, type_c), hn, mask, length

    def forward(self, input_word, input_char, input_pos, mask=None, length=None, hx=None):
        # output from rnn [batch, length, tag_space]
        arc, type, _, mask, length = self._get_rnn_output(input_word, input_char, input_pos, mask=mask, length=length,
                                                          hx=hx)
        # [batch, length, length]
        out_arc = self.attention(arc[0], arc[1], mask_d=mask, mask_e=mask).squeeze(dim=1)
        return out_arc, type, mask, length

    def loss(self, input_word, input_char, input_pos, heads, types, mask=None, length=None, hx=None):
        # out_arc shape [batch, length, length]
        out_arc, out_type, mask, length = self.forward(input_word, input_char, input_pos, mask=mask, length=length,
                                                       hx=hx)
        batch, max_len, _ = out_arc.size()

        if length is not None and heads.size(1) != mask.size(1):
            heads = heads[:, :max_len]
            types = types[:, :max_len]

        # out_type shape [batch, length, type_space]
        type_h, type_c = out_type

        # create batch index [batch]
        batch_index = torch.arange(0, batch).type_as(out_arc.data).long()
        # get vector for heads [batch, length, type_space],
        type_h = type_h[batch_index, heads.data.t()].transpose(0, 1).contiguous()
        # compute output for type [batch, length, num_labels]
        out_type = self.bilinear(type_h, type_c)

        # mask invalid position to -inf for log_softmax
        if mask is not None:
            minus_inf = -1e8
            minus_mask = (1 - mask) * minus_inf
            out_arc = out_arc + minus_mask.unsqueeze(2) + minus_mask.unsqueeze(1)

        # loss_arc shape [batch, length, length]
        loss_arc = F.log_softmax(out_arc, dim=1)
        # loss_type shape [batch, length, num_labels]
        loss_type = F.log_softmax(out_type, dim=2)

        # mask invalid position to 0 for sum loss
        if mask is not None:
            loss_arc = loss_arc * mask.unsqueeze(2) * mask.unsqueeze(1)
            loss_type = loss_type * mask.unsqueeze(2)
            # number of valid positions which contribute to loss (remove the symbolic head for each sentence.
            num = mask.sum() - batch
        else:
            # number of valid positions which contribute to loss (remove the symbolic head for each sentence.
            num = float(max_len - 1) * batch

        # first create index matrix [length, batch]
        child_index = torch.arange(0, max_len).view(max_len, 1).expand(max_len, batch)
        child_index = child_index.type_as(out_arc.data).long()
        # [length-1, batch]
        loss_arc = loss_arc[batch_index, heads.data.t(), child_index][1:]
        loss_type = loss_type[batch_index, child_index, types.data.t()][1:]

        return -loss_arc.sum() / num, -loss_type.sum() / num

    def _decode_types(self, out_type, heads, leading_symbolic):
        # out_type shape [batch, length, type_space]
        type_h, type_c = out_type
        batch, max_len, _ = type_h.size()
        # create batch index [batch]
        batch_index = torch.arange(0, batch).type_as(type_h.data).long()
        # get vector for heads [batch, length, type_space],
        type_h = type_h[batch_index, heads.t()].transpose(0, 1).contiguous()
        # compute output for type [batch, length, num_labels]
        out_type = self.bilinear(type_h, type_c)
        # remove the first #leading_symbolic types.
        out_type = out_type[:, :, leading_symbolic:]
        # compute the prediction of types [batch, length]
        _, types = out_type.max(dim=2)
        return types + leading_symbolic


    def decode(self, input_word, input_char, input_pos, mask=None, length=None, hx=None, leading_symbolic=0):
        # out_arc shape [batch, length, length]
        out_arc, out_type, mask, length = self.forward(input_word, input_char, input_pos, mask=mask, length=length,
                                                       hx=hx)
        out_arc = out_arc.data
        batch, max_len, _ = out_arc.size()
        # set diagonal elements to -inf
        out_arc = out_arc + torch.diag(out_arc.new(max_len).fill_(-np.inf))
        # set invalid positions to -inf
        if mask is not None:
            # minus_mask = (1 - mask.data).byte().view(batch, max_len, 1)
            minus_mask = (1 - mask.data).byte().unsqueeze(2)
            out_arc.masked_fill_(minus_mask, -np.inf)

        # compute naive predictions.
        # predition shape = [batch, length]
        _, heads = out_arc.max(dim=1)

        types = self._decode_types(out_type, heads, leading_symbolic)

        return heads.cpu().numpy(), types.data.cpu().numpy()

    def decode_mst(self, input_word, input_char, input_pos, mask=None, length=None, hx=None, leading_symbolic=0, constraints=None, method='Lagrange'):
        '''
        Args:
            input_word: Tensor
                the word input tensor with shape = [batch, length]
            input_char: Tensor
                the character input tensor with shape = [batch, length, char_length]
            input_pos: Tensor
                the pos input tensor with shape = [batch, length]
            mask: Tensor or None
                the mask tensor with shape = [batch, length]
            length: Tensor or None
                the length tensor with shape = [batch]
            hx: Tensor or None
                the initial states of RNN
            leading_symbolic: int
                number of symbolic labels leading in type alphabets (set it to 0 if you are not sure)

        Returns: (Tensor, Tensor)
                predicted heads and types.

        '''
        # out_arc shape [batch, length, length]
        out_arc, out_type, mask, length = self.forward(input_word, input_char, input_pos, mask=mask, length=length,
                                                       hx=hx)

        # out_type shape [batch, length, type_space]
        type_h, type_c = out_type
        batch, max_len, type_space = type_h.size()

        # compute lengths
        if length is None:
            if mask is None:
                length = [max_len for _ in range(batch)]
            else:
                length = mask.data.sum(dim=1).long().cpu().numpy()

        type_h = type_h.unsqueeze(2).expand(batch, max_len, max_len, type_space).contiguous()
        type_c = type_c.unsqueeze(1).expand(batch, max_len, max_len, type_space).contiguous()
        # compute output for type [batch, length, length, num_labels]
        out_type = self.bilinear(type_h, type_c)
        
        # mask invalid position to -inf for log_softmax
        if mask is not None:
            minus_inf = -1e8
            minus_mask = (1 - mask) * minus_inf
            out_arc = out_arc + minus_mask.unsqueeze(2) + minus_mask.unsqueeze(1)

        # loss_arc shape [batch, length, length]
        loss_arc = F.log_softmax(out_arc, dim=1)
        # loss_type shape [batch, length, length, num_labels]
        loss_type = F.log_softmax(out_type, dim=3).permute(0, 3, 1, 2)
        # [batch, num_labels, length, length]
        if method == 'Lagrange':
	    if constraints is not None:
                for constraint in constraints:
                    loss_arc = self.apply_constraints(loss_arc, input_pos, constraint, method)
        #energy = torch.exp(loss_arc.unsqueeze(1) + loss_type)
        energy = loss_arc.unsqueeze(1) + loss_type
        return parser.decode_MST(energy.data.cpu().numpy(), length, leading_symbolic=leading_symbolic, labeled=True)
    
    def decode_proj(self, input_word, input_char, input_pos, mask=None, length=None, hx=None, leading_symbolic=0, constraints=None, method='Lagrange'):
        '''
        Args:
            input_word: Tensor
                the word input tensor with shape = [batch, length]
            input_char: Tensor
                the character input tensor with shape = [batch, length, char_length]
            input_pos: Tensor
                the pos input tensor with shape = [batch, length]
            mask: Tensor or None
                the mask tensor with shape = [batch, length]
            length: Tensor or None
                the length tensor with shape = [batch]
            hx: Tensor or None
                the initial states of RNN
            leading_symbolic: int
                number of symbolic labels leading in type alphabets (set it to 0 if you are not sure)

        Returns: (Tensor, Tensor)
                predicted heads and types.

        '''
        # out_arc shape [batch, length, length]
        out_arc, out_type, mask, length = self.forward(input_word, input_char, input_pos, mask=mask, length=length,
                                                       hx=hx)

        # out_type shape [batch, length, type_space]
        type_h, type_c = out_type
        batch, max_len, type_space = type_h.size()

        # compute lengths
        if length is None:
            if mask is None:
                length = [max_len for _ in range(batch)]
            else:
                length = mask.data.sum(dim=1).long().cpu().numpy()

        type_h = type_h.unsqueeze(2).expand(batch, max_len, max_len, type_space).contiguous()
        type_c = type_c.unsqueeze(1).expand(batch, max_len, max_len, type_space).contiguous()
        # compute output for type [batch, length, length, num_labels]
        out_type = self.bilinear(type_h, type_c)
	if method == 'binary':
            if constraints is not None:
                for constraint in constraints:
                    out_arc = self.apply_constraints(out_arc, input_pos, constraint, method)
        
        # mask invalid position to -inf for log_softmax
        if mask is not None:
            minus_inf = -1e8
            minus_mask = (1 - mask) * minus_inf
            out_arc = out_arc + minus_mask.unsqueeze(2) + minus_mask.unsqueeze(1)

        # loss_arc shape [batch, length, length]
        loss_arc = F.log_softmax(out_arc, dim=1)
        # loss_type shape [batch, length, length, num_labels]
        loss_type = F.log_softmax(out_type, dim=3).permute(0, 3, 1, 2)
        # [batch, num_labels, length, length]
        if method == 'Lagrange' or method == 'PR':
	    if constraints is not None:
                for constraint in constraints:
                    loss_arc = self.apply_constraints(loss_arc, input_pos, constraint, method)
        #energy = torch.exp(loss_arc.unsqueeze(1) + loss_type)
        energy = loss_arc.unsqueeze(1) + loss_type
        return parser.decode_proj(energy.data.cpu().numpy(), length, leading_symbolic=leading_symbolic, labeled=True)

    def pretrain_constraint(self, input_word, input_char, input_pos, mask=None, length=None, hx=None, leading_symbolic=0):
        out_arc, out_type, mask, length = self.forward(input_word, input_char, input_pos, mask=mask, length=length,
                                                       hx=hx)
        type_h, type_c = out_type
        batch, max_len, type_space = type_h.size()

        if length is None:
            if mask is None:
                length = [max_len for _ in range(batch)]
            else:
                length = mask.data.sum(dim=1).long().cpu().numpy()

        type_h = type_h.unsqueeze(2).expand(batch, max_len, max_len, type_space).contiguous()
        type_c = type_c.unsqueeze(1).expand(batch, max_len, max_len, type_space).contiguous()
        out_type = self.bilinear(type_h, type_c)

        if mask is not None:
            minus_inf = -1e8
            minus_mask = (1 - mask) * minus_inf
            out_arc = out_arc + minus_mask.unsqueeze(2) + minus_mask.unsqueeze(1)

        return out_arc, out_type, length

    def PR_constraints(self, out_arc, out_type, length, pos, constraints, tolerance, mt_log):
        N = len(out_arc)
        temp = np.zeros(1, dtype='uint8')
        M = len(constraints)
        total = [0] * M
        sat_con = [0] * M
        ratio = [0.0] * M
        #First pass to decide the constraints directions
        for i in range(N):
            loss_arc = F.log_softmax(out_arc[i].unsqueeze(0), dim = 1)
            loss_type = F.log_softmax(out_type[i], dim = 2).permute(2, 0, 1).unsqueeze(0)
            energy = torch.exp(loss_arc.unsqueeze(0) + loss_type)
            temp[0] = length[i]
            my_par, my_type = parser.decode_proj(energy.data.cpu().numpy(), temp, labeled=True)
            for idx, constraint in enumerate(constraints):
                tot, con = constraint.count(my_par[0], pos[i], length[i])
                total[idx] += tot
                sat_con[idx] += con
        print ("Number of Instance: %d\n"%(N)) 
        for i, constraint in enumerate(constraints):
            ratio[i] = float(sat_con[i]) / total[i]
            if ratio[i] < constraint.ratio:
                constraint.direction = -1
            else:
                constraint.direction = 1
            constraint.output()
        #apply gradient descent to find the lambda
        learning_rate = 1e-5
        lr_decay = 0.9
        while learning_rate > 1e-6:
            logZ = 0.0
            gradientZ = [0.0] * M
            for i in range(N):
                loss_arc = F.log_softmax(out_arc[i], dim = 0)
                loss_type = F.log_softmax(out_type[i], dim = 2).permute(2, 0, 1)
                score_matrix = loss_arc.data.cpu().numpy()
                #print (score_matrix.shape, length[i])
                for j in range(length[i]):
                    sum0 = 0.0
                    sum1 = [0.0] * M
                    for k in range(length[i]):
                        if j == k:
                            sum0 += math.exp(score_matrix[k, k])
                            continue
                        temp = score_matrix[k, j]
                        #print ("score_matrix=%f\n"%(score_matrix[j, k]))
                        for constraint in constraints:
                            temp -= constraint.PROffset(constraint.pair_count(pos[i].data[j], pos[i].data[k], j, k))
                        #print ("temp=%f\n"%(temp))
                        for idx, constraint in enumerate(constraints):
                            sum1[idx] -= constraint.PRFunction(constraint.pair_count(pos[i].data[j], pos[i].data[k], j, k)) * math.exp(temp)
                        sum0 += math.exp(temp)
                    for idx in range(M):
                        gradientZ[idx] += sum1[idx] / sum0
                    #print ("sum0=%.4f"%(sum0))
                    logZ += math.log(sum0)
            print (logZ)
            for idx, constraint in enumerate(constraints):
                gradientZ[idx] *= math.exp(logZ)
                constraint.weightFactor -= gradientZ[idx] * learning_rate
                if constraint.weightFactor < 0:
                    constraint.weightFactor = 0
            print (gradientZ)
            learning_rate *= lr_decay

    def Lagrange_constraints(self, out_arc, out_type, length, pos, constraints, tolerance, mt_log):
        temp = np.zeros(1, dtype='uint8')
        N = len(out_arc)
        alpha = 50.0
        M = len(constraints)
        while alpha > 0.5:
            total = [0] * M
            sat_con = [0] * M
            ratio = [0.0] * M
            for i in range(N):
                loss_arc = F.log_softmax(out_arc[i].unsqueeze(0), dim = 1)
                loss_type = F.log_softmax(out_type[i], dim = 2).permute(2, 0, 1).unsqueeze(0)
                for constraint in constraints:
                    loss_arc = self.apply_constraints(loss_arc, pos[i].unsqueeze(0), constraint, method='Lagrange')
                #energy = torch.exp(loss_arc.unsqueeze(0) + loss_type)
                energy = loss_arc.unsqueeze(0) + loss_type
                temp[0] = length[i]
                my_par, my_type = parser.decode_proj(energy.data.cpu().numpy(), temp, labeled=True)
                for idx, constraint in enumerate(constraints):
                    tot, con = constraint.count(my_par[0], pos[i], length[i])
                    total[idx] += tot
                    sat_con[idx] += con
            flag = True
            for i, constraint in enumerate(constraints):
                ratio[i] = float(sat_con[i]) / total[i]
                if abs(ratio[i] - constraint.ratio) > tolerance:
                    flag = False
                constraint.output(ratio[i])
                #constraint.weightFactor += alpha * (constraint.ratio - ratio[i])
            if alpha > 49:
                constraint.output_to_file(mt_log, ratio[i])
            if flag:
                mt_log.write("Convergence.\n")
                for i, constraint in enumerate(constraints):
                    constraint.output_to_file(mt_log, ratio[i])
                return True
            for i, constraint in enumerate(constraints):
                constraint.weightFactor += alpha * (constraint.ratio - ratio[i])
            alpha *= 0.9 
        mt_log.write("Non-Convergence.\n")
        for i, constraint in enumerate(constraints):
            constraint.output_to_file(mt_log, ratio[i])
        return False
    
    def binary_constraints(self, out_arc, out_type, length, pos, constraints, tolerance, mt_log):
        N = 10
	for i in range(N):
            flag = True
            for constraint in constraints:
                if not self.train_constraint(out_arc, out_type, length, pos, constraint, tolerance, mt_log):
                    flag = False
            if flag:
                return True
        return False
                

    def train_constraint(self, out_arc, out_type, length, pos, constraint, tolerance, mt_log):
        if constraint.ratio == 0:
            constraint.weightFactor = -1e+8
            return
        N = len(out_arc)
        ws = 1e+1
        total_weightShift = constraint.weightFactor
        constraint.weightFactor = 0
	temp = np.zeros(1, dtype='uint8')
        while ws > 1e-3:
            total = 0
            sat_con = 0
            for i in range(N):
                loss_arc = F.log_softmax(self.apply_constraints(out_arc[i].unsqueeze(0), pos[i].unsqueeze(0), constraint), dim = 1)
                #loss_arc = F.log_softmax(out_arc[i].unsqueeze(0), dim = 1)
                loss_type = F.log_softmax(out_type[i], dim = 2).permute(2, 0, 1).unsqueeze(0)
                energy = torch.exp(loss_arc.unsqueeze(0) + loss_type)
                temp[0] = length[i]
                my_par, my_type = parser.decode_proj(energy.data.cpu().numpy(), temp, labeled=True)
                tot, con = constraint.count(my_par[0], pos[i], length[i])
                total += tot
                sat_con += con
            ratio = float(sat_con) / total
            if ws > 9.0:
                constraint.output_to_file(mt_log, ratio)
            if abs(ratio - constraint.ratio) < tolerance and constraint.weightFactor < 1e-7:
                constraint.weightFactor = total_weightShift
                print("Satisfied, skiped")
                return True
            if abs(ratio - constraint.ratio) < 0.5 * tolerance:
                constraint.weightFactor = total_weightShift
                print("Satisfied, finished")
                return False
            if ratio < constraint.ratio:
                constraint.weightFactor = ws
                total_weightShift += ws
            else:
                constraint.weightFactor = -ws
                total_weightShift -= ws
            ws /= 2.0
            print(total, sat_con, ratio, total_weightShift)
        constraint.weighFactor = total_weightShift
        return False

    def train_constraint2(self, out_arc, out_type, length, pos, constraint):
        if constraint.ratio == 0:
            constraint.weightFactor = -1e+8
            return
        N = len(out_arc)
        ws = 1e+1
        total_weightShift = 0
	temp = np.zeros(1, dtype='uint8')
        while ws > 1e-3:
            total = 0
            sat_con = 0
            for i in range(N):
                loss_arc = F.log_softmax(out_arc[i].unsqueeze(0), dim = 1)
                loss_type = F.log_softmax(out_type[i], dim = 2).permute(2, 0, 1).unsqueeze(0)
                loss_arc = self.apply_constraints(loss_arc, pos[i].unsqueeze(0), constraint)
                energy = torch.exp(loss_arc.unsqueeze(0) + loss_type)
                temp[0] = length[i]
                my_par, my_type = parser.decode_proj(energy.data.cpu().numpy(), temp, labeled=True)
                tot, con = constraint.count(my_par[0], pos[i], length[i])
                total += tot
                sat_con += con
            ratio = float(sat_con) / total
            if ratio < constraint.ratio:
                constraint.weightFactor += ws
                total_weightShift += ws
            else:
                constraint.weightFactor += -ws
                total_weightShift -= ws
            ws /= 2.0
            print(total, sat_con, ratio, total_weightShift)
        constraint.Factor = total_weightShift
    
    def apply_constraints(self, arc, pos, constraint, method='Lagrange'):
        #print ("The shapes:", arc.shape, pos.shape, constraints)
        batch = arc.shape[0]
        length = arc.shape[1]
        for i in range(batch):
            for j in range(length - 1):
                for k in range(j + 1, length):
                    #print(pos1, pos2)
                    '''
                    if method == 'Lagrange':
                        if constraint.leftPos == constraint.rightPos:
                            if pos.data[i, j] == constraint.leftPos:
                                arc.data[i, k, j] = arc.data[i, k, j] + constraint.LagrangePos()
                            if pos.data[i, k] == constraint.leftPos:
                                arc.data[i, j, k] = arc.data[i, j, k] + constraint.LagrangeNeg()
                            continue
                        if pos.data[i, j] == constraint.leftPos and pos.data[i, k] == constraint.rightPos:
                            arc.data[i, j, k] = arc.data[i, j, k] + constraint.LagrangePos()
                            arc.data[i, k, j] = arc.data[i, k, j] + constraint.LagrangePos()
                        if pos.data[i, j] == constraint.rightPos and pos.data[i, k] == constraint.leftPos:
                            arc.data[i, j, k] = arc.data[i, j, k] + constraint.LagrangeNeg()
                            arc.data[i, k, j] = arc.data[i, k, j] + constraint.LagrangeNeg()
                        continue
                    '''
                    if method == 'Lagrange':
                        arc.data[i, k, j] = arc.data[i, k, j] + constraint.LagrangeOffset(constraint.pair_count(pos.data[i, j], pos.data[i, k], j, k))
                        arc.data[i, j, k] = arc.data[i, j, k] + constraint.LagrangeOffset(constraint.pair_count(pos.data[i, k], pos.data[i, j], k, j))
                        continue

                    if method == 'PR':
                        arc.data[i, k, j] = arc.data[i, k, j] + constraint.PROffset(constraint.pair_count(pos.data[i, j], pos.data[i, k], j, k))
                        arc.data[i, j, k] = arc.data[i, j, k] + constraint.PROffset(constraint.pair_count(pos.data[i, k], pos.data[i, j], k, j))
                        continue

                    if constraint.leftPos == constraint.rightPos:
                        if pos.data[i, j] == constraint.leftPos:
                            arc.data[i, k, j] = arc.data[i, k, j] + constraint.weightFactor
                        continue
                    if pos.data[i, j] == constraint.leftPos and pos.data[i, k] == constraint.rightPos:
                        #print (arc[i,j,k], arc[i,k,j])
                        arc.data[i, j, k] = arc.data[i, j, k] + constraint.weightFactor
                        arc.data[i, k, j] = arc.data[i, k, j] + constraint.weightFactor
                        #print (arc[i,j,k], arc[i,k,j])
        return arc

class StackPtrNet(nn.Module):
    def __init__(self, word_dim, num_words, char_dim, num_chars, pos_dim, num_pos, num_filters, kernel_size,
                 rnn_mode, input_size_decoder, hidden_size, encoder_layers, decoder_layers, num_labels, arc_space,
                 type_space, pool_type, multi_head_attn, num_head, max_sent_length, trans_hid_size, d_k, d_v,
                 train_position=False, embedd_word=None, embedd_char=None, embedd_pos=None, p_in=0.33, p_out=0.33,
                 p_rnn=(0.33, 0.33), biaffine=True, use_word_emb=True, pos=True, char=True, prior_order='inside_out',
                 skipConnect=False, use_con_rnn=True, grandPar=False, sibling=False, use_gpu=False,
                 dec_max_dist=0, dec_use_neg_dist=False, dec_use_encoder_pos=False, dec_use_decoder_pos=False,
                 dec_dim_feature=10, dec_drop_f_embed=0.,
                 enc_clip_dist=0, enc_use_neg_dist=False,
                 input_concat_embeds=False, input_concat_position=False, position_dim=50):

        super(StackPtrNet, self).__init__()
        self.word_embedd = Embedding(num_words, word_dim, init_embedding=embedd_word) if use_word_emb else None
        self.pos_embedd = Embedding(num_pos, pos_dim, init_embedding=embedd_pos) if pos else None
        self.char_embedd = Embedding(num_chars, char_dim, init_embedding=embedd_char) if char else None
        self.conv1d = nn.Conv1d(char_dim, num_filters, kernel_size, padding=kernel_size - 1) if char else None
        self.dropout_in = nn.Dropout2d(p=p_in)
        self.dropout_out = nn.Dropout2d(p=p_out)
        self.num_labels = num_labels
        if prior_order in ['deep_first', 'shallow_first']:
            self.prior_order = PriorOrder.DEPTH
        elif prior_order == 'inside_out':
            self.prior_order = PriorOrder.INSIDE_OUT
        elif prior_order == 'left2right':
            self.prior_order = PriorOrder.LEFT2RIGTH
        else:
            raise ValueError('Unknown prior order: %s' % prior_order)
        self.pos = pos
        self.char = char
        self.use_word_emb = use_word_emb
        self.use_con_rnn = use_con_rnn
        self.multi_head_attn = multi_head_attn
        self.pool_type = pool_type
        self.skipConnect = skipConnect
        self.grandPar = grandPar
        self.sibling = sibling
        #
        self.input_concat_embeds = input_concat_embeds
        self.input_concat_position = input_concat_position
        self.position_dim = position_dim

        if rnn_mode == 'RNN':
            RNN_ENCODER = VarMaskedRNN
            RNN_DECODER = SkipConnectRNN if skipConnect else VarMaskedRNN
        elif rnn_mode == 'LSTM':
            RNN_ENCODER = VarMaskedLSTM
            RNN_DECODER = SkipConnectLSTM if skipConnect else VarMaskedLSTM
        elif rnn_mode == 'FastLSTM':
            RNN_ENCODER = VarMaskedFastLSTM
            RNN_DECODER = SkipConnectFastLSTM if skipConnect else VarMaskedFastLSTM
        elif rnn_mode == 'GRU':
            RNN_ENCODER = VarMaskedGRU
            RNN_DECODER = SkipConnectGRU if skipConnect else VarMaskedGRU
        else:
            raise ValueError('Unknown RNN mode: %s' % rnn_mode)

        # embed
        dim_enc = 0
        if use_word_emb:
            dim_enc = word_dim
        if pos:
            dim_enc = dim_enc + pos_dim if input_concat_embeds else pos_dim
        if char:
            dim_enc = dim_enc + num_filters if input_concat_embeds else num_filters

        # enc
        self.encoder_layers = encoder_layers
        if self.use_con_rnn:
            self.encoder = RNN_ENCODER(dim_enc, hidden_size, num_layers=encoder_layers, batch_first=True,
                                       bidirectional=True, dropout=p_rnn)
            enc_output_dim = 2 * hidden_size
        else:
            if self.multi_head_attn:
                # pos_emb_size = 0
                # if self.use_word_emb:
                #     # pos_emb_size += word_dim
                #     pos_emb_size = word_dim
                # if self.char:
                #     # pos_emb_size += char_dim
                #     pos_emb_size = char_dim
                # if self.pos:
                #     # pos_emb_size += pos_dim
                #     pos_emb_size = pos_dim

                pos_emb_size = position_dim
                if input_concat_position:
                    d_model = pos_emb_size + dim_enc
                else:
                    d_model = dim_enc

                if position_dim > 0:
                    self.position_embedding = nn.Embedding(max_sent_length, pos_emb_size)
                    if not train_position:
                        self.position_embedding.weight.requires_grad = False  # turn off pos embedding training
                        ######################### init positional embedding ##########################
                        # keep dim 0 for padding token position encoding zero vector
                        position_enc = np.array([[pos / np.power(10000, 2 * (j // 2) / pos_emb_size) for j in
                                                  range(pos_emb_size)] if pos != 0 else np.zeros(pos_emb_size) for pos in
                                                 range(max_sent_length)])
                        position_enc[1:, 0::2] = np.sin(position_enc[1:, 0::2])  # dim 2i
                        position_enc[1:, 1::2] = np.cos(position_enc[1:, 1::2])  # dim 2i+1
                        self.position_embedding.weight.data.copy_(torch.from_numpy(position_enc).type(torch.FloatTensor))
                        ##############################################################################

                self.transformer = TransformerEncoder(self.encoder_layers,
                                                      d_model=d_model,
                                                      heads=num_head,
                                                      d_ff=trans_hid_size,
                                                      d_k=d_k,
                                                      d_v=d_v,
                                                      attn_drop=p_rnn[0],
                                                      relu_drop=p_rnn[1],
                                                      res_drop=p_rnn[2],
                                                      clip_dist=enc_clip_dist,
                                                      use_neg_dist=enc_use_neg_dist)

                enc_output_dim = d_model

            else:
                self.linear1 = nn.Linear(dim_enc, dim_enc)
                enc_output_dim = dim_enc

            if self.pool_type == 'weight':
                self.self_attn = nn.Linear(enc_output_dim, 1)

        # dec
        dim_dec = input_size_decoder
        self.src_dense = nn.Linear(enc_output_dim, dim_dec)

        self.decoder_layers = decoder_layers
        drop_rnn = p_rnn[:2] if self.multi_head_attn else p_rnn
        self.decoder = RNN_DECODER(dim_dec, hidden_size, num_layers=decoder_layers, batch_first=True,
                                   bidirectional=False, dropout=drop_rnn)

        self.hx_dense = nn.Linear(enc_output_dim, hidden_size)
        self.arc_h = nn.Linear(hidden_size, arc_space)  # arc dense for decoder
        self.arc_c = nn.Linear(enc_output_dim, arc_space)  # arc dense for encoder

        # AugAttentioner (with dist/pos features included)
        # self.attention = BiAAttention(arc_space, arc_space, 1, biaffine=biaffine)
        self.attention_helper = AugFeatureHelper(dec_max_dist, dec_use_neg_dist, num_pos, dec_use_encoder_pos,
                                                 dec_use_decoder_pos)
        self.attention = AugBiAAttention(arc_space, arc_space, 1, num_features=self.attention_helper.get_num_features(),
                                         dim_feature=dec_dim_feature, drop_f_embed=dec_drop_f_embed, biaffine=biaffine)

        self.type_h = nn.Linear(hidden_size, type_space)  # type dense for decoder
        self.type_c = nn.Linear(enc_output_dim, type_space)  # type dense for encoder
        self.bilinear = BiLinear(type_space, type_space, self.num_labels)

        # ----- modified by zs (used for position inputs)
        self.use_gpu = use_gpu

    def _get_encoder_output(self, input_word, input_char, input_pos, mask_e=None, length_e=None, hx=None):
        src_encoding = None
        if self.use_word_emb:
            # [batch, length, word_dim]
            word = self.word_embedd(input_word)
            # apply dropout on input
            word = self.dropout_in(word)
            src_encoding = word

        if self.char:
            # [batch, length, char_length, char_dim]
            char = self.char_embedd(input_char)
            char_size = char.size()
            # first transform to [batch *length, char_length, char_dim]
            # then transpose to [batch * length, char_dim, char_length]
            char = char.view(char_size[0] * char_size[1], char_size[2], char_size[3]).transpose(1, 2)
            # put into cnn [batch*length, char_filters, char_length]
            # then put into maxpooling [batch * length, char_filters]
            char, _ = self.conv1d(char).max(dim=2)
            # reshape to [batch, length, char_filters]
            char = torch.tanh(char).view(char_size[0], char_size[1], -1)
            # apply dropout on input
            char = self.dropout_in(char)
            # concatenate word and char [batch, length, word_dim+char_filter]
            if src_encoding is None:
                src_encoding = char
            else:
                src_encoding = torch.cat([src_encoding, char], dim=2) if self.input_concat_embeds \
                    else src_encoding + char

        if self.pos:
            # [batch, length, pos_dim]
            pos = self.pos_embedd(input_pos)
            # apply dropout on input
            if self.use_con_rnn:
                pos = self.dropout_in(pos)

            if src_encoding is None:
                src_encoding = pos
            else:
                src_encoding = torch.cat([src_encoding, pos], dim=2) if self.input_concat_embeds \
                    else src_encoding + pos

        if self.use_con_rnn:
            # output from rnn [batch, length, hidden_size]
            output, hn = self.encoder(src_encoding, mask_e, hx=hx)
        else:
            if self.multi_head_attn:
                # padding_idx = 1
                # words = src_encoding[:, :, 0]
                # w_batch, w_len = words.size()
                # mask = words.data.eq(padding_idx).unsqueeze(1).expand(w_batch, w_len, w_len)
                # Run the forward pass of every layer of the tranformer.

                if self.position_dim > 0:
                    position_encoding = Variable(torch.arange(start=0, end=src_encoding.size(1)).type(torch.LongTensor))
                    # ----- modified by zs
                    if self.use_gpu:
                        position_encoding = position_encoding.cuda()
                    # -----
                    position_encoding = position_encoding.expand(*src_encoding.size()[:-1])
                    position_encoding = self.position_embedding(position_encoding)
                    # src_encoding = src_encoding + position_encoding
                    src_encoding = torch.cat([src_encoding, position_encoding], dim=2) if self.input_concat_position \
                        else src_encoding + position_encoding
                src_encoding = self.transformer(src_encoding)
            else:
                # if we want to apply self-attention to compute the fixed-length vector
                hw = self.linear1(src_encoding.view(-1, src_encoding.size(2)))  # (B*S) x h
                hw = hw.view(*src_encoding.size())  # B x S x h
                attn_weights = torch.bmm(src_encoding, hw.transpose(1, 2))  # B x S x S
                attn_weights = F.softmax(attn_weights, dim=2)  # B x S x S
                src_encoding = torch.bmm(attn_weights, src_encoding)  # B x S x h

            if self.pool_type == 'mean':
                # if we want to use averaging to compute the fixed-length vector
                temp_hidden = torch.sum(src_encoding, 1).div(src_encoding.size(1)).unsqueeze(0)
                output, hn = src_encoding, (temp_hidden, torch.zeros_like(temp_hidden))
            elif self.pool_type == 'max':
                # if we want to use max-pooling to compute the fixed-length vector
                temp_hidden = torch.max(src_encoding, dim=1)[0].unsqueeze(0)
                output, hn = src_encoding, (temp_hidden, torch.zeros_like(temp_hidden))
            elif self.pool_type == 'weight':
                # if we want to apply weighted-pooling to compute the fixed-length vector
                att_weights = self.self_attn(src_encoding.view(-1, src_encoding.size(2))).squeeze(1)
                att_weights = F.softmax(att_weights.view(src_encoding.size(0), src_encoding.size(1)), 1)
                attn_rep = torch.bmm(src_encoding.transpose(1, 2), att_weights.unsqueeze(2)).squeeze(2)
                attn_rep = attn_rep.unsqueeze(0)
                output, hn = src_encoding, (attn_rep, torch.zeros_like(attn_rep))

        # apply dropout
        # [batch, length, hidden_size] --> [batch, hidden_size, length] --> [batch, length, hidden_size]
        output = self.dropout_out(output.transpose(1, 2)).transpose(1, 2)

        return output, hn, mask_e, length_e

    def _get_decoder_output(self, output_enc, heads, heads_stack, siblings, hx, mask_d=None, length_d=None):
        batch, _, _ = output_enc.size()
        # create batch index [batch]
        batch_index = torch.arange(0, batch).type_as(output_enc.data).long()
        # get vector for heads [batch, length_decoder, input_dim],
        src_encoding = output_enc[batch_index, heads_stack.data.t()].transpose(0, 1)

        if self.sibling:
            # [batch, length_decoder, hidden_size * 2]
            mask_sibs = siblings.ne(0).float().unsqueeze(2)
            output_enc_sibling = output_enc[batch_index, siblings.data.t()].transpose(0, 1) * mask_sibs
            src_encoding = src_encoding + output_enc_sibling

        if self.grandPar:
            # [length_decoder, batch]
            gpars = heads[batch_index, heads_stack.data.t()].data
            # [batch, length_decoder, hidden_size * 2]
            output_enc_gpar = output_enc[batch_index, gpars].transpose(0, 1)
            src_encoding = src_encoding + output_enc_gpar

        # transform to decoder input
        # [batch, length_decoder, dec_dim]
        src_encoding = F.elu(self.src_dense(src_encoding))

        # output from rnn [batch, length, hidden_size]
        output, hn = self.decoder(src_encoding, mask_d, hx=hx)

        # apply dropout
        # [batch, length, hidden_size] --> [batch, hidden_size, length] --> [batch, length, hidden_size]
        output = self.dropout_out(output.transpose(1, 2)).transpose(1, 2)

        return output, hn, mask_d, length_d

    def _get_decoder_output_with_skip_connect(self, output_enc, heads, heads_stack, siblings, skip_connect, hx,
                                              mask_d=None, length_d=None):
        batch, _, _ = output_enc.size()
        # create batch index [batch]
        batch_index = torch.arange(0, batch).type_as(output_enc.data).long()
        # get vector for heads [batch, length_decoder, input_dim],
        src_encoding = output_enc[batch_index, heads_stack.data.t()].transpose(0, 1)

        if self.sibling:
            # [batch, length_decoder, hidden_size * 2]
            mask_sibs = siblings.ne(0).float().unsqueeze(2)
            output_enc_sibling = output_enc[batch_index, siblings.data.t()].transpose(0, 1) * mask_sibs
            src_encoding = src_encoding + output_enc_sibling

        if self.grandPar:
            # [length_decoder, batch]
            gpars = heads[batch_index, heads_stack.data.t()].data
            # [batch, length_decoder, hidden_size * 2]
            output_enc_gpar = output_enc[batch_index, gpars].transpose(0, 1)
            src_encoding = src_encoding + output_enc_gpar

        # transform to decoder input
        # [batch, length_decoder, dec_dim]
        src_encoding = F.elu(self.src_dense(src_encoding))

        # output from rnn [batch, length, hidden_size]
        output, hn = self.decoder(src_encoding, skip_connect, mask_d, hx=hx)

        # apply dropout
        # [batch, length, hidden_size] --> [batch, hidden_size, length] --> [batch, length, hidden_size]
        output = self.dropout_out(output.transpose(1, 2)).transpose(1, 2)

        return output, hn, mask_d, length_d

    def forward(self, input_word, input_char, input_pos, mask=None, length=None, hx=None):
        raise RuntimeError('Stack Pointer Network does not implement forward')

    def _transform_decoder_init_state(self, hn):
        if isinstance(hn, tuple):
            if self.use_con_rnn:
                hn, cn = hn
                # take the last layers
                # [2, batch, hidden_size]
                cn = cn[-2:]
                # hn [2, batch, hidden_size]
                _, batch, hidden_size = cn.size()
                # first convert cn t0 [batch, 2, hidden_size]
                cn = cn.transpose(0, 1).contiguous()
                # then view to [batch, 1, 2 * hidden_size] --> [1, batch, 2 * hidden_size]
                cn = cn.view(batch, 1, 2 * hidden_size).transpose(0, 1)
            else:
                cn, hn = hn

            # take hx_dense to [1, batch, hidden_size]
            cn = self.hx_dense(cn)
            # [decoder_layers, batch, hidden_size]
            if self.decoder_layers > 1:
                cn = torch.cat([cn, Variable(cn.data.new(self.decoder_layers - 1, batch, hidden_size).zero_())], dim=0)
            # hn is tanh(cn)
            hn = F.tanh(cn)
            hn = (hn, cn)
        else:
            # take the last layers
            # [2, batch, hidden_size]
            hn = hn[-2:]
            # hn [2, batch, hidden_size]
            _, batch, hidden_size = hn.size()
            # first convert hn t0 [batch, 2, hidden_size]
            hn = hn.transpose(0, 1).contiguous()
            # then view to [batch, 1, 2 * hidden_size] --> [1, batch, 2 * hidden_size]
            if self.use_con_rnn:
                hn = hn.view(batch, 1, 2 * hidden_size).transpose(0, 1)
            else:
                hn = hn.view(batch, 1, hidden_size).transpose(0, 1)
            # take hx_dense to [1, batch, hidden_size]
            hn = F.tanh(self.hx_dense(hn))
            # [decoder_layers, batch, hidden_size]
            if self.decoder_layers > 1:
                hn = torch.cat([hn, Variable(hn.data.new(self.decoder_layers - 1, batch, hidden_size).zero_())], dim=0)
        return hn

    def loss(self, input_word, input_char, input_pos, heads, stacked_heads, children, siblings, stacked_types,
             label_smooth,
             skip_connect=None, mask_e=None, length_e=None, mask_d=None, length_d=None, hx=None):
        # output from encoder [batch, length_encoder, tag_space]
        output_enc, hn, mask_e, _ = self._get_encoder_output(input_word, input_char, input_pos, mask_e=mask_e,
                                                             length_e=length_e, hx=hx)

        # output size [batch, length_encoder, arc_space]
        arc_c = F.elu(self.arc_c(output_enc))
        # output size [batch, length_encoder, type_space]
        type_c = F.elu(self.type_c(output_enc))

        # transform hn to [decoder_layers, batch, hidden_size]
        hn = self._transform_decoder_init_state(hn)

        # output from decoder [batch, length_decoder, tag_space]
        if self.skipConnect:
            output_dec, _, mask_d, _ = self._get_decoder_output_with_skip_connect(output_enc, heads, stacked_heads,
                                                                                  siblings, skip_connect, hn,
                                                                                  mask_d=mask_d, length_d=length_d)
        else:
            output_dec, _, mask_d, _ = self._get_decoder_output(output_enc, heads, stacked_heads, siblings, hn,
                                                                mask_d=mask_d, length_d=length_d)

        # output size [batch, length_decoder, arc_space]
        arc_h = F.elu(self.arc_h(output_dec))
        type_h = F.elu(self.type_h(output_dec))

        _, max_len_d, _ = arc_h.size()
        if mask_d is not None and children.size(1) != mask_d.size(1):
            stacked_heads = stacked_heads[:, :max_len_d]
            children = children[:, :max_len_d]
            stacked_types = stacked_types[:, :max_len_d]

        # apply dropout
        # [batch, length_decoder, dim] + [batch, length_encoder, dim] --> [batch, length_decoder + length_encoder, dim]
        arc = self.dropout_out(torch.cat([arc_h, arc_c], dim=1).transpose(1, 2)).transpose(1, 2)
        arc_h = arc[:, :max_len_d]
        arc_c = arc[:, max_len_d:]

        type = self.dropout_out(torch.cat([type_h, type_c], dim=1).transpose(1, 2)).transpose(1, 2)
        type_h = type[:, :max_len_d].contiguous()
        type_c = type[:, max_len_d:]

        # [batch, length_decoder, length_encoder]
        if self.attention.use_features:
            batch, max_len_e, _ = arc_c.size()
            batch_index = torch.arange(0, batch).type_as(arc_c.data).long()
            child_pos = input_pos  # [batch, len-e]
            head_pos = input_pos[batch_index, stacked_heads.data.t()].transpose(0, 1)  # [batch, len-d]
            child_position_idxes = torch.arange(max_len_e).type_as(arc_c.data).long().expand(batch, -1).unsqueeze(
                -2)  # [batch, 1, len-e]
            head_position_idxes = stacked_heads.unsqueeze(-1)  # [batch, len-d, 1]
            raw_distances = head_position_idxes.expand(-1, -1, child_position_idxes.size()[
                -1]).data - child_position_idxes.expand(-1, head_position_idxes.size()[-2], -1)  # [batch, len-d, len-e]
            input_features = self.attention_helper.get_final_features(raw_distances, child_pos.data, head_pos.data)
        else:
            input_features = None
        out_arc = self.attention(arc_h, arc_c, input_features=input_features, mask_d=mask_d, mask_e=mask_e).squeeze(
            dim=1)

        batch, max_len_e, _ = arc_c.size()
        # create batch index [batch]
        batch_index = torch.arange(0, batch).type_as(arc_c.data).long()
        # get vector for heads [batch, length_decoder, type_space],
        type_c = type_c[batch_index, children.data.t()].transpose(0, 1).contiguous()
        # compute output for type [batch, length_decoder, num_labels]
        out_type = self.bilinear(type_h, type_c)

        # mask invalid position to -inf for log_softmax
        if mask_e is not None:
            minus_inf = -1e8
            minus_mask_d = (1 - mask_d) * minus_inf
            minus_mask_e = (1 - mask_e) * minus_inf
            out_arc = out_arc + minus_mask_d.unsqueeze(2) + minus_mask_e.unsqueeze(1)

        # [batch, length_decoder, length_encoder]
        loss_arc = F.log_softmax(out_arc, dim=2)
        # [batch, length_decoder, num_labels]
        loss_type = F.log_softmax(out_type, dim=2)

        # compute coverage loss
        # [batch, length_decoder, length_encoder]
        coverage = torch.exp(loss_arc).cumsum(dim=1)

        # get leaf and non-leaf mask
        # shape = [batch, length_decoder]
        mask_leaf = torch.eq(children, stacked_heads).float()
        mask_non_leaf = (1.0 - mask_leaf)

        # mask invalid position to 0 for sum loss
        if mask_e is not None:
            loss_arc = loss_arc * mask_d.unsqueeze(2) * mask_e.unsqueeze(1)
            coverage = coverage * mask_d.unsqueeze(2) * mask_e.unsqueeze(1)
            loss_type = loss_type * mask_d.unsqueeze(2)
            mask_leaf = mask_leaf * mask_d
            mask_non_leaf = mask_non_leaf * mask_d

            # number of valid positions which contribute to loss (remove the symbolic head for each sentence.
            num_leaf = mask_leaf.sum()
            num_non_leaf = mask_non_leaf.sum()
        else:
            # number of valid positions which contribute to loss (remove the symbolic head for each sentence.
            num_leaf = max_len_e
            num_non_leaf = max_len_e - 1

        # first create index matrix [length, batch]
        head_index = torch.arange(0, max_len_d).view(max_len_d, 1).expand(max_len_d, batch)
        head_index = head_index.type_as(out_arc.data).long()
        # [batch, length_decoder]
        if 0.0 < label_smooth < 1.0 - 1e-4:
            # label smoothing
            loss_arc1 = loss_arc[batch_index, head_index, children.data.t()].transpose(0, 1)
            loss_arc2 = loss_arc.sum(dim=2) / mask_e.sum(dim=1).unsqueeze(1)
            loss_arc = loss_arc1 * label_smooth + loss_arc2 * (1 - label_smooth)

            loss_type1 = loss_type[batch_index, head_index, stacked_types.data.t()].transpose(0, 1)
            loss_type2 = loss_type.sum(dim=2) / self.num_labels
            loss_type = loss_type1 * label_smooth + loss_type2 * (1 - label_smooth)
        else:
            loss_arc = loss_arc[batch_index, head_index, children.data.t()].transpose(0, 1)
            loss_type = loss_type[batch_index, head_index, stacked_types.data.t()].transpose(0, 1)

        loss_arc_leaf = loss_arc * mask_leaf
        loss_arc_non_leaf = loss_arc * mask_non_leaf

        loss_type_leaf = loss_type * mask_leaf
        loss_type_non_leaf = loss_type * mask_non_leaf

        loss_cov = (coverage - 2.0).clamp(min=0.)

        return -loss_arc_leaf.sum() / num_leaf, -loss_arc_non_leaf.sum() / num_non_leaf, \
               -loss_type_leaf.sum() / num_leaf, -loss_type_non_leaf.sum() / num_non_leaf, \
               loss_cov.sum() / (num_leaf + num_non_leaf), num_leaf, num_non_leaf

    def _decode_per_sentence(self, output_enc, arc_c, type_c, hx, length, beam, ordered, leading_symbolic, input_pos):
        def valid_hyp(base_id, child_id, head):
            if constraints[base_id, child_id]:
                return False
            elif not ordered or self.prior_order == PriorOrder.DEPTH or child_orders[base_id, head] == 0:
                return True
            elif self.prior_order == PriorOrder.LEFT2RIGTH:
                return child_id > child_orders[base_id, head]
            else:
                if child_id < head:
                    return child_id < child_orders[base_id, head] < head
                else:
                    return child_id > child_orders[base_id, head]

        # output_enc [length, hidden_size * 2]
        # arc_c [length, arc_space]
        # type_c [length, type_space]
        # hx [decoder_layers, hidden_size]
        if length is not None:
            output_enc = output_enc[:length]
            arc_c = arc_c[:length]
            type_c = type_c[:length]
            input_pos = input_pos[:length]  # input_pos: [length]
        else:
            length = output_enc.size(0)

        # [decoder_layers, 1, hidden_size]
        # hack to handle LSTM
        if isinstance(hx, tuple):
            hx, cx = hx
            hx = hx.unsqueeze(1)
            cx = cx.unsqueeze(1)
            h0 = hx
            hx = (hx, cx)
        else:
            hx = hx.unsqueeze(1)
            h0 = hx

        stacked_heads = [[0] for _ in range(beam)]
        grand_parents = [[0] for _ in range(beam)] if self.grandPar else None
        siblings = [[0] for _ in range(beam)] if self.sibling else None
        skip_connects = [[h0] for _ in range(beam)] if self.skipConnect else None
        children = torch.zeros(beam, 2 * length - 1).type_as(output_enc.data).long()
        stacked_types = children.new(children.size()).zero_()
        hypothesis_scores = output_enc.data.new(beam).zero_()
        constraints = np.zeros([beam, length], dtype=np.bool)
        constraints[:, 0] = True
        child_orders = np.zeros([beam, length], dtype=np.int32)

        # temporal tensors for each step.
        new_stacked_heads = [[] for _ in range(beam)]
        new_grand_parents = [[] for _ in range(beam)] if self.grandPar else None
        new_siblings = [[] for _ in range(beam)] if self.sibling else None
        new_skip_connects = [[] for _ in range(beam)] if self.skipConnect else None
        new_children = children.new(children.size()).zero_()
        new_stacked_types = stacked_types.new(stacked_types.size()).zero_()
        num_hyp = 1
        num_step = 2 * length - 1
        for t in range(num_step):
            # [num_hyp]
            heads = torch.LongTensor([stacked_heads[i][-1] for i in range(num_hyp)]).type_as(children)
            gpars = torch.LongTensor([grand_parents[i][-1] for i in range(num_hyp)]).type_as(
                children) if self.grandPar else None
            sibs = torch.LongTensor([siblings[i].pop() for i in range(num_hyp)]).type_as(
                children) if self.sibling else None

            # [decoder_layers, num_hyp, hidden_size]
            hs = torch.cat([skip_connects[i].pop() for i in range(num_hyp)], dim=1) if self.skipConnect else None

            # [num_hyp, hidden_size * 2]
            src_encoding = output_enc[heads]

            if self.sibling:
                mask_sibs = Variable(sibs.ne(0).float().unsqueeze(1))
                output_enc_sibling = output_enc[sibs] * mask_sibs
                src_encoding = src_encoding + output_enc_sibling

            if self.grandPar:
                output_enc_gpar = output_enc[gpars]
                src_encoding = src_encoding + output_enc_gpar

            # transform to decoder input
            # [num_hyp, dec_dim]
            src_encoding = F.elu(self.src_dense(src_encoding))

            # output [num_hyp, hidden_size]
            # hx [decoder_layer, num_hyp, hidden_size]
            output_dec, hx = self.decoder.step(src_encoding, hx=hx, hs=hs) if self.skipConnect else self.decoder.step(
                src_encoding, hx=hx)

            # arc_h size [num_hyp, 1, arc_space]
            arc_h = F.elu(self.arc_h(output_dec.unsqueeze(1)))
            # type_h size [num_hyp, type_space]
            type_h = F.elu(self.type_h(output_dec))

            # [num_hyp, length_encoder]
            if self.attention.use_features:
                # len-d == 1
                child_pos = input_pos.expand(num_hyp, *input_pos.size())  # [num-hyp, len-e]
                head_pos = input_pos[heads].unsqueeze(-1)  # [num-hyp, 1]
                child_position_idxes = torch.arange(length).type_as(input_pos.data).long().expand(num_hyp,
                                                                                                  -1).unsqueeze(
                    -2)  # [batch, 1, len-e]
                head_position_idxes = heads.unsqueeze(-1).unsqueeze(-1)  # [batch, 1, 1]
                raw_distances = head_position_idxes - child_position_idxes  # [batch, 1, len-e]
                input_features = self.attention_helper.get_final_features(raw_distances, child_pos.data, head_pos.data)
            else:
                input_features = None
            out_arc = self.attention(arc_h, arc_c.expand(num_hyp, *arc_c.size()),
                                     input_features=input_features).squeeze(dim=1).squeeze(dim=1)

            # [num_hyp, length_encoder]
            hyp_scores = F.log_softmax(out_arc, dim=1).data

            new_hypothesis_scores = hypothesis_scores[:num_hyp].unsqueeze(1) + hyp_scores
            # [num_hyp * length_encoder]
            new_hypothesis_scores, hyp_index = torch.sort(new_hypothesis_scores.view(-1), dim=0, descending=True)
            base_index = hyp_index / length
            child_index = hyp_index % length

            cc = 0
            ids = []
            new_constraints = np.zeros([beam, length], dtype=np.bool)
            new_child_orders = np.zeros([beam, length], dtype=np.int32)
            for id in range(num_hyp * length):
                base_id = base_index[id]
                child_id = child_index[id]
                head = heads[base_id]
                new_hyp_score = new_hypothesis_scores[id]
                if child_id == head:
                    assert constraints[base_id, child_id], 'constrains error: %d, %d' % (base_id, child_id)
                    if head != 0 or t + 1 == num_step:
                        new_constraints[cc] = constraints[base_id]
                        new_child_orders[cc] = child_orders[base_id]

                        new_stacked_heads[cc] = [stacked_heads[base_id][i] for i in range(len(stacked_heads[base_id]))]
                        new_stacked_heads[cc].pop()

                        if self.grandPar:
                            new_grand_parents[cc] = [grand_parents[base_id][i] for i in
                                                     range(len(grand_parents[base_id]))]
                            new_grand_parents[cc].pop()

                        if self.sibling:
                            new_siblings[cc] = [siblings[base_id][i] for i in range(len(siblings[base_id]))]

                        if self.skipConnect:
                            new_skip_connects[cc] = [skip_connects[base_id][i] for i in
                                                     range(len(skip_connects[base_id]))]

                        new_children[cc] = children[base_id]
                        new_children[cc, t] = child_id

                        hypothesis_scores[cc] = new_hyp_score
                        ids.append(id)
                        cc += 1
                elif valid_hyp(base_id, child_id, head):
                    new_constraints[cc] = constraints[base_id]
                    new_constraints[cc, child_id] = True

                    new_child_orders[cc] = child_orders[base_id]
                    new_child_orders[cc, head] = child_id

                    new_stacked_heads[cc] = [stacked_heads[base_id][i] for i in range(len(stacked_heads[base_id]))]
                    new_stacked_heads[cc].append(child_id)

                    if self.grandPar:
                        new_grand_parents[cc] = [grand_parents[base_id][i] for i in range(len(grand_parents[base_id]))]
                        new_grand_parents[cc].append(head)

                    if self.sibling:
                        new_siblings[cc] = [siblings[base_id][i] for i in range(len(siblings[base_id]))]
                        new_siblings[cc].append(child_id)
                        new_siblings[cc].append(0)

                    if self.skipConnect:
                        new_skip_connects[cc] = [skip_connects[base_id][i] for i in range(len(skip_connects[base_id]))]
                        # hack to handle LSTM
                        if isinstance(hx, tuple):
                            new_skip_connects[cc].append(hx[0][:, base_id, :].unsqueeze(1))
                        else:
                            new_skip_connects[cc].append(hx[:, base_id, :].unsqueeze(1))
                        new_skip_connects[cc].append(h0)

                    new_children[cc] = children[base_id]
                    new_children[cc, t] = child_id

                    hypothesis_scores[cc] = new_hyp_score
                    ids.append(id)
                    cc += 1

                if cc == beam:
                    break

            # [num_hyp]
            num_hyp = len(ids)
            if num_hyp == 0:
                return None
            elif num_hyp == 1:
                index = base_index.new(1).fill_(ids[0])
            else:
                index = torch.from_numpy(np.array(ids)).type_as(base_index)
            base_index = base_index[index]
            child_index = child_index[index]

            # predict types for new hypotheses
            # compute output for type [num_hyp, num_labels]
            out_type = self.bilinear(type_h[base_index], type_c[child_index])
            hyp_type_scores = F.log_softmax(out_type, dim=1).data
            # compute the prediction of types [num_hyp]
            hyp_type_scores, hyp_types = hyp_type_scores.max(dim=1)
            hypothesis_scores[:num_hyp] = hypothesis_scores[:num_hyp] + hyp_type_scores

            for i in range(num_hyp):
                base_id = base_index[i]
                new_stacked_types[i] = stacked_types[base_id]
                new_stacked_types[i, t] = hyp_types[i]

            stacked_heads = [[new_stacked_heads[i][j] for j in range(len(new_stacked_heads[i]))] for i in
                             range(num_hyp)]
            if self.grandPar:
                grand_parents = [[new_grand_parents[i][j] for j in range(len(new_grand_parents[i]))] for i in
                                 range(num_hyp)]
            if self.sibling:
                siblings = [[new_siblings[i][j] for j in range(len(new_siblings[i]))] for i in range(num_hyp)]
            if self.skipConnect:
                skip_connects = [[new_skip_connects[i][j] for j in range(len(new_skip_connects[i]))] for i in
                                 range(num_hyp)]
            constraints = new_constraints
            child_orders = new_child_orders
            children.copy_(new_children)
            stacked_types.copy_(new_stacked_types)
            # hx [decoder_layers, num_hyp, hidden_size]
            # hack to handle LSTM
            if isinstance(hx, tuple):
                hx, cx = hx
                hx = hx[:, base_index, :]
                cx = cx[:, base_index, :]
                hx = (hx, cx)
            else:
                hx = hx[:, base_index, :]

        children = children.cpu().numpy()[0]
        stacked_types = stacked_types.cpu().numpy()[0]
        heads = np.zeros(length, dtype=np.int32)
        types = np.zeros(length, dtype=np.int32)
        stack = [0]
        for i in range(num_step):
            head = stack[-1]
            child = children[i]
            type = stacked_types[i]
            if child != head:
                heads[child] = head
                types[child] = type
                stack.append(child)
            else:
                stacked_types[i] = 0
                stack.pop()

        return heads, types, length, children, stacked_types

    def decode(self, input_word, input_char, input_pos, mask=None, length=None, hx=None, beam=1, leading_symbolic=0,
               ordered=True):
        # reset noise for decoder
        self.decoder.reset_noise(0)

        # output from encoder [batch, length_encoder, tag_space]
        # output_enc [batch, length, input_size]
        # arc_c [batch, length, arc_space]
        # type_c [batch, length, type_space]
        # hn [num_direction, batch, hidden_size]
        output_enc, hn, mask, length = self._get_encoder_output(input_word, input_char, input_pos, mask_e=mask,
                                                                length_e=length, hx=hx)
        # output size [batch, length_encoder, arc_space]
        arc_c = F.elu(self.arc_c(output_enc))
        # output size [batch, length_encoder, type_space]
        type_c = F.elu(self.type_c(output_enc))
        # [decoder_layers, batch, hidden_size
        hn = self._transform_decoder_init_state(hn)
        batch, max_len_e, _ = output_enc.size()

        heads = np.zeros([batch, max_len_e], dtype=np.int32)
        types = np.zeros([batch, max_len_e], dtype=np.int32)

        children = np.zeros([batch, 2 * max_len_e - 1], dtype=np.int32)
        stack_types = np.zeros([batch, 2 * max_len_e - 1], dtype=np.int32)

        for b in range(batch):
            sent_len = None if length is None else length[b]
            # hack to handle LSTM
            if isinstance(hn, tuple):
                hx, cx = hn
                hx = hx[:, b, :].contiguous()
                cx = cx[:, b, :].contiguous()
                hx = (hx, cx)
            else:
                hx = hn[:, b, :].contiguous()

            preds = self._decode_per_sentence(output_enc[b], arc_c[b], type_c[b], hx, sent_len, beam, ordered,
                                              leading_symbolic, input_pos[b])
            if preds is None:
                preds = self._decode_per_sentence(output_enc[b], arc_c[b], type_c[b], hx, sent_len, beam, False,
                                                  leading_symbolic, input_pos[b])
            hids, tids, sent_len, chids, stids = preds
            heads[b, :sent_len] = hids
            types[b, :sent_len] = tids

            children[b, :2 * sent_len - 1] = chids
            stack_types[b, :2 * sent_len - 1] = stids

        return heads, types, children, stack_types
