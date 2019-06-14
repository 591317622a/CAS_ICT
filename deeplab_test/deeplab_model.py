#!D:/workplace/python
# -*- coding: utf-8 -*-
# @File  : cifar10_atrous_conv2d.py
# @Author: WangYe
# @Date  : 2019/3/26
# @Software: PyCharm

# coding:utf-8
# 导入官方cifar10模块
#from tensorflow.image.cifar10 import cifar10
# import cifar10
# import tensorflow as tf
#
# # tf.app.flags.FLAGS是tensorflow的一个内部全局变量存储器
# FLAGS = tf.app.flags.FLAGS
# # cifar10模块中预定义下载路径的变量data_dir为'/tmp/cifar10_eval',预定义如下：
# # tf.app.flags.DEFINE_string('data_dir', './cifar10_data',
# #                           """Path to the CIFAR-10 data directory.""")
# # 为了方便，我们将这个路径改为当前位置
# FLAGS.data_dir = './cifar10_data'
#
# # 如果不存在数据文件则下载，并且解压
# cifar10.maybe_download_and_extract()
from readdata import read,read_image
from readhdf5 import train_data,label_data,readdata
import tensorflow as tf
import numpy as np
import time

#cifar10.maybe_download_and_extract()

# datapath = r'train.txt'
# trainpath = r'D:\code\python\DeepLab_v3\data\datasets\VOCdevkit\VOC2012\JPEGImages'
# labelpath = r'D:\code\python\DeepLab_v3\data\datasets\VOCdevkit\VOC2012\SegmentationObject'
# name_list = read(datapath)
# train_list = read_image(path=trainpath, list_name=name_list, str='.jpg', dim=3)  # (1464, 500, 500, 3)
# label_list = read_image(path=labelpath, list_name=name_list, str='.png', dim=1)  # (1464, 500, 500, 1)

# def variable_with_weight_loss(shape, stddev, w1):
#     var = tf.Variable(tf.truncated_normal(shape, stddev=stddev))
#     if w1 is not None:
#         weight_loss = tf.multiply(tf.nn.l2_loss(var), w1, name='weight_loss')
#         tf.add_to_collection('losses', weight_loss)
#     return var
path = 'test1.h5'
matrix = readdata(path)
train_list = train_data(matrix)
label_list =  label_data(matrix)
max_steps = 3000
batch_size = 1
train_x1 = 384  #训练集矩阵第一维度
train_x2 = 576  #训练集矩阵第二维度
train_dim = 4  #训练集图片通道数
label_y1 = 384  #标签矩阵第一维度
label_y2 = 576  #标签矩阵第二维度
label_dim = 1   #标签图片通道数


image_holder = tf.placeholder(tf.float32, [batch_size, train_x1, train_x2, train_dim])
label_holder = tf.placeholder(tf.float32, [batch_size, label_y1, label_y2, label_dim])

def tf_conv(inputs,filters,kernel_size,
            strides=1,stddev=0.01,padding = 'SAME'):  #卷积层
    out = tf.layers.conv2d(
        inputs=inputs,  #输入tensor
        filters=filters, #输出维度
        kernel_size=kernel_size,#卷积核大小,例如 [3,3]是3*3的大小
        strides=strides,        #步长
        padding=padding,        #是否填充
        activation=tf.nn.relu,
        # kernel_initializer=tf.truncated_normal_initializer(stddev=stddev)#卷积核的初始化，一般不管
    )
    return out

def tf_pooling(inputs,pool_size,strides):   #池化层
    out =tf.layers.max_pooling2d(
        inputs=inputs,   #输入tensor
        pool_size=pool_size, #池化大小
        strides=strides    #步长
    )
    return out

def tf_atrous_conv(inputs, filters,kernel_size, rate, padding='SAME'):#空洞卷积层
    # out = tf.nn.atrous_conv2d(
    #     value=inputs,  # 输入tensor
    #     filters=filters_kernel,  # 输出维度+卷积核  [卷积核的高度，卷积核的宽度，输入通道数，输入通道数]
    #     rate=rate,  #空洞卷积步长,[1,1]指上下各填充1
    #     padding=padding,  # 是否填充
    # )

    out = tf.layers.conv2d(inputs=inputs, #输入tensor
                           filters=filters, #输出维度
                           kernel_size=kernel_size,#卷积核大小
                            padding=padding,
                           dilation_rate=(rate, rate)#卷积孔大小
                           )

    return out

'''
残差网络是非连续层数之间的一个参数传递，例如第5层和第10层，那第10层就是 9->10->10+5
就像SDU一样，绳索速降，从10楼直接顺着个绳就到1楼了，跳过中间楼层了
所以只有best of the best 才能加入SDU
'''
def tf_resnet(net1,net2):  #残差网络

    out = tf.add(net1, net2)
    return out


def tf_trans_conv(inputs,filters,kernel_size,strides,padding='valid'):
    out = tf.layers.conv2d_transpose(
        inputs=inputs,     #输入的张量
        filters=filters,   #输出维度
        kernel_size=kernel_size,  #卷积核大小
        strides=strides,   #放大倍数
        padding=padding
    )
    return out

def atrous_spatial_pyramid_pooling(inputs, filters=256, regularizer=None):  #ASPP层
    '''
    Atrous Spatial Pyramid Pooling (ASPP) Block
    '''
    pool_height = tf.shape(inputs)[1]
    pool_width = tf.shape(inputs)[2]

    resize_height = pool_height
    resize_width = pool_width

    # Atrous Spatial Pyramid Pooling
    # Atrous 1x1
    aspp1x1 = tf.layers.conv2d(inputs=inputs, filters=filters, kernel_size=(1, 1),
                               padding='same', kernel_regularizer=regularizer,
                               name='aspp1x1')
    # Atrous 3x3, rate = 6
    aspp3x3_1 = tf.layers.conv2d(inputs=inputs, filters=filters, kernel_size=(3, 3),
                                 padding='same', dilation_rate=(12, 12), kernel_regularizer=regularizer,
                                 name='aspp3x3_1')
    # Atrous 3x3, rate = 12
    aspp3x3_2 = tf.layers.conv2d(inputs=inputs, filters=filters, kernel_size=(3, 3),
                                 padding='same', dilation_rate=(24, 24), kernel_regularizer=regularizer,
                                 name='aspp3x3_2')
    # Atrous 3x3, rate = 18
    aspp3x3_3 = tf.layers.conv2d(inputs=inputs, filters=filters, kernel_size=(3, 3),
                                 padding='same', dilation_rate=(36, 36), kernel_regularizer=regularizer,
                                 name='aspp3x3_3')
    # Image Level Pooling
    image_feature = tf.reduce_mean(inputs, [1, 2], keepdims=True)
    image_feature = tf.layers.conv2d(inputs=image_feature, filters=filters, kernel_size=(1, 1),
                                     padding='same')
    image_feature = tf.image.resize_bilinear(images=image_feature,
                                             size=[resize_height, resize_width],
                                             align_corners=True, name='image_pool_feature')
    # Merge Poolings
    outputs = tf.concat(values=[aspp1x1, aspp3x3_1, aspp3x3_2, aspp3x3_3, image_feature],
                        axis=3, name='aspp_pools')
    outputs = tf.layers.conv2d(inputs=outputs, filters=filters, kernel_size=(1, 1),
                               padding='same', kernel_regularizer=regularizer, name='aspp_outputs')

    return outputs


def model():

    #第一堆
    resnet2 = tf_conv(inputs=image_holder,filters=64,strides=1,kernel_size = [3,3])
    conv = tf_conv(inputs=image_holder,filters=64,strides=2,kernel_size = [8,8],padding='SAME')
    pool = tf_pooling(inputs=conv,pool_size=[2,2],strides=2)
    print('1',pool)
    #第二堆
    for i in range(3):
        conv = tf_conv(inputs=pool,filters=64,kernel_size=[1,1])
        conv = tf_conv(inputs=conv,filters=64,kernel_size=[3,3])
        conv = tf_conv(inputs=conv,filters=256,kernel_size=[3,3])
    resnet1 = conv
    print('2',conv)
    #第三堆
    for i in range(4):
        conv = tf_conv(inputs=conv,filters=128,kernel_size=[1,1])
        conv = tf_conv(inputs=conv, filters=128, kernel_size=[3,3])
        conv = tf_conv(inputs=conv, filters=512, kernel_size=[1, 1])
    print("3",conv)
    #第四堆
    for i in range(6):
        conv = tf_conv(inputs=conv, filters=256, kernel_size=[1, 1])
        atr_conv = tf_atrous_conv(inputs=conv,filters=256,kernel_size=[3,3],rate=2)
        conv = tf_conv(inputs=atr_conv,filters=1024,kernel_size=[1,1])
    print("4",conv)
    #第五维度
    for i in range(3):
        conv = tf_conv(inputs=conv, filters=512, kernel_size=[1, 1])
        atr_conv = tf_atrous_conv(inputs=conv, filters=512,kernel_size=[3,3], rate=4)
        conv = tf_conv(inputs=atr_conv, filters=2048, kernel_size=[1, 1])
    print("5",conv)
    #第五维度，ASPP层
    ASPP = atrous_spatial_pyramid_pooling(conv,filters=256)
    print("5,ASPP",ASPP)

    #第六维度
    '''
    论文中图片此处维度有问题，这里更改了步长，将维度变相等，否则维度对不上
    '''
    conv = tf_conv(inputs=ASPP,filters=256,kernel_size=[1,1],strides=2)
    trans_conv = tf_trans_conv(inputs=conv,filters=256,kernel_size=[2,2],strides=2)
    # print('121',trans_conv)
    conv = tf_conv(inputs=resnet1,filters=256,kernel_size=[3,3])
    resnet_conv = tf_resnet(conv,trans_conv)
    print('6',resnet_conv)

    #第七维度
    conv = tf_conv(inputs=resnet_conv,filters=256,kernel_size=[3,3])
    conv = tf_conv(inputs=conv, filters=256, kernel_size=[3, 3])
    trans_conv = tf_trans_conv(inputs=conv,filters=256,kernel_size=[2,2],strides=2)
    trans_conv = tf_trans_conv(inputs=trans_conv, filters=256, kernel_size=[2, 2], strides=2)
            #加入残差网络的预备卷积
    conv = tf_conv(inputs=resnet2,filters=256,kernel_size=[3,3])
    resnet_conv = tf_resnet(conv,trans_conv)
    print('7',resnet_conv)
    #第八维度
    conv = tf_conv(inputs=resnet_conv,filters=256,kernel_size=[3,3])
    conv = tf_conv(inputs=conv,filters=256,kernel_size=[3,3])
    conv = tf_conv(inputs=conv,filters=3,kernel_size=[1,1])
    print('8',conv)
    out = conv
    return out


logits=model()


def get_Batch(data, label, batch_size):
    print(data.shape, label.shape)
    input_queue = tf.train.slice_input_producer([data, label], num_epochs=1, shuffle=True, capacity=32 )
    x_batch, y_batch = tf.train.batch(input_queue, batch_size=batch_size, num_threads=1, capacity=32, allow_smaller_final_batch=False)
    print('x_batch',x_batch.shape)
    print('y_batch',y_batch.shape)
    return x_batch, y_batch
image_batch,label_batch = get_Batch(train_list,label_list,batch_size)


def loss(logits, labels):
    labels = tf.cast(labels, tf.float32)
    cross_entropy = logits - labels
    # tf.nn.sparse_softmax_cross_entropy_with_logits\
    # (logits=logits, labels=labels,
    #   # name='cross_entropy_per_example'
    #  )
    cross_entropy_mean = tf.reduce_mean(cross_entropy, name='cross_entropy')
    tf.add_to_collection('losses', cross_entropy_mean)
    return tf.add_n(tf.get_collection('losses'), name='total_loss')


loss = loss(logits, label_holder)

train_op = tf.train.AdamOptimizer(1e-3).minimize(loss)
# top_k_op = tf.nn.in_top_k(logits, tf.cast(label_holder, tf.int64), 1)


sess = tf.InteractiveSession()
tf.global_variables_initializer().run()
sess.run(tf.local_variables_initializer())
tf.train.start_queue_runners()
for step in range(max_steps):
    start_time = time.time()
    # image_batch, label_batch = sess.run([images_train, labels_train])
    date,label= sess.run([image_batch,label_batch])
    _, loss_value = sess.run([train_op, loss], feed_dict={image_holder: date, label_holder: label})
    duration = time.time() - start_time
    if step % 10 == 0:
        examples_per_sec = batch_size / duration
        sec_per_batch = float(duration)

        format_str = ('step %d,loss=%.2f (%.1f examples/sec;%.3f sec/batch)')
        print(format_str % (step, loss_value, examples_per_sec, sec_per_batch))
#
# num_examples = 10000
# import math
#
# num_iter = int(math.ceil(num_examples / batch_size))
# true_count = 0
# total_sample_count = num_iter * batch_size
# step = 0
# # with tf.Session() as sess:
# while step < num_iter:
#     image_batch, label_batch = sess.run([images_test, labels_test])
#     predictions = sess.run([top_k_op], feed_dict={image_holder: image_batch,
#                                                   label_holder: label_batch})
#     true_count += np.sum(predictions)
#     step += 1
#     if step % 10 == 0:
#         print(true_count)
#
# precision = float(true_count) / total_sample_count
# print('precision @ 1 =%.3f' % precision)