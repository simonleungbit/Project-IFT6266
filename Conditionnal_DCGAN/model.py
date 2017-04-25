"""
        Implementation of a CNN autoencoder
        """

import lasagne
import lasagne.layers as layers
from lasagne.nonlinearities import tanh
from lasagne.nonlinearities import rectify
from lasagne.nonlinearities import sigmoid
from lasagne.nonlinearities import LeakyRectify


#########################
# Layers implementation #
#########################

def initialize_parameters():
    W = lasagne.init.Normal(std=0.02)
    b = lasagne.init.Constant(0.)

    return [W, b]


class InputLayer(object):
    def __init__(self, shape, input_var=None):
        """
                Input of the Network

                """

        self.output = layers.InputLayer(shape, input_var=input_var)


class DenseLayer(object):
    def __init__(self, input, num_units, activation=rectify):
        """
                Typical hidden layer of a MLP: units are fully-connected

                NOTE : The non linearity used here is relu

                """

        self.input = input
        self.output = layers.DenseLayer(self.input, num_units, W=initialize_parameters()[0],
                                        b=initialize_parameters()[1],
                                        nonlinearity=activation)


class ConvLayer(object):
    def __init__(self, input, num_filters, filter_size, stride=(2, 2), pad=(0, 0),
                 activation=LeakyRectify(leakiness=0.2)):
        """
                Allocate a ConvLayer with shared variable internal parameters

                """

        self.input = input
        self.output = layers.Conv2DLayer(self.input, num_filters, filter_size, stride=stride, pad=pad,
                                         W=initialize_parameters()[0], b=initialize_parameters()[1],
                                         nonlinearity=activation)


class TransposedConvLayer(object):
    def __init__(self, input, num_filters, filter_size, stride=(2, 2), padding=(0, 0), activation=rectify):
        """
                Allocate a TransposedConvLayer with shared variable internal parameters.

                """

        self.input = input
        self.output = layers.TransposedConv2DLayer(self.input, num_filters, filter_size, stride=stride, crop=padding,
                                                   W=initialize_parameters()[0], b=initialize_parameters()[1],
                                                   nonlinearity=activation)


def build_context_encoder(input_var=None, nfilters=[64, 128, 256, 512, 4000, 512, 256, 128, 3],
                          filter_size=[2, 2, 2, 2, 4, 4, 2, 2, 2, 2], input_channels=3):

    ###############################
    # Build Network Configuration #
    ###############################

    print ('... Building the generator')

    # Input of the network : shape = (batch_size, 3, 64, 64)
    input_layer = InputLayer(shape=(None, input_channels, 64, 64), input_var=input_var)

    # Conv layer : output.shape = (batch_size, 64, 32, 32)
    conv_layer1 = ConvLayer(input_layer.output, num_filters=nfilters[0], filter_size=filter_size[0])

    # Conv layer : output.shape = (batch_size, 128, 16, 16)
    conv_layer2 = ConvLayer(layers.batch_norm(conv_layer1.output), num_filters=nfilters[1], filter_size=filter_size[1])

    # Conv layer : output.shape = (batch_size, 256, 8, 8)
    conv_layer3 = ConvLayer(layers.batch_norm(conv_layer2.output), num_filters=nfilters[2], filter_size=filter_size[2])

    # Conv layer : output.shape = (batch_size, 512, 4, 4)
    conv_layer4 = ConvLayer(layers.batch_norm(conv_layer3.output), num_filters=nfilters[3], filter_size=filter_size[3])

    # Conv layer : output.shape = (batch_size, 4000, 1, 1)
    conv_layer5 = ConvLayer(layers.batch_norm(conv_layer4.output), num_filters=nfilters[4], filter_size=filter_size[4])

    # Tranposed conv layer : output.shape = (batch_size, 512, 4, 4)
    transconv_layer1 = TransposedConvLayer(layers.batch_norm(conv_layer5.output), num_filters=nfilters[5],
                                           filter_size=filter_size[5])

    # Tranposed conv layer : output.shape = (batch_size, 256, 8, 8)
    transconv_layer2 = TransposedConvLayer(layers.batch_norm(transconv_layer1.output), num_filters=nfilters[6],
                                           filter_size=filter_size[6])

    # Tranposed conv layer : output.shape = (batch_size, 128, 16, 16)
    transconv_layer3 = TransposedConvLayer(layers.batch_norm(transconv_layer2.output), num_filters=nfilters[7],
                                           filter_size=filter_size[7])

    # Tranposed conv layer : output.shape = (batch_size, 3, 32, 32)
    transconv_layer4 = TransposedConvLayer(layers.batch_norm(transconv_layer3.output), num_filters=nfilters[8],
                                           filter_size=filter_size[8], activation=tanh)

    return transconv_layer4.output


def build_discriminator(input_var=None, nfilters=[128, 256, 512], filter_size=[2, 2, 2], input_channels=3):

    ###############################
    # Build Network Configuration #
    ###############################

    print ('... Building the discriminator')

    # Input of the network : shape = (batch_size, 3, 32, 32)
    input_layer = InputLayer(shape=(None, input_channels, 32, 32), input_var=input_var)

    # Conv layer : output.shape = (batch_size, 128, 16, 16)
    conv_layer1 = ConvLayer(input_layer.output, num_filters=nfilters[0], filter_size=filter_size[0])

    # Conv layer : output.shape = (batch_size, 256, 8, 8)
    conv_layer2 = ConvLayer(layers.batch_norm(conv_layer1.output), num_filters=nfilters[1], filter_size=filter_size[1])

    # Conv layer : output.shape = (batch_size, 512, 4, 4)
    conv_layer3 = ConvLayer(layers.batch_norm(conv_layer2.output), num_filters=nfilters[2], filter_size=filter_size[2])

    # Dense Layer : output.shape = (batch_size, 1)
    dense_layer = DenseLayer(layers.FlattenLayer(layers.batch_norm(conv_layer3.output)), num_units=1,
                             activation=sigmoid)

    return layers.batch_norm(dense_layer.output)