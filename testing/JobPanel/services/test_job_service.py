from JobPanel.backend.service_base import ServiceBase, ServiceStatus
from testing.JobPanel.mock.passwords import get_test_password
from .port_forwarder import PortForwarder
from gm_base.global_const import GEOMOP_INTERNAL_DIR_NAME

import threading
import os
import shutil
import time
import logging
import pytest

logging.basicConfig(filename='test_job_service.log', filemode='w', level=logging.INFO)


this_source_dir = os.path.dirname(os.path.realpath(__file__))
geomop_root_local = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(this_source_dir))), "src")

TEST_FILES = "test_files"
REMOTE_WORKSPACE = "/home/test/workspace"


@pytest.mark.slow
def test_correct_run(request):
    local_service = None
    local_service_thread = None

    def finalizer():
        # stopping, closing
        if local_service_thread is not None:
            local_service._closing = True
            local_service_thread.join(timeout=5)
            assert not local_service_thread.is_alive()

        shutil.rmtree(TEST_FILES, ignore_errors=True)
    request.addfinalizer(finalizer)

    # create analysis and job workspaces
    os.makedirs(os.path.join(TEST_FILES, "workspace/job"), exist_ok=True)

    # local service
    env = {"__class__": "Environment",
           "geomop_root": geomop_root_local,
           "geomop_analysis_workspace": os.path.abspath(os.path.join(TEST_FILES, "workspace")),
           "python": "python3"}
    cl = {"__class__": "ConnectionLocal",
          "address": "localhost",
          "environment": env,
          "name": "local"}
    local_service = ServiceBase({"service_host_connection": cl})
    local_service_thread = threading.Thread(target=local_service.run, daemon=True)
    local_service_thread.start()

    # job data
    pe = {"__class__": "ProcessExec",
          "executable": {"__class__": "Executable",
                         "path": "JobPanel/services/job_service.py",
                         "script": True}}
    je = {"__class__": "Executable",
          "path": os.path.join(this_source_dir, "job_1.py"),
          "script": True}
    service_data = {"service_host_connection": cl,
                    "process": pe,
                    "job_executable": je,
                    "workspace": "job",
                    "config_file_name": GEOMOP_INTERNAL_DIR_NAME + "/job_service.conf",
                    "wait_before_run": 10.0}

    # start job
    local_service.request_start_child(service_data)
    job = local_service._child_services[1]

    # check correct job state transition
    time.sleep(5)
    assert job._status == ServiceStatus.queued
    time.sleep(10)
    assert job._status == ServiceStatus.running
    time.sleep(30)
    assert job._status == ServiceStatus.done


@pytest.mark.slow
@pytest.mark.ssh
def test_correct_run_connection_fail(request):
    local_service = None
    local_service_thread = None
    port_forwarder = None

    def finalizer():
        # stopping, closing
        if port_forwarder is not None:
            port_forwarder.close_all_forwarded_ports()

        if local_service_thread is not None:
            local_service._closing = True
            local_service_thread.join(timeout=5)
            assert not local_service_thread.is_alive()

        shutil.rmtree(TEST_FILES, ignore_errors=True)
    request.addfinalizer(finalizer)

    # create analysis and job workspaces
    os.makedirs(os.path.join(TEST_FILES, "workspace/job"), exist_ok=True)

    # local service
    env = {"__class__": "Environment",
           "geomop_root": geomop_root_local,
           "geomop_analysis_workspace": os.path.abspath(os.path.join(TEST_FILES, "workspace")),
           "python": "python3"}
    cl = {"__class__": "ConnectionLocal",
          "address": "localhost",
          "environment": env,
          "name": "local"}
    local_service = ServiceBase({"service_host_connection": cl})
    local_service_thread = threading.Thread(target=local_service.run, daemon=True)
    local_service_thread.start()

    # port forwarder
    port_forwarder = PortForwarder()
    forwarded_port = port_forwarder.forward_port(22)

    # job data
    env_rem = {"__class__": "Environment",
               "geomop_root": geomop_root_local,
               "geomop_analysis_workspace": REMOTE_WORKSPACE,
               "python": "python3"}
    u, p = get_test_password()
    cr = {"__class__": "ConnectionSSH",
          "address": "localhost",
          "port": forwarded_port,
          "uid": u,
          "password": p,
          "environment": env_rem,
          "name": "remote"}
    pe = {"__class__": "ProcessExec",
          "executable": {"__class__": "Executable",
                         "path": "JobPanel/services/job_service.py",
                         "script": True}}
    je = {"__class__": "Executable",
          "path": os.path.join(this_source_dir, "job_1.py"),
          "script": True}
    service_data = {"service_host_connection": cr,
                    "process": pe,
                    "job_executable": je,
                    "workspace": "job",
                    "config_file_name": GEOMOP_INTERNAL_DIR_NAME + "/job_service.conf",
                    "wait_before_run": 15.0}

    # start job
    local_service.request_start_child(service_data)
    #print(local_service._child_services.keys())
    job = local_service._child_services[2]

    # check correct job state transition
    time.sleep(5)
    port_forwarder.discard_data = True
    time.sleep(5)
    port_forwarder.discard_data = False
    time.sleep(10)
    assert job._status == ServiceStatus.running
    time.sleep(5)
    port_forwarder.discard_data = True
    time.sleep(5)
    port_forwarder.discard_data = False
    time.sleep(10)
    assert job._status == ServiceStatus.running
    assert job._online
    time.sleep(10)
    assert job._status == ServiceStatus.done
