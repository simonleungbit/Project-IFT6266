import sys
#import timeit
import theano
import lasagne
import numpy as np
import theano.tensor as T
import lasagne.layers as layers
import lasagne.objectives as objectives

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import mpl_toolkits.axisartist as AA
from mpl_toolkits.axes_grid1 import host_subplot

from model import build_context_encoder
from model import build_discriminator

sys.path.insert(0, '/home2/ift6ed67/Project-IFT6266/CNN_Autoencoder')
from utils import shared_GPU_data
from utils import get_path
from utils import assemble
from utils import get_image

theano.config.floatX = 'float32'


def rolling_average(list, max_iter=100):
    y = []
    for i in range(len(list)):
        if i < max_iter:
            y.append(np.mean(list[:i + 1]))
        else:
            y.append(np.mean(list[i - max_iter:i + 1]))

    return y


def train_model(learning_rate_dis=0.0004, learning_rate_model=0.0004, n_epochs=40, batch_size=20):
    '''
            Function that compute the training of the model
            '''

    #######################
    # Loading the dataset #
    #######################

    print ('... Loading data')

    # Load the dataset on the CPU
    data_path = get_path()
    train_input_path = 'train_input_'
    train_target_path = 'train_target_'
    valid_input_path = 'valid_input_'
    valid_target_path = 'valid_target_'
    nb_train_batch = 8

    # Creating symbolic variables
    input_channel = 3
    max_height = 64
    max_width = 64
    min_height = 32
    min_width = 32
    # Shape = (100, 3, 64, 64)
    input = shared_GPU_data(shape=(batch_size, input_channel, max_height, max_width))
    # Shape = (100, 3, 32, 32)
    target = shared_GPU_data(shape=(batch_size, input_channel, min_height, min_width))

    ######################
    # Building the model #
    ######################

    # Symbolic variables
    # Shape = (_, 3, 64, 64)
    x = T.tensor4('x', dtype=theano.config.floatX)
    # Shape = (_, 3, 32, 32)
    y = T.tensor4('y', dtype=theano.config.floatX)
    # Shape = (_, 3, 32, 32)
    z = T.tensor4('x', dtype=theano.config.floatX)

    # Creation of the model
    model = build_context_encoder(input_var=None)
    discriminator = build_discriminator(input_var=None)

    fake_image = layers.get_output(model, inputs=x)
    fake_image_det = layers.get_output(model, inputs=x, deterministic=True)
    prob_real = layers.get_output(discriminator, inputs=y)
    prob_fake = layers.get_output(discriminator, inputs=fake_image)

    params_model = layers.get_all_params(model, trainable=True)
    params_dis = layers.get_all_params(discriminator, trainable=True)

    loss_real = -T.mean(T.log(prob_real))
    loss_fake = -T.mean(T.log(1 - prob_fake))
    loss_dis = 0.001 * (loss_real + loss_fake)

    loss_gen = -T.mean(T.log(prob_fake))
    recons_error = T.mean(objectives.squared_error(fake_image, z))
    loss_model = 0.001 * loss_gen + 0.999 * recons_error

    updates_dis = lasagne.updates.adam(loss_dis, params_dis, learning_rate=learning_rate_dis, beta1=0.5)
    updates_model = lasagne.updates.adam(loss_model, params_model, learning_rate=learning_rate_model, beta1=0.5)

    # Creation of theano functions
    train_dis = theano.function([], loss_dis, updates=updates_dis, allow_input_downcast=True,
                                givens={x: input, y: target})

    train_model = theano.function([], loss_model, updates=updates_model, allow_input_downcast=True,
                                  givens={x: input, z: target})

    predict_image = theano.function([], fake_image_det, allow_input_downcast=True, givens={x: input})

    ###################
    # Train the model #
    ###################

    print('... Training')

    epoch = 0
    nb_train_dis = 25
    nb_train_gen = 10
    nb_batch = 10000 // batch_size
    nb_block = nb_batch // nb_train_dis
    loss_dis = []
    loss_model = []

    idx = 50
    pred_batch = 5

    #start_time = timeit.default_timer()

    while (epoch < n_epochs):
        epoch = epoch + 1
        for i in range(nb_train_batch):
            #print (i)
            # Shape = (10000, 3, 64, 64) & Shape = (10000, 3, 32, 32)
            contour, center = get_image(data_path, train_input_path, train_target_path, str(i))
            for j in range(nb_block):
                #print (j)
                for index in range(nb_train_dis * j, nb_train_dis * (j + 1)):
                    #print (index)
                    input.set_value(contour[index * batch_size: (index + 1) * batch_size])
                    target.set_value(center[index * batch_size: (index + 1) * batch_size])
                    loss = train_dis()
                    loss_dis.append(loss)
                for index in range(nb_train_gen * j, nb_train_gen * (j + 1)):
                    #print (index)
                    input.set_value(contour[index * batch_size: (index + 1) * batch_size])
                    target.set_value(center[index * batch_size: (index + 1) * batch_size])
                    loss = train_model()
                    loss_model.append(loss)

        if epoch % 4 == 0:
            # save the model and a bunch of generated pictures
            print ('... saving model and generated images')

            np.savez('discriminator_epoch' + str(epoch) + '.npz', *layers.get_all_param_values(discriminator))
            np.savez('context_encoder_epoch' + str(epoch) + '.npz', *layers.get_all_param_values(model))
            np.save('loss_dis', loss_dis)
            np.save('loss_gen', loss_model)

            contour, center = get_image(data_path, valid_input_path, valid_target_path, str(0))
            input.set_value(contour[idx * pred_batch: (idx + 1) * pred_batch])
            generated_centers = predict_image()
            generated_images = assemble(contour[idx * pred_batch: (idx + 1) * pred_batch], generated_centers)

            for k in range(pred_batch):
                plt.subplot(1, pred_batch, (k + 1))
                plt.axis('off')
                plt.imshow(generated_images[k, :, :, :].transpose(1, 2, 0))

            plt.savefig('generated_images_epoch' + str(epoch) + '.png', bbox_inches='tight')

    #end_time = timeit.default_timer()

    # Plot the learning curve
    ax1 = host_subplot(111, axes_class=AA.Axes)
    plt.subplots_adjust(right=0.75)
    ax2 = ax1.twiny()

    x1 = range(1, len(loss_dis) + 1)
    ax1.set_xlim([x1[0], x1[-1]])
    x2 = range(1, len(loss_model) + 1)
    ax2.set_xlim([x2[0], x2[-1]])

    ax1.set_xlabel('training iteration (Discriminator)', color='g')
    ax2.set_xlabel('training iteration (Context encoder)', color='b')
    ax1.set_ylabel('Loss')

    ax1.plot(x1, rolling_average(loss_dis), 'g', label='Discriminator loss')
    ax2.plot(x2, rolling_average(loss_model), 'b', label='Context encoder Loss')

    ax1.grid(True)
    ax1.legend()

    plt.savefig('Learning_curve')

    print('Optimization complete.')
    #print('The code ran for %.2fm' % ((end_time - start_time) / 60.))


if __name__ == '__main__':
    train_model()
