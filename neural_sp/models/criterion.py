#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2018 Kyoto University (Hirofumi Inaguma)
#  Apache 2.0  (http://www.apache.org/licenses/LICENSE-2.0)

"""Criterions."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import math
import numpy as np
import torch
import torch.nn.functional as F


def cross_entropy_lsm(logits, ys, ylens, lsm_prob, size_average=False):
    """Compute cross entropy loss for label smoothing of sequence-to-sequence models.

    Args:
        logits (FloatTensor): `[B, T, vocab]`
        ys (LongTensor): Indices of labels. `[B, L]`.
        ylens (IntTensor): `[B]`
        lsm_prob (float):
        size_average (bool):
    Returns:
        loss (FloatTensor): `[1]`

    """
    bs, _, vocab = logits.size()

    # Create one-hot vector
    log_probs_uniform = logits.new_zeros(logits.size()).fill_(lsm_prob / (vocab - 1 - 2))
    log_probs_uniform[:, :, 0] = 0  # blank
    log_probs_uniform[:, :, 3] = 0  # pad
    for b in range(bs):
        for t in range(ylens[b]):
            log_probs_uniform[b, t, ys[b, t]] = 1 - lsm_prob

    # Compute XE for label smoothing
    log_probs = F.log_softmax(logits, dim=-1)
    xe = -torch.mul(log_probs_uniform, log_probs)
    loss = np.sum([xe[b, :ylens[b]].sum() for b in range(bs)])
    if size_average:
        loss /= bs
    return loss


def distillation(logits_student, probs_teacher, ylens, temperature=1, size_average=False):
    """Compute cross entropy loss for knowledge distillation of sequence-to-sequence models.

    Args:
        logits_student (FloatTensor): `[B, T, vocab]`
        probs_teacher (FloatTensor): `[B, T, vocab]`
        ylens (IntTensor): `[B]`
        temperature (float):
        size_average (bool):
    Returns:
        loss (FloatTensor): `[1]`

    """
    bs, _, vocab = logits_student.size()

    # Compute XE for knowledge distillation
    log_probs_student = F.log_softmax(logits_student / temperature, dim=-1)
    xe = -torch.mul(probs_teacher, log_probs_student)
    loss = np.sum([xe[b, :ylens[b]].sum() for b in range(bs)])
    if size_average:
        loss /= bs
    return loss


def kldiv_lsm_ctc(logits, ylens, size_average=False):
    """Compute KL divergence loss for label smoothing of CTC and Transducer models.

    Args:
        logits (FloatTensor): `[B, T, vocab]`
        ylens (IntTensor): `[B]`
        size_average (bool):
    Returns:
        loss (FloatTensor): `[1]`

    """
    bs = logits.size(0)
    vocab = logits.size(-1)

    # Create uniform distribution
    log_uniform = logits.new_zeros(logits.size()).fill_(math.log(1 / (vocab - 2)))
    log_uniform[:, :, 2] = 0  # eos
    log_uniform[:, :, 3] = 0  # pad

    # Compute KL divergence for label smoothing
    probs = F.softmax(logits, dim=-1)
    log_probs = F.log_softmax(logits, dim=-1)
    kl_div = torch.mul(probs, log_probs - log_uniform)
    loss = np.sum([kl_div[b, :ylens[b]].sum() for b in range(bs)])
    # assert loss >= 0
    if size_average:
        loss /= bs
    return loss


def focal_loss(logits, ys, ylens, alpha, gamma, size_average=False):
    """Compute focal loss.

    Args:
        logits (FloatTensor): `[B, T, vocab]`
        ys (LongTensor): Indices of labels. `[B, L]`
        ylens (IntTensor): `[B]`
        alpha (float):
        gamma (float):
        size_average (bool):
    Returns:
        loss (FloatTensor): `[1]`

    """
    bs = ys.size(0)

    # Compute focal loss
    log_probs = F.log_softmax(logits, dim=-1)
    probs_inv = -F.softmax(logits, dim=-1) + 1
    fl = - alpha * torch.mul(torch.pow(probs_inv, gamma), log_probs)
    loss = np.sum([fl[b, :ylens[b]].sum() for b in range(bs)])
    if size_average:
        loss /= bs
    return loss
