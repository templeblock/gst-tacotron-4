import io
import numpy as np
import tensorflow as tf
from hparams import hparams
from librosa import effects
from models import create_model
from text import text_to_sequence
from util import audio, plot
import textwrap

import datetime
import random





class Synthesizer:
  def __init__(self, teacher_forcing_generating=False):
    self.teacher_forcing_generating = teacher_forcing_generating
  def load(self, checkpoint_path, reference_mel=None, model_name='tacotron'):
    print('Constructing model: %s' % model_name)
    inputs = tf.placeholder(tf.float32, [1, None, 80], 'inputs')
    inputs_jp = tf.placeholder(tf.float32, [1, None, 80], 'inputs_jp')
    input_lengths = tf.placeholder(tf.int32, [1], 'input_lengths')
    # if reference_mel is not None:
    #   reference_mel = tf.placeholder(tf.float32, [1, None, hparams.num_mels], 'reference_mel')
    # # Only used in teacher-forcing generating mode
    # if self.teacher_forcing_generating:
    #   mel_targets = tf.placeholder(tf.float32, [1, None, hparams.num_mels], 'mel_targets')
    # else:
    #   mel_targets = None

    with tf.variable_scope('model') as scope:
      self.model = create_model(model_name, hparams)
      self.model.initialize(inputs, input_lengths, inputs_jp)
      self.wav_output = audio.inv_spectrogram_tensorflow(self.model.linear_outputs[0])
      self.alignments = self.model.alignments[0]

    print('Loading checkpoint: %s' % checkpoint_path)
    self.session = tf.Session()
    self.session.run(tf.global_variables_initializer())
    saver = tf.train.Saver()
    saver.restore(self.session, checkpoint_path)


  def synthesize(self, path_in, path_re, mel_targets=None, reference_mel=None, alignment_path=None):
    wav_in = audio.load_wav(path_in)
    wav_re = audio.load_wav(path_re)
    mel_in = audio.melspectrogram(wav_in).astype(np.float32)
    mel_re = audio.melspectrogram(wav_re).astype(np.float32)
   # print(mel_jp)
    feed_dict = {
      self.model.inputs: [mel_in.T],
      self.model.input_lengths: np.asarray([len(mel_in)], dtype=np.int32),
      self.model.inputs_jp: [mel_re.T],
    }
    # if mel_targets is not None:
    #   mel_targets = np.expand_dims(mel_targets, 0)
    #   print(reference_mel.shapex)
    #   feed_dict.update({self.model.mel_targets: np.asarray(mel_targets, dtype=np.float32)})
    # if reference_mel is not None:
    #   reference_mel = np.expand_dims(reference_mel, 0)
    #   print(reference_mel.shapex)
    #   feed_dict.update({self.model.reference_mel: np.asarray(reference_mel, dtype=np.float32)})

    wav_out, alignments = self.session.run([self.wav_output, self.alignments], feed_dict=feed_dict)
    wav = audio.inv_preemphasis(wav_out)
    end_point = audio.find_endpoint(wav)
    wav = wav[:end_point]
    nowTime = datetime.datetime.now().strftime("%Y%m%d%H%M%S")  # 生成当前时间
    randomNum = random.randint(0, 100)  # 生成的随机整数n，其中0<=n<=100
    if randomNum <= 10:
      randomNum = str(0) + str(randomNum)
    uniqueNum = str(nowTime) + str(randomNum)
    out_dir = "static\\out\\"+uniqueNum+".wav"
    out_name=uniqueNum+".wav"

    audio.save_wav(wav, out_dir)
    out = io.BytesIO()
    audio.save_wav(wav, out)
    # n_frame = int(end_point / (hparams.frame_shift_ms / 1000* hparams.sample_rate)) + 1
    # plot.plot_alignment(alignments[:,:n_frame], alignment_path, info='%s' % (path))
    return out_dir,out_name
