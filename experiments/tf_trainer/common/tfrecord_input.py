"""DatasetInput class based on TFRecord files."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import tensorflow as tf
from tf_trainer.common import dataset_input
from tf_trainer.common import types
from typing import Callable, Dict, List


class TFRecordInput(dataset_input.DatasetInput):
  """TFRecord based DatasetInput.

  Handles parsing of TF Examples.
  """

  def __init__(
      self,
      train_path: str,
      validate_path: str,
      text_feature: str,
      labels: Dict[str, tf.DType],
      feature_preprocessor_init: Callable[[], Callable[[str], List[str]]],
      batch_size: int = 64,
      max_seq_length: int = 300,
      round_labels: bool = True) -> None:
    self._train_path = train_path
    self._validate_path = validate_path
    self._text_feature = text_feature
    self._labels = labels
    self._batch_size = batch_size
    self._max_seq_length = max_seq_length
    self.feature_preprocessor_init = feature_preprocessor_init
    self._round_labels = round_labels

  def train_input_fn(self) -> types.FeatureAndLabelTensors:
    """input_fn for TF Estimators for training set."""
    return self._input_fn_from_file(self._train_path)

  def validate_input_fn(self) -> types.FeatureAndLabelTensors:
    """input_fn for TF Estimators for validation set."""
    return self._input_fn_from_file(self._validate_path)

  def _input_fn_from_file(self, filepath: str) -> types.FeatureAndLabelTensors:
    dataset = tf.data.TFRecordDataset(filepath)  # type: tf.data.TFRecordDataset

    # Feature preprocessor must be initialized outside of the map function
    # but inside the inpout_fn function.
    feature_preprocessor = self.feature_preprocessor_init()
    parsed_dataset = dataset.map(
        lambda x: self._read_tf_example(x, feature_preprocessor))
    batched_dataset = parsed_dataset.padded_batch(
        self._batch_size,
        padded_shapes=(
            {
                # TODO: truncate to max_seq_length
                self._text_feature: [None]
            },
            {label: [] for label in self._labels}))

    # TODO: think about what happens when we run out of examples; should we be
    # using something that repeats over the dataset many time to allow
    # multi-epoch learning, or does estimator do this for us?
    itr_op = batched_dataset.make_initializable_iterator()
    # Adding the initializer operation to the graph.
    tf.add_to_collection(tf.GraphKeys.TABLE_INITIALIZERS, itr_op.initializer)
    return itr_op.get_next()

  def _read_tf_example(self,
                       record: tf.Tensor,
                       feature_preprocessor: Callable[[str], List[str]]
                      ) -> types.FeatureAndLabelTensors:
    """Parses TF Example protobuf into a text feature and labels.

    The input TF Example has a text feature as a singleton list with the full
    comment as the single element.
    """

    keys_to_features = {}
    keys_to_features[self._text_feature] = tf.FixedLenFeature([], tf.string)
    for label, dtype in self._labels.items():
      keys_to_features[label] = tf.FixedLenFeature([], dtype)
    parsed = tf.parse_single_example(
        record, keys_to_features)  # type: Dict[str, types.Tensor]

    text = parsed[self._text_feature]
    # I think this could be a feature column, but feature columns seem so beta.
    preprocessed_text = feature_preprocessor(text)
    features = {self._text_feature: preprocessed_text}
    if self._round_labels:
      labels = {label: tf.round(parsed[label]) for label in self._labels}
    else:
      labels = {label: parsed[label] for label in self._labels}

    return features, labels
