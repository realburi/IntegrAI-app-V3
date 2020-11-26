#-*- coding:utf-8 -*-

import torch.nn.functional as F
import torch.nn as nn
import numpy as np
import torch

class Encoder(nn.Module):
    def __init__(self, backbone, backbone_out=512, batch_first=True):
        super(Encoder, self).__init__()
        self.backbone = backbone
        self.lstm = nn.LSTM(backbone_out, 256, bidirectional=True, num_layers=2, batch_first=batch_first)
        self.out_channel = 2 * 256

    def forward(self, x):
        x = self.backbone(x) # (B, 512, 2, 32)
        x = x.squeeze(2).transpose(2, 1) # (B, 32, 512)
        x, _ = self.lstm(x)
        return x


class AttentionBlock(nn.Module):
    def __init__(self, input_size, state_size, hidden_size):
        super(AttentionBlock, self).__init__()
        self.input_size = input_size
        self.state_size = state_size
        self.hidden_size = hidden_size

        self.state_fc = nn.Linear(state_size, hidden_size)
        self.input_fc = nn.Linear(input_size, hidden_size)
        self.output_fc = nn.Linear(hidden_size, 1)

    def forward(self, x, s_prev):
        B, T, L = x.shape # (B, 32, 512)
        x = x.reshape(-1, L)

        xEmb = self.input_fc(x).view(B, T, self.hidden_size)
        sEmb = self.state_fc(s_prev).unsqueeze(1) # (B, 1, 512)
        sEmb = sEmb.expand_as(xEmb)

        ssum = torch.tanh(xEmb + sEmb)
        ssum = ssum.view(-1, self.hidden_size)
        oEmb = self.output_fc(ssum).view(B, T)
        attention_weights = torch.softmax(oEmb, 1).unsqueeze(1)
        return torch.bmm(attention_weights, x.reshape(B, T, L))


class Decoder(nn.Module):
    def __init__(self, num_classes, eos_label=94, maxlen=10, input_size=512, hidden_size=512, batch_first=True, beam_width=5, device='cpu', gradcam=False):
        super(Decoder, self).__init__()
        self.device = device
        self.maxlen = maxlen
        self.beam_width = beam_width
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_classes = num_classes
        self.eos = eos_label
        self.embedding = nn.Embedding(num_classes+1, hidden_size) # +1 -> blank label
        self.attention = AttentionBlock(input_size, hidden_size, hidden_size)
        self.gru = nn.GRU(input_size=input_size+hidden_size, hidden_size=hidden_size, batch_first=batch_first)
        self.output_fc = nn.Linear(hidden_size, num_classes)
        self.gradcam = gradcam
        self.to(device)

    def decode(self, x, y_prev, state_prev):
        attention_values = self.attention(x, state_prev.squeeze(0)).squeeze(1)
        y_emb = self.embedding(y_prev.long())
        y = torch.cat([y_emb, attention_values], 1).unsqueeze(1)

        out, state = self.gru(y, state_prev)
        out = torch.log_softmax(self.output_fc(out.squeeze(1)), 1)
        return out, state


    def forward(self, x, targets):
        B, T, L = x.shape
        state = torch.zeros(1, B, self.hidden_size).to(self.device)
        y_prev = torch.zeros((B,)).fill_(self.num_classes).to(self.device) #-> y_prev all blank

        if self.training or self.gradcam:
            teach_force = True if np.random.rand() < 0.5 else False
            scores, states = [], []
            for t in range(self.maxlen):
                if t > 0:
                    #refresh y_prev
                    if self.gradcam:
                        topv, topi = out.topk(1)
                        y_prev = topi.squeeze(1)
                    if teach_force:
                        y_prev = targets[:, t-1]
                    else:
                        topv, topi = out.topk(1)
                        y_prev = topi.squeeze(1)
                out, state = self.decode(x, y_prev, state)
                # score, predict = out.max(-1)
                scores.append(out)
                states.append(state)
            return torch.stack(scores), states
        else:
            preds, scores = self.beam_search(x)
            return preds, scores

    # https://github.com/IBM/pytorch-seq2seq/blob/fede87655ddce6c94b38886089e05321dc9802af/seq2seq/models/TopKDecoder.py
    def beam_search(self, x):
        beam_width = self.beam_width
        eos = self.eos
        def _inflate(tensor, times, dim):
          repeat_dims = [1] * tensor.dim()
          repeat_dims[dim] = times
          return tensor.repeat(*repeat_dims)

        batch_size, l, d = x.size()
        # inflated_encoder_feats = _inflate(encoder_feats, beam_width, 0) # ABC --> AABBCC -/-> ABCABC
        inflated_encoder_feats = x.unsqueeze(1).permute((1,0,2,3)).repeat((beam_width,1,1,1)).permute((1,0,2,3)).contiguous().view(-1, l, d)

        # Initialize the decoder
        state = torch.zeros(1, batch_size * beam_width, self.hidden_size).to(self.device)
        pos_index = (torch.Tensor(range(batch_size)) * beam_width).long().view(-1, 1).to(self.device)

        # Initialize the scores
        sequence_scores = torch.Tensor(batch_size * beam_width, 1).to(self.device)
        sequence_scores.fill_(-float('Inf')).to(self.device)
        sequence_scores.index_fill_(0, torch.Tensor([i * beam_width for i in range(0, batch_size)]).long().to(self.device), 0.0).to(self.device)
        # sequence_scores.fill_(0.0)

        # Initialize the input vector
        y_prev = torch.zeros((batch_size * beam_width)).fill_(self.num_classes).to(self.device)

        # Store decisions for backtracking
        stored_scores          = list()
        stored_predecessors    = list()
        stored_emitted_symbols = list()

        for i in range(self.maxlen):
          output, state = self.decode(inflated_encoder_feats, y_prev, state)
          log_softmax_output = F.log_softmax(output, dim=1)

          sequence_scores = _inflate(sequence_scores, self.num_classes, 1).to(self.device)
          sequence_scores += log_softmax_output
          scores, candidates = sequence_scores.view(batch_size, -1).topk(beam_width, dim=1)

          # Reshape input = (bk, 1) and sequence_scores = (bk, 1)
          y_prev = (candidates % self.num_classes).view(batch_size * beam_width)
          sequence_scores = scores.view(batch_size * beam_width, 1)

          # Update fields for next timestep
          predecessors = (torch.true_divide(candidates, self.num_classes) + pos_index.expand_as(candidates)).view(batch_size * beam_width, 1).type(torch.long)
          state = state.index_select(1, predecessors.squeeze())

          # Update sequence socres and erase scores for <eos> symbol so that they aren't expanded
          stored_scores.append(sequence_scores.clone())
          eos_indices = y_prev.view(-1, 1).eq(eos)
          if eos_indices.nonzero().dim() > 0:
            sequence_scores.masked_fill_(eos_indices, -float('inf'))

          # Cache results for backtracking
          stored_predecessors.append(predecessors)
          stored_emitted_symbols.append(y_prev)

        # Do backtracking to return the optimal values
        #====== backtrak ======#
        # Initialize return variables given different types
        p = list()
        l = [[self.maxlen] * beam_width for _ in range(batch_size)]  # Placeholder for lengths of top-k sequences

        # the last step output of the beams are not sorted
        # thus they are sorted here
        sorted_score, sorted_idx = stored_scores[-1].view(batch_size, beam_width).topk(beam_width)
        # initialize the sequence scores with the sorted last step beam scores
        s = sorted_score.clone()

        batch_eos_found = [0] * batch_size  # the number of EOS found
                                            # in the backward loop below for each batch
        t = self.maxlen - 1
        # initialize the back pointer with the sorted order of the last step beams.
        # add pos_index for indexing variable with b*k as the first dimension.
        t_predecessors = (sorted_idx + pos_index.expand_as(sorted_idx)).view(batch_size * beam_width)
        while t >= 0:
          # Re-order the variables with the back pointer
          current_symbol = stored_emitted_symbols[t].index_select(0, t_predecessors)
          t_predecessors = stored_predecessors[t].index_select(0, t_predecessors).squeeze()
          eos_indices = stored_emitted_symbols[t].eq(eos).nonzero()
          if eos_indices.dim() > 0:
            for i in range(eos_indices.size(0)-1, -1, -1):
              # Indices of the EOS symbol for both variables
              # with b*k as the first dimension, and b, k for
              # the first two dimensions
              idx = eos_indices[i]
              b_idx = int(torch.true_divide(idx[0], beam_width))
              # The indices of the replacing position
              # according to the replacement strategy noted above
              res_k_idx = beam_width - (batch_eos_found[b_idx] % beam_width) - 1
              batch_eos_found[b_idx] += 1
              res_idx = b_idx * beam_width + res_k_idx

              # Replace the old information in return variables
              # with the new ended sequence information
              t_predecessors[res_idx] = stored_predecessors[t][idx[0]]
              current_symbol[res_idx] = stored_emitted_symbols[t][idx[0]]
              s[b_idx, res_k_idx] = stored_scores[t][idx[0], [0]]
              l[b_idx][res_k_idx] = t + 1

          # record the back tracked results
          p.append(current_symbol)
          t -= 1
        # Sort and re-order again as the added ended sequences may change
        # the order (very unlikely)
        s, re_sorted_idx = s.topk(beam_width)
        for b_idx in range(batch_size):
          l[b_idx] = [l[b_idx][k_idx.item()] for k_idx in re_sorted_idx[b_idx,:]]

        re_sorted_idx = (re_sorted_idx + pos_index.expand_as(re_sorted_idx)).view(batch_size*beam_width)

        # Reverse the sequences and re-order at the same time
        # It is reversed because the backtracking happens in reverse time order
        p = [step.index_select(0, re_sorted_idx).view(batch_size, beam_width, -1) for step in reversed(p)]
        p = torch.cat(p, -1)[:,0,:]
        return p, torch.ones_like(p)


if __name__ == '__main__':
    from backbone import ResNet50
    bsize = 3
    maxlen = 10
    encoder = Encoder(ResNet50())
    encoder.lstm.load_state_dict(torch.load('../weights/BiLSTM_pretrained_SVT.pth'))
    encoder.eval()
    x = torch.rand(bsize, 3, 32, 78)
    encoded = encoder(x)
    print(encoded.shape)
    decoder = Decoder(97, maxlen=maxlen).eval()
    decoder.load_state_dict(torch.load('../weights/AttnGRU_pretrained_SVT.pth'))
    targets = torch.IntTensor(bsize, maxlen).fill_(1)
    preds, scores = decoder(encoded, targets)
    print(preds.shape, scores.shape)
    print(preds)
