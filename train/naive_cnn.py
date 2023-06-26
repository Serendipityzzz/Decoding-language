
import time
import copy as cp
import numpy as np
import tensorflow as tf
from sklearn import datasets
# local dep
if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.pardir)
import models, utils

__all__ = [
    "train",
]

# Global variables.
params = None; paths = None

"""
init funcs
"""
# def init func
def init(base_, params_):
    """
    Initialize `naive_cnn` training variables.
    :param base_: The base path of current project.
    :param params_: The parameters of current training process.
    """
    global params, paths
    # Initialize params.
    params = cp.deepcopy(params_)
    paths = utils.Paths.Paths(base=base_, params=params)
    # Initialize model.
    _init_model()
    # Initialize training process.
    _init_train()

# def _init_model func
def _init_model():
    """
    Initialize model used in the training process.
    """
    global params
    ## Initialize tf configuration.
    # Not set random seed, should be done before instantiating `model`.
    # Set default precision.
    tf.keras.backend.set_floatx(params._precision)
    # Check whether run in graph mode or eager mode.
    tf.config.run_functions_eagerly(not params.train.use_graph_mode)

# def _init_train func
def _init_train():
    """
    Initialize the training process.
    """
    pass

"""
data funcs
"""
# def load_data func
def load_data(load_params):
    """
    Load data from specified dataset.
    :param load_params: DotDict - The load parameters of specified dataset.
    :return dataset_train_: tf.data.Dataset - The input train dataset.
    :return dataset_test_: tf.data.Dataset - The input test dataset.
    """
    global params
    # Load data from specified dataset.
    try:
        func = getattr(sys.modules[__name__], "_".join(["_load_data", params.train.dataset]))
        dataset_train_, dataset_test_ = func(load_params)
    except Exception:
        raise ValueError("ERROR: Unknown dataset type {} in train.naive_cnn.".format(params.train.dataset))
    # Return the final `dataset_train_` & `dataset_test_`.
    return dataset_train_, dataset_test_

# def _load_data_toy func
def _load_data_toy(load_params):
    """
    Load data from `sklearn.datasets`.
    :param load_params: DotDict - The load parameters of specified dataset.
        - n_labels: int - The number of labels.
    :return dataset_train_: (1[list],) - The input train dataset.
    :return dataset_test_: (1[list],) - The input test dataset.
    """
    global params
    # Initialize n_labels.
    n_labels = load_params.n_labels
    # Generate a random n-class classification problem.
    # X - (n_samples, n_features), y - (n_samples, n_labels)
    n_informative = int(np.ceil(np.log2(n_labels)))
    n_redundant = 0; n_repeated = 0; n_random = 0; n_features = n_informative + n_redundant + n_repeated + n_random
    X, y = datasets.make_classification(
        n_samples=1000, n_features=n_features,
        n_informative=n_informative, n_redundant=n_redundant, n_repeated=n_repeated,
        n_clusters_per_class=1, n_classes=n_labels
    ); X = np.expand_dims(X, axis=-1).astype(np.float32); y = np.eye(len(set(y)))[y].astype(np.float32)
    # Construct [train,test] dataset from mnist dataset, and downsample sequence data X.
    train_ratio = params.train.train_ratio
    X_train = X[:int(train_ratio*X.shape[0]),:,:]; y_train = y[:int(train_ratio*y.shape[0]),:]
    X_test = X[int(train_ratio*X.shape[0]):,:,:]; y_test = y[int(train_ratio*y.shape[0]):,:]
    # Return the final `dataset_train_` & `dataset_test_`.
    return (X_train, y_train), (X_test, y_test)

# def _load_data_mnist func
def _load_data_mnist(load_params):
    """
    Load data from `mnist` dataset.
    :param load_params: DotDict - The load parameters of specified dataset.
        - resample_rate: int - The rate of re-sample, and the original sample rate is 28Hz (supposed).
    :return dataset_train_: ((seq_len/downsample_rate)[list],) - The input train dataset.
    :return dataset_test_: ((seq_len/downsample_rate)[list],) - The input test dataset.
    """
    # Initialize resample_rate.
    resample_rate = load_params.resample_rate
    # Initialize sample_rate, and get the corresponding downsample_rate.
    sample_rate = 28; assert sample_rate / resample_rate == sample_rate // resample_rate
    downsample_rate = sample_rate // resample_rate
    # Load data from `mnist` dataset.
    # train_data - (n_train, 28, 28), train_label - (n_train,)
    # test_data - (n_test, 28, 28), train_label - (n_test,)
    (train_data, train_label), (test_data, test_label) = tf.keras.datasets.mnist.load_data()
    # Construct train dataset from mnist dataset, and downsample sequence data X.
    X_train = train_data.astype(np.float32); y_train = np.eye(len(set(np.squeeze(train_label))))[train_label].astype(np.float32)
    X_train = (X_train - np.min(X_train)) / (np.max(X_train) - np.min(X_train))
    assert X_train.shape[1] / downsample_rate == X_train.shape[1] // downsample_rate
    X_train = np.concatenate([X_train[:,np.arange(start_i, X_train.shape[1], downsample_rate),:]\
        for start_i in range(downsample_rate)], axis=0)
    y_train = np.concatenate([y_train for _ in range(downsample_rate)], axis=0)
    # Construct test dataset from mnist dataset, and downsample sequence data X.
    X_test = test_data.astype(np.float32); y_test = np.eye(len(set(np.squeeze(test_label))))[test_label].astype(np.float32)
    X_test = (X_test - np.min(X_test)) / (np.max(X_test) - np.min(X_test))
    assert X_test.shape[1] / downsample_rate == X_test.shape[1] // downsample_rate
    X_test = np.concatenate([X_test[:,np.arange(start_i, X_test.shape[1], downsample_rate),:]\
        for start_i in range(downsample_rate)], axis=0)
    y_test = np.concatenate([y_test for _ in range(downsample_rate)], axis=0)
    # Return the final `dataset_train_` & `dataset_test_`.
    return (X_train, y_train), (X_test, y_test)

# def _load_data_meg_liu2019cell func
def _load_data_meg_liu2019cell(load_params):
    """
    Load data from `meg_liu2019cell` dataset.
    :param load_params: DotDict - The load parameters of specified dataset.
        - resample_rate: int - The rate of re-sample, and the original sample rate is 600Hz. We should note
            that the duration of replay is about 30ms ~ 40ms, which corresponds to 18 ~ 24 sample points in the
            original sample rate setting. And we assume that replay is time-compressed neural activity, e.g.
            compress the original 1s neural activity to 30ms ~ 40ms, thus we need the resample_rate to be in 18~24Hz.
        - subjects_allowed: list - The indices of allowed subjects.
    :return dataset_train_: ((seq_len/downsample_rate)[list],) - The input train dataset.
    :return dataset_test_: ((seq_len/downsample_rate)[list],) - The input test dataset.
    """
    global params, paths
    # Initialize resample_rate & subjects_allowed.
    resample_rate = load_params.resample_rate; subjects_allowed = load_params.subjects_allowed
    # Initialize path_data & subjects_allowed.
    path_data = os.path.join(paths.base, "data", "meg.liu2019cell"); subjects_allowed = subjects_allowed
    # Initialize sample_rate, and get the corresponding downsample_rate.
    sample_rate = 600; assert sample_rate / resample_rate == sample_rate // resample_rate
    downsample_rate = sample_rate // resample_rate
    # Load data from `meg_liu2019cell` dataset.
    # data - (n_samples[list],)
    data = utils.data.meg.meg_liu2019cell.load_meg_liu2019cell(
        path_data=path_data, subjects_allowed=subjects_allowed
    ); np.random.shuffle(data)
    # Initialize X, then do cross-trial normalization.
    # X - (n_samples, seq_len, n_channels)
    X = np.array([data_i.data for data_i in data], dtype=np.float32)[:,1800:,:]
    X = (X - np.min(X, axis=0)) / (np.max(X, axis=0) - np.min(X, axis=0))
    # Initialize y, then transform y to one-hot encoding.
    # y - (n_samples, n_labels)
    labels = list(set([data_i.label for data_i in data])); labels.sort(); assert len(labels) == 8
    y = np.array([labels.index(data_i.label) for data_i in data], dtype=np.int64)
    y = np.eye(len(labels))[y]
    # Construct train dataset from mnist dataset, and downsample sequence data X.
    train_ratio = params.train.train_ratio
    X_train = X[:int(train_ratio*X.shape[0]),:,:]; y_train = y[:int(train_ratio*y.shape[0]),:]
    assert X_train.shape[1] / downsample_rate == X_train.shape[1] // downsample_rate
    X_train = np.concatenate([X_train[:,np.arange(start_i, X_train.shape[1], downsample_rate),:]\
        for start_i in range(downsample_rate)], axis=0)
    y_train = np.concatenate([y_train for _ in range(downsample_rate)], axis=0)
    # Construct test dataset from mnist dataset, and downsample sequence data X.
    X_test = X[int(train_ratio*X.shape[0]):,:,:]; y_test = y[int(train_ratio*y.shape[0]):,:]
    assert X_test.shape[1] / downsample_rate == X_test.shape[1] // downsample_rate
    X_test = np.concatenate([X_test[:,np.arange(start_i, X_test.shape[1], downsample_rate),:]\
        for start_i in range(downsample_rate)], axis=0)
    y_test = np.concatenate([y_test for _ in range(downsample_rate)], axis=0)
    # Return the final `dataset_train_` & `dataset_test_`.
    return (X_train, y_train), (X_test, y_test)

"""
train funcs
"""
# def train func
def train(base_, params_):
    """
    Train the model.
    :param base_: The base path of current project.
    :param params_: The parameters of current training process.
    """
    global params, paths
    # Initialize parameters & variables of current training process.
    init(base_, params_)
    # Log the start of current training process.
    paths.run.logger.summaries.info("Training started with dataset {}.".format(params.train.dataset))
    # Initialize load_params. Each load_params_i corresponds to a sub-dataset.
    if params.train.dataset == "meg_liu2019cell":
        load_params = [utils.DotDict({
            "resample_rate": 75,
            "subjects_allowed": [subject_idx,],
        }) for subject_idx in range(43)]
    elif params.train.dataset == "eeg":
        load_params = [utils.DotDict({"downsample_rate":5,}),]
    elif params.train.dataset == "mnist":
        load_params = [utils.DotDict({"downsample_rate":2,}),]
    elif params.train.dataset == "toy":
        load_params = [utils.DotDict({"n_labels":8,}),]
    else:
        raise ValueError("ERROR: Unknown dataset {} in train.naive_cnn.".format(params.train.dataset))
    for dataset_idx, load_params_i in enumerate(load_params):
        # Load data from specified sub-dataset.
        dataset_train, dataset_test = load_data(load_params_i)
        # Start training process of current specified sub-dataset.
        paths.run.logger.summaries.info("Start the training process of sub-dataset {:d}.".format(dataset_idx))

        # Train the model for each time segment.
        accuracy = []

        # Initialize model of current time segment.
        model = models.naive_cnn(params.model)
        for epoch_idx in range(params.train.n_epochs):
            # Record the start time of preparing data.
            time_start = time.time()
            # Fit the model using [X_train,y_train].
            model.fit(dataset_train[0], dataset_train[1], epochs=1, batch_size=params.train.batch_size)
            # Predict the corresponding `y_pred` of `X_test`.
            _, accuracy_i = model.evaluate(dataset_test[0], dataset_test[1]); accuracy.append(accuracy_i)
            # Record current time segment.
            time_stop = time.time()
            msg = (
                "Finish epoch {:d} in {:.2f} seconds, with accuracy {:.2f}%."
            ).format(epoch_idx, time_stop-time_start, accuracy_i*100.)
            print(msg); paths.run.logger.summaries.info(msg)
        # Finish training process of current specified sub-dataset.
        paths.run.logger.summaries.info((
            "Finish the training process of sub-dataset {:d}, with max accuracy {:.2f}% at time point {:d}."
        ).format(dataset_idx, np.max(accuracy)*100., np.argmax(accuracy)))
    # Log the end of current training process.
    paths.run.logger.summaries.info("Training finished with dataset {}.".format(params.train.dataset))

if __name__ == "__main__":
    import os
    # local dep
    from params import naive_cnn_params

    # macro
    dataset = "meg_liu2019cell"

    # Initialize random seed.
    utils.model.set_seeds(42)

    ## Instantiate naive_cnn.
    # Initialize base.
    base = os.path.join(os.getcwd(), os.pardir)
    # Instantiate naive_cnn_params.
    naive_cnn_params_inst = naive_cnn_params(dataset=dataset)
    # Train naive_cnn.
    train(base, naive_cnn_params_inst)
