# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""
The best thing I wrote so far :-D
"""
import logging
import subprocess
from typing import Any, List
import uuid
import time
import argparse
import socket
from dataclasses import dataclass

from shrike._core import experimental
from shrike.distributed import EXPERIMENTAL_WARNING_MSG
from shrike.distributed.cluster_auto_setup import ClusterAutoSetupHandler

from .service_bus_driver import ServiceBusMPILikeDriver


class ServiceBusRemoteClusterAutoSetup(ClusterAutoSetupHandler):
    def __init__(
        self,
        world_size: int,
        world_rank: int,
        topic: str,
        subscription: str = None,
        sb_host: str = None,
        auth_method: str = "SystemAssigned",
    ):
        """Constructor"""
        self.logger = logging.getLogger(__name__)

        # keep those for initialization later
        self.multinode_driver = ServiceBusMPILikeDriver(
            world_size=world_size,
            world_rank=world_rank,
            topic=topic,
            subscription=subscription,
            sb_host=sb_host,
            auth_method=auth_method,
            allowed_tags=[
                ClusterAutoSetupHandler.COMM_TAG_CLUSTER_SETUP,
                ClusterAutoSetupHandler.COMM_TAG_SETUP_FINISHED,
                ClusterAutoSetupHandler.COMM_TAG_CLUSTER_SHUTDOWN,
            ],
        )

        # this will be used to collect cluster config
        self._setup_config = {}

        # network config
        local_hostname = socket.gethostname()
        self.local_ip = socket.gethostbyname(local_hostname)
        self.logger.info(f"Detected IP from socket.gethostbyname(): {self.local_ip}")

        self.head_address = "127.0.0.1"
        self.workers = []


    #################
    # SETUP METHODS #
    #################

    def setup_local(self):
        """Setup method if custom_sync_setup=False"""
        self.logger.info(f"{self.__class__.__name__}.setup_local() called.")

    def setup_head_node(self):
        """Setup to run only on head node"""
        self.logger.info(
            f"{self.__class__.__name__}.setup_head_node() called to set up HEAD node."
        )
        self.setup_config_add_key("_session_id", str(uuid.uuid4()))

        # create setup config
        self.head_address = self.local_ip

        # record what's needed to setup cluster nodes
        self.setup_config_add_key("head_address", self.head_address)

    def setup_cluster_node(self):
        """Setup to run only on non-head cluster nodes"""
        self.logger.info(f"{self.__class__.__name__}.setup_cluster_node() called.")
        self.head_address = self.setup_config_get_key("head_address")

    def head_node_teardown(self):
        """Un-setup a cluster node"""
        self.logger.info(f"{self.__class__.__name__}.head_node_teardown() called.")
        self.multinode_driver.flush_recv()

    def cluster_node_teardown(self):
        """Un-setup a cluster node"""
        self.logger.info(f"{self.__class__.__name__}.cluster_node_teardown() called.")
        self.multinode_driver.flush_recv()

    ############
    # MPI COMM #
    ############

    # those are simulated by service bus thanks to our fake driver

    def wait_on_nodes_setup_ready(self):
        """[HEAD only] Waits for each node to report completion of their setup"""
        self.logger.info("Checking setup status from each node...")

        # loop on each node in the world and wait for status
        for i in range(1, self.multinode_driver.get_multinode_config().world_size):
            status = self.multinode_driver.get_comm().recv(
                source=i, tag=ClusterAutoSetupHandler.COMM_TAG_SETUP_FINISHED
            )
            self.logger.info(f"Node #{i} status received: {status}")

            if isinstance(status, dict):
                if status["status"] != "OK":
                    raise RuntimeError(
                        f"Node #{i} failed to setup. Status: {status}"
                    )
                self.workers.append(status["local_ip"])
            else:
                raise RuntimeError(f"Node #{i} failed to setup, status=={status}.")

    def report_node_setup_complete(self):
        """[NODE only] Report to head that this node setup is complete"""
        self.logger.info("Reporting status OK to head node.")
        self.multinode_driver.get_comm().send(
            { 'local_ip': self.local_ip, 'status': "OK" }, 0, tag=ClusterAutoSetupHandler.COMM_TAG_SETUP_FINISHED
        )

    def non_block_wait_for_shutdown(self):
        """[NODE only] Checks if head node has sent shutdown message"""
        shutdown_msg = self.multinode_driver.get_comm().iprobe(
            source=0, tag=ClusterAutoSetupHandler.COMM_TAG_CLUSTER_SHUTDOWN
        )
        if shutdown_msg == "SHUTDOWN":
            return shutdown_msg
        else:
            self.logger.info(
                "Received a message that is not shutdown on the shutdown tag."
            )
            return None


###########################
# USER FRIENDLY FUNCTIONS #
###########################

_SETUP_HANDLER = None


@dataclass
class RemoteClusterConfig:
    world_size: int
    world_rank: int
    main_node: bool
    multinode_available: bool
    head: str
    workers: List[str]
    local_ip: str


@experimental(EXPERIMENTAL_WARNING_MSG)
def init() -> Any:
    """User-friendly function to initialize the script using ServiceBusRemoteClusterAutoSetup"""
    global _SETUP_HANDLER

    # run the script
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sb_auth",
        type=str,
        choices=["ManagedIdentity", "ConnectionString"],
        required=False,
        default="SystemAssigned",
    )
    parser.add_argument("--sb_host", type=str, required=False, default=None)
    parser.add_argument("--sb_size", type=int, required=True)
    parser.add_argument("--sb_rank", type=int, required=True)
    parser.add_argument("--sb_topic", type=str, required=True)
    parser.add_argument("--sb_sub", type=str, required=False)
    args, _ = parser.parse_known_args()

    _SETUP_HANDLER = ServiceBusRemoteClusterAutoSetup(
        world_size=args.sb_size,
        world_rank=args.sb_rank,
        topic=args.sb_topic,
        subscription=args.sb_sub,
        sb_host=args.sb_host,
        auth_method=args.sb_auth,
    )
    _SETUP_HANDLER.initialize_run()

    return RemoteClusterConfig(
        world_size=_SETUP_HANDLER.multinode_driver.get_multinode_config().world_size,
        world_rank=_SETUP_HANDLER.multinode_driver.get_multinode_config().world_rank,
        main_node=_SETUP_HANDLER.multinode_driver.get_multinode_config().main_node,
        multinode_available=_SETUP_HANDLER.multinode_driver.get_multinode_config().multinode_available,
        head=_SETUP_HANDLER.head_address,
        workers=_SETUP_HANDLER.workers,
        local_ip=_SETUP_HANDLER.local_ip,
    )


@experimental(EXPERIMENTAL_WARNING_MSG)
def shutdown():
    """User-friendly function to teardown the script using ServiceBusRemoteClusterAutoSetup"""
    global _SETUP_HANDLER
    if _SETUP_HANDLER is not None:
        _SETUP_HANDLER.finalize_run()


# for local test only
def _main():
    # initialize root logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s : %(levelname)s : %(name)s : %(message)s"
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    session = init()

    if session:
        print(f"Running on head node")
    else:
        print("Running on cluster node")

    shutdown()


if __name__ == "__main__":
    _main()
