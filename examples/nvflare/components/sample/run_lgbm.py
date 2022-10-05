"""
Ray run example using shrike.distributed.shrike_ray
"""
import logging
import time
import os
import sys
import traceback

import argparse
from azureml.core import Run
import netifaces

# add local dir for local testing
sys.path.append(os.path.join(os.path.dirname(__file__), "."))

from helper import service_bus_remote


############################
### SAMPLE TRAINING CODE ###
############################

# see code from https://www.datatechnotes.com/2022/03/lightgbm-classification-example-in.html

import lightgbm as lgb
from sklearn.datasets import load_iris
from sklearn.metrics import classification_report
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import train_test_split
from pandas import DataFrame
from numpy import argmax 

def run(rank, size, head, workers, local_ip):
    iris = load_iris()
    x, y = iris.data, iris.target

    x_df = DataFrame(x, columns= iris.feature_names)
    x_train, x_test, y_train, y_test = train_test_split(x_df, y, test_size=0.15)

    # defining parameters
    params = {
        'boosting': 'gbdt',
        'objective': 'multiclass',
        'num_leaves': 10,
        'num_class': 3
    }
    
    # multinode params
    params['num_machines'] = size
    main_port = 23456
    if rank == 0:
        machines = ",".join(
            [f"{head}:{main_port}"] + [f"{worker}:{main_port+i+1}" for i,worker in enumerate(workers)],
        )
    else:
        machines = ",".join([
            f"{head}:{main_port}",
            f"{local_ip}:{main_port+rank}"
        ])
    params['machines'] = machines
    params['local_listen_port'] = main_port+rank

    logging.info(f"Params: {params}")
    # loading data
    lgb_train = lgb.Dataset(x_train, y_train, params=params).construct()
    lgb_eval = lgb.Dataset(x_test, y_test, reference=lgb_train).construct()

    # fitting the model
    model = lgb.train(params,
                    train_set=lgb_train,
                    valid_sets=lgb_eval)

    # prediction
    y_pred = model.predict(x_test)

    y_pred = argmax(y_pred, axis=1)
    cr = classification_report(y_test, y_pred)
    cm = confusion_matrix(y_test, y_pred)
    
    print(cr)
    print(cm) 
    
###########################
### REMOTE CLUSTER MAIN ###
###########################

def main():
    # use the init() method to let shrike.distributed
    # initialize the VMs for you

    # requires either a secret in the AzureML environment named SERVICEBUS_CONNSTR (safe)
    # or an environment variable SERVICEBUS_CONNSTR (unsafe)
    remote_cluster_config = service_bus_remote.init()

    if remote_cluster_config.main_node:
        logging.info(f"Running on head node")
    else:
        logging.info("Running on cluster node with head located at {}".format(remote_cluster_config.head))

    logging.info(f"Remote cluster config: {remote_cluster_config}")

    # for k in os.environ:
    #     logging.info("ENV: {}={}".format(k, os.environ[k]))

    for interface in netifaces.interfaces():
        logging.info("IFADDR: {}".format(netifaces.ifaddresses(str(interface))))

    # calling shutdown() on head node will actually shutdown the job
    # on cluster nodes, it will wait head node signal to teardown properly

    try:
        run(
            rank=remote_cluster_config.world_rank,
            size=remote_cluster_config.world_size,
            head=remote_cluster_config.head,
            workers=remote_cluster_config.workers,
            local_ip=remote_cluster_config.local_ip,
        )
    except:
        raise Exception("Failed to run mnist: {}".format(traceback.format_exc()))

    service_bus_remote.shutdown()


def set_logging(logger_name=None, level=logging.INFO):
    # initialize root logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s : %(levelname)s : %(name)s : %(message)s"
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


if __name__ == "__main__":
    set_logging(logger_name="service_bus_driver", level=logging.INFO)
    set_logging(logger_name="service_bus_remote", level=logging.INFO)
    set_logging(logger_name=__name__, level=logging.INFO)
    set_logging(logger_name=None, level=logging.WARN)
    main()
