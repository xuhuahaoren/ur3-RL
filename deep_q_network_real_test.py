####################################################################################
# This file is for testing the dqn learning model in the real environment
# Modified by xfyu on May 24
####################################################################################
# -*- coding: utf-8 -*-
# !/usr/bin/python
from __future__ import print_function

import tensorflow as tf
import cv2
import os
import sys
import random
import numpy as np
import matplotlib.pyplot as plt

# import collect_code.pycontrol as ur

###################################################################################
# Important global parameters
###################################################################################
# PATH = "/home/robot/RL" # current working path
PATH = os.path.split(os.path.realpath(__file__))[0]
# tf.app.flags defined input parameters
# Necessary: VERSION, ENV_PATH.
# Annotate the parameters in training and in virtual environments
# tf.app.flags.DEFINE_string('TEST_PATH', '/home/robot/RL/data/new_grp2','test image path')
tf.app.flags.DEFINE_string('VERSION', 'virf_grp2_changepoint20_pre', 'version of this training')
# tf.app.flags.DEFINE_string('BASED_VERSION', '', 'version of the based model')
tf.app.flags.DEFINE_string('ENV_PATH', 'realenv_test', 'path of environment class file')
# tf.app.flags.DEFINE_integer('NUM_TRAINING_STEPS', 50000, 'number of time steps in one training')
# tf.app.flags.DEFINE_integer('OBSERVE', 1000, 'number of time steps to observe before training')
# tf.app.flags.DEFINE_integer('EXPLORE', 30000, 'number of time steps to explore after observation')
# tf.app.flags.DEFINE_integer('REPLAY_MEMORY', 500, 'number of previous transitions to remember')
# tf.app.flags.DEFINE_float('LEARNING_RATE', 0.001, 'learning rate for optimizer')
tf.app.flags.DEFINE_integer('TEST_ROUND', 10, 'how many episodes in the test')
# tf.app.flags.DEFINE_float('GAMMA', 0.99, 'decay rate of past observations')
# tf.app.flags.DEFINE_integer('BATCH', 32, 'size of minibatch')
# tf.app.flags.DEFINE_float('FINAL_EPSILON', 0.001, 'final value of epsilon')
# tf.app.flags.DEFINE_float('INITIAL_EPSILON', 0.01, 'starting value of epsilon')
# tf.app.flags.DEFINE_integer('COST_RECORD_STEP', 100, 'cost recording step')
# tf.app.flags.DEFINE_integer('NETWORK_RECORD_STEP', 1000, 'network recording step')
# tf.app.flags.DEFINE_integer('REWARD_RECORD_STEP', 100, 'reward recording step')
# tf.app.flags.DEFINE_integer('STEP_RECORD_STEP', 100, 'step recording step')
# tf.app.flags.DEFINE_integer('SUCCESS_RATE_TEST_STEP', 1000, 'testing accuracy step')
tf.app.flags.DEFINE_float('PER_GPU_USAGE', 0.333, 'how much space taken per gpu')
tf.app.flags.DEFINE_string('GPU_LIST', '0, 1', 'how much space taken per gpu')
tf.app.flags.DEFINE_integer('MAX_STEPS', 20, 'max steps defined in env')
tf.app.flags.DEFINE_float('MIN_ANGLE', 30.0, 'min angle defined in env')
tf.app.flags.DEFINE_float('MAX_ANGLE', 69.0, 'max angle defined in env')
FLAGS = tf.app.flags.FLAGS

# define global variables
env = None
# LOG_DIR = None
TRAIN_DIR = None
# BASED_DIR = None
READ_NETWORK_DIR = None
# SAVE_NETWORK_DIR = None
# FILE_SUCCESS = None
# FILE_REWARD = None
# FILE_STEP = None
ACTION_NORM = None
TEST_RESULT_PATH = None

# used in pre-process the picture
RESIZE_WIDTH = 128
RESIZE_HEIGHT = 128

# parameters used in testing
ACTIONS = 5  # number of valid actions
PAST_FRAME = 3


###################################################################################
# Functions
###################################################################################
def weight_variable(shape):
    initial = tf.truncated_normal(shape, stddev=0.01)
    return tf.Variable(initial)


def bias_variable(shape):
    initial = tf.constant(0.01, shape=shape)
    return tf.Variable(initial)


def conv2d(x, W, stride):
    return tf.nn.conv2d(x, W, strides=[1, stride, stride, 1], padding="SAME")


def max_pool_2x2(x):
    return tf.nn.max_pool(x, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding="SAME")


def space_tiling(x):  # expand from [None, 64] to [None, 4, 4, 64]
    x = tf.expand_dims(tf.expand_dims(x, 1), 1)
    return tf.tile(x, [1, 4, 4, 1])


'''
createNetwork - set the structure of CNN
'''
# network weights
W_conv1 = weight_variable([8, 8, PAST_FRAME, 32])
b_conv1 = bias_variable([32])

W_conv2 = weight_variable([6, 6, 32, 64])
b_conv2 = bias_variable([64])

W_conv3 = weight_variable([4, 4, 128, 64])
b_conv3 = bias_variable([64])

W_conv4 = weight_variable([3, 3, 64, 64])
b_conv4 = bias_variable([64])

W_fc1 = weight_variable([256, 256])
b_fc1 = bias_variable([256])

W_fc2 = weight_variable([256, 256])
b_fc2 = bias_variable([256])

W_fc3 = weight_variable([256, ACTIONS])
b_fc3 = bias_variable([ACTIONS])

W_fc_info = weight_variable([PAST_FRAME, 64])
b_fc_info = bias_variable([64])

# input layer
# one state to train each time
s = tf.placeholder(dtype=tf.float32, name='s', shape=(None, RESIZE_WIDTH, RESIZE_HEIGHT, PAST_FRAME))
past_info = tf.placeholder(dtype=tf.float32, name='past_info', shape=(None, PAST_FRAME))
training = tf.placeholder_with_default(False, name='training', shape=())

# hidden layers
h_conv1 = conv2d(s, W_conv1, 4) + b_conv1
h_bn1 = tf.layers.batch_normalization(h_conv1, axis=-1, training=training, momentum=0.9)
h_relu1 = tf.nn.relu(h_bn1)
h_pool1 = max_pool_2x2(h_relu1)  # [None, 16, 16, 32]

h_conv2 = conv2d(h_pool1, W_conv2, 2) + b_conv2
h_bn2 = tf.layers.batch_normalization(h_conv2, axis=-1, training=training, momentum=0.9)
h_relu2 = tf.nn.relu(h_bn2)
h_pool2 = max_pool_2x2(h_relu2)  # [None, 4, 4, 64]

h_fc_info = tf.matmul(past_info, W_fc_info) + b_fc_info
h_bn_info = tf.layers.batch_normalization(h_fc_info, axis=-1, training=training, momentum=0.9)
h_relu_info = tf.nn.relu(h_bn_info)  # [None, 64]

info_add = space_tiling(h_relu_info)  # [None, 4, 4, 64]
layer3_input = tf.concat([h_pool2, info_add], 3)  # [None, 4, 4, 128]
h_conv3 = conv2d(layer3_input, W_conv3, 1) + b_conv3
h_bn3 = tf.layers.batch_normalization(h_conv3, axis=-1, training=training, momentum=0.9)
h_relu3 = tf.nn.relu(h_bn3)  # [None, 4, 4, 64]
# h_pool3 = max_pool_2x2(h_relu3) # [None, 2, 2, 64]

h_conv4 = conv2d(h_relu3, W_conv4, 1) + b_conv4
h_bn4 = tf.layers.batch_normalization(h_conv4, axis=-1, training=training, momentum=0.9)
h_relu4 = tf.nn.relu(h_bn4)  # [None, 4, 4, 64]
h_pool4 = max_pool_2x2(h_relu4)  # [None, 2, 2, 64]

h_pool4_flat = tf.reshape(h_pool4, [-1, 256])  # [None, 256]

h_fc1 = tf.matmul(h_pool4_flat, W_fc1) + b_fc1
h_bn_fc1 = tf.layers.batch_normalization(h_fc1, axis=-1, training=training, momentum=0.9)
h_relu_fc1 = tf.nn.relu(h_bn_fc1)  # [None, 256]

h_fc2 = tf.matmul(h_relu_fc1, W_fc2) + b_fc2
h_bn_fc2 = tf.layers.batch_normalization(h_fc2, axis=-1, training=training, momentum=0.9)
h_relu_fc2 = tf.nn.relu(h_bn_fc2)  # [None, 256]
# readout layer
readout = tf.matmul(h_relu_fc2, W_fc3) + b_fc3  # [None, 5]

'''
Neural Network Definitions --- not necessary in test
'''
'''
# define the cost function
a = tf.placeholder(dtype=tf.float32, name='a', shape=(None, ACTIONS))
y = tf.placeholder(dtype=tf.float32, name='y', shape=(None))
accuracy = tf.placeholder(dtype=tf.float32, name='accuracy', shape=())
# define cost
with tf.name_scope('cost'):
    readout_action = tf.reduce_sum(tf.multiply(readout, a), reduction_indices=1)
    cost = tf.reduce_mean(tf.square(y - readout_action))
    tf.summary.scalar('cost', cost)
with tf.name_scope('accuracy'):
    tf.summary.scalar('accuracy', accuracy)
# define training step
with tf.name_scope('train'):
    optimizer = tf.train.AdamOptimizer(LEARNING_RATE)
    update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
    with tf.control_dependencies(update_ops):
        train_step = optimizer.minimize(cost)
'''

'''
testNetwork - test the training performance, calculate the success rate

Input: s, action,readout
Return: success rate
'''


def testNetwork():
    # init the real test environment
    test_env = env.FocusEnv([TEST_RESULT_PATH, None, FLAGS.MAX_STEPS, FLAGS.MIN_ANGLE, FLAGS.MAX_ANGLE])
    '''
    Start tensorflow
    '''

    # saving and loading networks
    saver = tf.train.Saver()

    gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=FLAGS.PER_GPU_USAGE)
    with tf.Session(config=tf.ConfigProto(gpu_options=gpu_options)) as sess:
        sess.run(tf.global_variables_initializer())

        # load in half-trained networks
        if FLAGS.VERSION:
            checkpoint = tf.train.get_checkpoint_state(READ_NETWORK_DIR)
            if checkpoint and checkpoint.model_checkpoint_path:
                saver.restore(sess, checkpoint.model_checkpoint_path)
                print("Successfully loaded:", checkpoint.model_checkpoint_path)
            else:
                print("Could not find old network weights")

        success_cnt = 0.0
        total_steps = 0.0
        # start test
        for test in range(FLAGS.TEST_ROUND):
            init_angle, init_img_path = test_env.reset()

            # generate the first state, a_past is 0
            img_t = cv2.imread(init_img_path)
            img_t = cv2.cvtColor(cv2.resize(img_t, (RESIZE_WIDTH, RESIZE_HEIGHT)), cv2.COLOR_BGR2GRAY)
            s_t = np.stack((img_t, img_t, img_t), axis=2)
            action_t = np.stack((0.0, 0.0, 0.0), axis=0)
            past_info_t = action_t
            step = 1
            # start 1 episode
            while True:
                # run the network forwardly
                readout_t = readout.eval(feed_dict={
                    s: [s_t],
                    past_info: [past_info_t],
                    training: False})[0]
                print(past_info_t)
                print(readout_t)
                # determine the next action
                action_index = np.argmax(readout_t)
                a_input = test_env.actions[action_index]
                # run the selected action and observe next state and reward
                angle_new, img_path_t1, terminal, success = test_env.test_step(a_input)

                if terminal:
                    # calculate
                    success_cnt += int(success)  # only represents the rate of active terminate
                    total_steps += step
                    # get the final focus
                    focus_end = TENG(img_path_t1)
                    print("test ", test, "ends at ", focus_end)
                    break

                img_t1 = cv2.imread(img_path_t1)
                img_t1 = cv2.cvtColor(cv2.resize(img_t1, (RESIZE_WIDTH, RESIZE_HEIGHT)), cv2.COLOR_BGR2GRAY)
                img_t1 = np.reshape(img_t1, (RESIZE_WIDTH, RESIZE_HEIGHT, 1))  # reshape, ready for insert
                action_new = np.reshape(a_input / ACTION_NORM, (1,))
                s_t1 = np.append(img_t1, s_t[:, :, :PAST_FRAME - 1], axis=2)
                action_t1 = np.append(action_new, action_t[:PAST_FRAME - 1], axis=0)
                past_info_t1 = action_t1
                # print test info
                print("TEST EPISODE", test, "/ TIMESTEP", step, \
                      "/ CURRENT ANGLE", test_env.cur_state, "/ ACTION", a_input)

                # update
                s_t = s_t1
                action_t = action_t1
                past_info_t = action_t
                step += 1

        sess.close()  # end session

    # calculate final return results
    success_rate = success_cnt / FLAGS.TEST_ROUND
    step_cost = total_steps / FLAGS.TEST_ROUND
    print("success_rate:", success_rate, "step per episode:", step_cost)
    # record and focus
    record_end_focus(success, step)
    return


'''
Tenengrad
'''


def TENG(img_path):
    img = cv2.imread(img_path)  # read pic
    img = cv2.cvtColor(cv2.resize(img, (RESIZE_WIDTH, RESIZE_HEIGHT)), cv2.COLOR_BGR2GRAY)  # resize
    guassianX = cv2.Sobel(img, cv2.CV_64F, 1, 0)
    guassianY = cv2.Sobel(img, cv2.CV_64F, 1, 0)
    return np.mean(guassianX * guassianX + guassianY * guassianY)


'''
record_end_focus
'''


def record_end_focus(success_rate, step_cost):
    # write success rate and average steps to txt file
    txtFile = os.path.join(TEST_RESULT_PATH, 'result.txt')
    with open(txtFile, 'w') as f:
        Data = "success rate:" + str(success_rate) + " step per episode:" + str(step_cost)
        f.write(Data)

    # data to record: endf and step
    endfList = []
    stepList = []
    epiDirs = []
    imageList = []

    # get all the directories under TEST_DIR
    for root, dirs, files in os.walk(TEST_RESULT_PATH):
        for dir in dirs:
            epiDirs.append(dir)
    epiDirs.sort(key=lambda obj: int(obj))  # only process dirs, sort episode dirs

    # walk through the folder
    for p in range(len(epiDirs)):
        imageList = []  # clear list
        # get into one episode directory
        for root, dirs, files in os.walk(os.path.join(TEST_RESULT_PATH, epiDirs[p])):
            for file in files:
                if os.path.splitext(file)[1] == '.jpg':
                    imageList.append(file)
        # print(imageList)
        # sort
        imageList.sort(key=lambda obj: int(obj.split('_')[0]))  # sort image list
        fList = []  # clear the list

        # walk through the images
        for i in range(len(imageList)):
            img_path = TEST_RESULT_PATH + '/' + epiDirs[p] + '/' + imageList[i]
            print("processing %s" % img_path)
            focus = TENG(img_path)
            fList.append(focus)
        # plot focus changing in one episode
        plot_focus_in_one_episode(os.path.join(TEST_RESULT_PATH, epiDirs[p]), p, fList)
        endfList.append(fList[-1])  # add the final focus to endfList
        stepList.append(len(imageList))
    plot_histogram(endfList, stepList)
    return


'''
plot focus in one episode
'''


def plot_focus_in_one_episode(epipath, p, fList):
    plt.figure()
    plt.plot(fList, 'bx-')
    plt.xlabel("ops")
    plt.ylabel("Focus Measure")
    plt.title("Focus Changing in episode {}".format(p))
    plt.savefig(epipath + "/f_change", dpi=600)
    # plt.show() 


'''
plot histogram of end focus measure and steps
'''


def plot_histogram(endfList, stepList):
    # plot focus histogram
    plt.figure()
    f = [94647, 85677, 93443, 100003, 99992, 88889, 99902, 110029, 89898, 92201]
    X = [15000, 30000, 45000, 60000, 75000, 90000, 105000, 120000]
    X1 = [X[i] + 6300 for i in range(len(X))]
    Y1 = [0 for i in range(len(X))]
    Y2 = [0 for i in range(len(X))]
    for i in range(len(endfList)):
        Y1[int(endfList[i] / 15000)] += 1
        Y2[int(f[i] / 15000)] += 1
    print(endfList, f)
    print(Y1, Y2)
    plt.bar(X, Y1, width=6000, facecolor='lightskyblue', label='virtually-trained model')
    plt.bar(X1, Y2, width=6000, facecolor='yellowgreen', label='real-trained model')
    # plt.axis([0, 130000, 0, 6])
    plt.xlabel("Focus Positions")
    plt.ylabel("Number of Cases")
    # plt.title("Distribution of Focused Positions")
    plt.legend(loc="upper left")
    plt.savefig(os.path.join(TEST_RESULT_PATH, "endf"), dpi=600)
    # plt.show()

    '''
    
    plt.hist(endfList, bins=10, normed=0, facecolor="blue", edgecolor="black", alpha=0.7, hold=1)
    plt.hist(f, bins=10, normed=0, facecolor='red', edgecolor='black', alpha=0.7)
    plt.xlabel("Focus Measure Region")
    plt.ylabel("Number of Cases")
    plt.title("Endpoint Focus Measure Distribution")
    plt.savefig(os.path.join(TEST_RESULT_PATH, "endf"), dpi=600)
    plt.show()
    '''

    # plot steps histogram
    '''
    plt.figure()
    print(stepList)
    plt.hist(stepList, bins=FLAGS.MAX_STEPS, normed=0, facecolor="blue", edgecolor="black", alpha=0.7)
    plt.xlabel("Steps Region")
    plt.ylabel("Number of Cases")
    plt.title("Endpoint Steps Distribution")
    plt.savefig(os.path.join(TEST_RESULT_PATH, "endstep"), dpi=600)
    plt.show()
    '''


'''
main
'''


def main(_):
    global TRAIN_DIR, READ_NETWORK_DIR, ACTION_NORM, env, TEST_RESULT_PATH
    # import env
    env = __import__(FLAGS.ENV_PATH)
    # normalize the action
    ACTION_NORM = 0.3 * env.TIMES

    # specify the important directories
    TRAIN_DIR = PATH + "/training/" + FLAGS.VERSION
    # the following files are all in training directories
    READ_NETWORK_DIR = TRAIN_DIR + "/saved_networks_" + FLAGS.VERSION
    # test result folder
    TEST_RESULT_PATH = PATH + "/realtesting/" + FLAGS.VERSION
    # if already exists, delete it and new another one
    if not os.path.isdir(TEST_RESULT_PATH):
        os.makedirs(TEST_RESULT_PATH)

    # set GPU
    os.environ['CUDA_VISIBLE_DEVICES'] = FLAGS.GPU_LIST

    # start real test!
    # testNetwork()
    record_end_focus(0.7, 9.8)


if __name__ == '__main__':
    tf.app.run()
