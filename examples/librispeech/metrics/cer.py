#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""Define evaluation method by Character Error Rate (Librispeech corpus)."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import re
from tqdm import tqdm

from utils.io.labels.character import Idx2char
from utils.io.variable import np2var
from utils.evaluation.edit_distance import compute_cer, compute_wer, wer_align


def do_eval_cer(model, model_type, dataset, label_type, data_size, beam_width,
                is_test=False, eval_batch_size=None, progressbar=False):
    """Evaluate trained model by Phone Error Rate.
    Args:
        model: the model to evaluate
        model_type (string): ctc or attention
        dataset: An instance of a `Dataset' class
        label_type (string): character or character_capital_divide or
            word_freq1 or word_freq5 or word_freq10 or word_freq15
        data_size (string): 100h or 460h or 960h
        beam_width: (int): the size of beam
        is_test (bool, optional): set to True when evaluating by the test set
        eval_batch_size (int, optional): the batch size when evaluating the model
        progressbar (bool, optional): if True, visualize the progressbar
    Returns:
        cer_mean (float): An average of CER
        wer_mean (float): An average of WER
    """
    batch_size_original = dataset.batch_size

    # Reset data counter
    dataset.reset()

    # Set batch size in the evaluation
    if eval_batch_size is not None:
        dataset.batch_size = eval_batch_size

    if label_type == 'character':
        vocab_file_path = '../../metrics/vocab_files/character.txt'
    else:
        vocab_file_path = '../../metrics/vocab_files/' + \
            label_type + '_' + data_size + '.txt'

    idx2char = Idx2char(vocab_file_path)

    cer_mean, wer_mean = 0, 0
    if progressbar:
        pbar = tqdm(total=len(dataset))
    for data, is_new_epoch in dataset:

        # Create feed dictionary for next mini-batch
        if model_type in ['ctc', 'attention']:
            inputs, labels_true, inputs_seq_len, labels_seq_len, _ = data
        else:
            raise NotImplementedError
        inputs = np2var(inputs, use_cuda=model.use_cuda, volatile=True)

        batch_size = inputs[0].size(0)

        # Decode
        if model_type == 'attention':
            labels_pred, _ = model.decode_infer(
                inputs[0], beam_width=beam_width)
        elif model_type == 'ctc':
            inputs_seq_len = np2var(
                inputs_seq_len, use_cuda=model.use_cuda, volatile=True, dtype='int')
            labels_pred = model.decode(
                inputs[0], inputs_seq_len[0], beam_width=beam_width)

        for i_batch in range(batch_size):

            # Convert from list of index to string
            if is_test:
                str_true = labels_true[0][i_batch][0]
                # NOTE: transcript is seperated by space('_')
            else:
                str_true = idx2char(
                    labels_true[0][i_batch][1:labels_seq_len[0][i_batch] - 1])
            str_pred = idx2char(labels_pred[i_batch]).split('>')[0]
            # NOTE: Trancate by <EOS>

            # Remove consecutive spaces
            str_pred = re.sub(r'[_]+', '_', str_pred)

            # Remove garbage labels
            str_true = re.sub(r'[\'<>]+', '', str_true)
            str_pred = re.sub(r'[\'<>]+', '', str_pred)

            # Compute WER
            wer_mean += compute_wer(ref=str_true.split('_'),
                                    hyp=str_pred.split('_'),
                                    normalize=True)
            # substitute, insert, delete = wer_align(
            #     ref=str_pred.split('_'),
            #     hyp=str_true.split('_'))
            # print('SUB: %d' % substitute)
            # print('INS: %d' % insert)
            # print('DEL: %d' % delete)

            # Compute CER
            cer_mean += compute_cer(ref=str_true,
                                    hyp=str_pred,
                                    normalize=True)

            if progressbar:
                pbar.update(1)

        if is_new_epoch:
            break

    cer_mean /= len(dataset)
    wer_mean /= len(dataset)

    # Register original batch size
    if eval_batch_size is not None:
        dataset.batch_size = batch_size_original

    return cer_mean, wer_mean