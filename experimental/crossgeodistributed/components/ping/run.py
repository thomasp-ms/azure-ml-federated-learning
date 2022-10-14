"""
Ray run example using shrike.distributed.shrike_ray
"""
import logging
import time
import os
import sys

# Import libraries
import netifaces
from azureml.core import Run
import pythonping

# add local dir for local imports
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from common import service_bus_remote


def main():
    # use the init() method to let shrike.distributed
    # initialize the VMs for you

    # requires either a secret in the AzureML environment named SERVICEBUS_CONNSTR (safe)
    # or an environment variable SERVICEBUS_CONNSTR (unsafe)
    remote_cluster_config = service_bus_remote.init()

    if remote_cluster_config.main_node:
        logging.info(f"Running on head node")
    else:
        logging.info("Running on cluster node")

    # run = Run.get_context()
    # run.parent.log("node_ready", session.world_rank)

    for k in os.environ:
        logging.info("ENV: {}={}".format(k, os.environ[k]))

    for interface in netifaces.interfaces():
        logging.info("IFADDR: {}".format(netifaces.ifaddresses(str(interface))))

    # ping the head node
    logging.info("Pinging head node")
    logging.info("Head node address: {}".format(remote_cluster_config.head))
    response_list = pythonping.ping(remote_cluster_config.head, count=100)
    for response in response_list:
        logging.info(response)
    
    print("RTT AVG (ms): {}".format(response_list.rtt_avg_ms))

    if remote_cluster_config.main_node:
        for i in range(10):
            logging.info(f"Pretending to be doing something {i}")
            time.sleep(60)

    # calling shutdown() on head node will actually shutdown the job
    # on cluster nodes, it will wait head node signal to teardown properly
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
