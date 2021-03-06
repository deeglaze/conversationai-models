"""Tests for tfrecord_input."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from tf_trainer.common import tfrecord_input
from tf_trainer.common import types

import numpy as np
import tensorflow as tf


class TFRecordInputTest(tf.test.TestCase):


  def setUp(self): 
    ex = tf.train.Example(
      features=tf.train.Features(
          feature={
              "label":
                  tf.train.Feature(
                      float_list=tf.train.FloatList(value=[0.8])),
              "comment":
                  tf.train.Feature(
                      bytes_list=tf.train.BytesList(
                          value=["Hi there Bob".encode("utf-8")]))
                  }))
    self.ex_tensor = tf.convert_to_tensor(ex.SerializeToString(), dtype=tf.string)

    self.word_to_idx = {"Hi": 12, "there": 13}
    self.unknown_token = 999

  def preprocessor(self, text):
    return tf.py_func(
        lambda t: np.asarray([self.word_to_idx.get(x, self.unknown_token) for x in t.decode().split(" ")]),
        [text], tf.int64)

  def test_TFRecordInput_unrounded(self):
    dataset_input = tfrecord_input.TFRecordInput(
        train_path=None,
        validate_path=None,
        text_feature="comment",
        labels={"label": tf.float32},
        feature_preprocessor=self.preprocessor,
        round_labels=False)

    with self.test_session():
      features, labels = dataset_input._read_tf_example(self.ex_tensor)
      self.assertEqual(list(features["comment"].eval()), [12, 13, 999])
      self.assertAlmostEqual(labels["label"].eval(), 0.8)

  def test_TFRecordInput_rounded(self):
    dataset_input = tfrecord_input.TFRecordInput(
        train_path=None,
        validate_path=None,
        text_feature="comment",
        labels={"label": tf.float32},
        feature_preprocessor=self.preprocessor,
        round_labels=True)

    with self.test_session():
      features, labels = dataset_input._read_tf_example(self.ex_tensor)
      self.assertEqual(list(features["comment"].eval()), [12, 13, 999])
      self.assertEqual(labels["label"].eval(), 1.0)

if __name__ == "__main__":
  tf.test.main()
