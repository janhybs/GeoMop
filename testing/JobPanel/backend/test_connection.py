# prerequisites for this tests:
# 1: on machine must be user "test" with ssh keys set for user which runs tests (or password in secret file)
# 2: directory "/home/test/test_dir" must be writable for user which runs tests

# TODO: Run in Tox virtual environment, try to set $HOME to a test directory and setup prerequisities

from JobPanel.backend.connection import *
from JobPanel.backend.service_base import ServiceBase, ServiceStatus
from JobPanel.backend.service_proxy import ServiceProxy
from testing.JobPanel.mock.passwords import get_test_password, get_passwords

import threading
import socket
import socketserver
import os
import shutil
import logging
import time
import stat
import pytest

logging.basicConfig(filename='test_connection.log', filemode='w', level=logging.INFO)


this_source_dir = os.path.dirname(os.path.realpath(__file__))
geomop_root_local = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(this_source_dir))), "src")

TEST_FILES = "test_files"
REMOTE_WORKSPACE = "/home/test/workspace"


@pytest.mark.ssh
@pytest.mark.slow
def test_port_forwarding(request):
    server = None
    server_thread = None
    local_service = None
    local_service_thread = None

    def finalizer():
        # stopping, closing
        if local_service_thread is not None:
            local_service._closing = True
            local_service_thread.join(timeout=5)
            assert not local_service_thread.is_alive()

        # shutdown server
        if server_thread is not None:
            server.shutdown()
            server.server_close()
            server_thread.join(timeout=5)
            assert not server_thread.is_alive()

        shutil.rmtree(TEST_FILES, ignore_errors=True)
    request.addfinalizer(finalizer)

    class Server(socketserver.ThreadingTCPServer):
        daemon_threads = True
        allow_reuse_address = True

    class RequestHandler(socketserver.BaseRequestHandler):
        def handle(self):
            data = str(self.request.recv(1024), 'ascii')
            if data == "hello":
                self.request.sendall(bytes("hello", 'ascii'))

    def connection_test(ip, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ip, port))
        try:
            sock.sendall(bytes("hello", 'ascii'))
            response = str(sock.recv(1024), 'ascii')
            if response == "hello":
                return True
        finally:
            sock.close()
        return False

    server = Server(('', 0), RequestHandler)
    ip, origin_port = server.server_address

    # start server in thread
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    # local service
    env = {"__class__": "Environment",
           "geomop_root": geomop_root_local,
           "geomop_analysis_workspace": os.path.abspath(os.path.join(TEST_FILES, "workspace")),
           "python": "python3"}
    cl = {"__class__": "ConnectionLocal",
          "address": "localhost",
          "environment": env}
    local_service = ServiceBase({"service_host_connection": cl})
    local_service_thread = threading.Thread(target=local_service.run, daemon=True)
    local_service_thread.start()

    # ConnectionLocal
    con = ConnectionLocal()
    con.set_local_service(local_service)
    con.connect()

    forwarded_port = con.forward_local_port(origin_port)
    assert connection_test("localhost", forwarded_port)

    forwarded_port = con.forward_remote_port(origin_port)
    assert connection_test("localhost", forwarded_port)

    con.close_connections()

    # environment
    env_rem = {"__class__": "Environment",
               "geomop_root": geomop_root_local,
               "geomop_analysis_workspace": REMOTE_WORKSPACE,
               "python": "python3"}

    # ConnectionSSH
    u, p = get_test_password()
    con = ConnectionSSH({"address": "localhost", "uid": u, "password": p, "environment": env_rem})
    con.set_local_service(local_service)
    con.connect()

    forwarded_port = con.forward_local_port(origin_port)
    assert connection_test("localhost", forwarded_port)

    forwarded_port = con.forward_remote_port(origin_port)
    assert connection_test("localhost", forwarded_port)

    con.close_connections()


LOCAL_TEST_FILES = os.path.abspath("test_files")
REMOTE_TEST_FILES = "/home/test/test_dir/test_files"


@pytest.mark.ssh
def test_upload_download(request):
    local_service = None
    local_service_thread = None

    def finalizer():
        # stopping, closing
        if local_service_thread is not None:
            local_service._closing = True
            local_service_thread.join(timeout=5)
            assert not local_service_thread.is_alive()

        shutil.rmtree(LOCAL_TEST_FILES, ignore_errors=True)
        shutil.rmtree(REMOTE_TEST_FILES, ignore_errors=True)
    request.addfinalizer(finalizer)

    files = ["f1.txt", "f2.txt", "l1.txt", "d1/f3.txt", "d2/f4.txt", "d2/d3/f5.txt", "d2/l2.txt"]
    paths = ["f1.txt", "f2.txt", "l1.txt", "d1/f3.txt", "d2"]

    def create_dir(path):
        shutil.rmtree(path, ignore_errors=True)
        os.makedirs(path)
        os.chmod(path, 0o777)

    def create_files(path):
        create_dir(path)
        for file in files:
            dir = os.path.dirname(file)
            if len(dir):
                os.makedirs(os.path.join(path, dir), exist_ok=True)
            if os.path.basename(file).startswith("l"):
                os.symlink("target", os.path.join(path, file))
            else:
                with open(os.path.join(path, file), 'w') as fd:
                    fd.write(file)

    def check_files(path):
        for file in files:
            if os.path.islink(os.path.join(path, file)):
                assert os.readlink(os.path.join(path, file)) == "target"
            else:
                with open(os.path.join(path, file), 'r') as fd:
                    assert fd.read() == file

    def remove_files(path):
        shutil.rmtree(path, ignore_errors=True)

    def remove_files_rem(path, con):
        sftp = con._sftp_pool.acquire()
        try:
            for fileattr in sftp.listdir_attr(path):
                path_name = os.path.join(path, fileattr.filename)
                if stat.S_ISDIR(sftp.lstat(path_name).st_mode):
                    remove_files_rem(path_name, con)
                    sftp.rmdir(path_name)
                else:
                    sftp.remove(path_name)
        finally:
            con._sftp_pool.release(sftp)

    # local service
    env = {"__class__": "Environment",
           "geomop_root": geomop_root_local,
           "geomop_analysis_workspace": os.path.abspath(os.path.join(TEST_FILES, "workspace")),
           "python": "python3"}
    cl = {"__class__": "ConnectionLocal",
          "address": "localhost",
          "environment": env}
    local_service = ServiceBase({"service_host_connection": cl})
    local_service_thread = threading.Thread(target=local_service.run, daemon=True)
    local_service_thread.start()

    # ConnectionLocal
    con = ConnectionLocal()
    con.set_local_service(local_service)
    con.connect()

    loc = os.path.join(LOCAL_TEST_FILES, "loc")
    rem = os.path.join(LOCAL_TEST_FILES, "rem")

    # upload
    create_files(loc)
    create_dir(rem)
    con.upload(paths, loc, rem, follow_symlinks=False)
    check_files(rem)
    remove_files(loc)
    remove_files(rem)

    # download
    create_files(rem)
    create_dir(loc)
    con.download(paths, loc, rem, follow_symlinks=False)
    check_files(loc)
    remove_files(loc)
    remove_files(rem)

    con.close_connections()

    # environment
    env_rem = {"__class__": "Environment",
               "geomop_root": geomop_root_local,
               "geomop_analysis_workspace": REMOTE_WORKSPACE,
               "python": "python3"}

    # ConnectionSSH
    u, p = get_test_password()
    con = ConnectionSSH({"address": "localhost", "uid": u, "password": p, "environment": env_rem})
    con.set_local_service(local_service)
    con.connect()

    loc = os.path.join(LOCAL_TEST_FILES, "loc")
    rem = os.path.join(REMOTE_TEST_FILES, "rem")

    # upload
    create_files(loc)
    create_dir(rem)
    con.upload(paths, loc, rem, follow_symlinks=False)
    check_files(rem)
    remove_files(loc)
    remove_files_rem(rem, con)
    remove_files(rem)

    # download
    create_files(rem)
    create_dir(loc)
    con.download(paths, loc, rem, follow_symlinks=False)
    check_files(loc)
    remove_files(loc)
    remove_files(rem)

    # FileNotFoundError
    try:
        con.upload(["x.txt"], loc, rem)
        assert False
    except FileNotFoundError:
        pass

    try:
        con.download(["x.txt"], loc, rem)
        assert False
    except FileNotFoundError:
        pass

    con.close_connections()


@pytest.mark.ssh
def test_exceptions():
    con = ConnectionSSH({"address": "localhost", "uid": "user_not_exist", "password": ""})
    try:
        con.connect()
        assert False
    except SSHAuthenticationError:
        pass

    con = ConnectionSSH({"address": "unknown_host", "uid": "user", "password": ""})
    try:
        con.connect()
        assert False
    except SSHAuthenticationError:
        assert False
    except SSHError:
        pass


@pytest.mark.ssh
def test_get_delegator(request):
    local_service = None
    local_service_thread = None

    def finalizer():
        # stopping, closing
        if local_service_thread is not None:
            local_service._closing = True
            local_service_thread.join(timeout=5)
            assert not local_service_thread.is_alive()
    request.addfinalizer(finalizer)

    # local service
    local_service = ServiceBase({})
    local_service_thread = threading.Thread(target=local_service.run, daemon=True)
    local_service_thread.start()

    # environment
    env = {"__class__": "Environment",
           "geomop_root": geomop_root_local,
           "geomop_analysis_workspace": REMOTE_WORKSPACE,
           "python": "python3"}

    # ConnectionSSH
    u, p = get_test_password()
    con = ConnectionSSH({"address": "localhost", "uid": u, "password": p, "environment":env})
    con.set_local_service(local_service)
    con.connect()

    # get_delegator
    delegator_proxy = con.get_delegator()
    assert isinstance(delegator_proxy, ServiceProxy)

    con.close_connections()


@pytest.mark.slow
@pytest.mark.ssh
def test_delegator_exec(request):
    local_service = None
    local_service_thread = None

    def finalizer():
        # stopping, closing
        if local_service_thread is not None:
            local_service._closing = True
            local_service_thread.join(timeout=5)
            assert not local_service_thread.is_alive()
    request.addfinalizer(finalizer)

    # local service
    env = {"__class__": "Environment",
           "geomop_root": geomop_root_local,
           "geomop_analysis_workspace": os.path.abspath(os.path.join(TEST_FILES, "workspace")),
           "python": "python3"}
    cl = {"__class__": "ConnectionLocal",
          "address": "localhost",
          "environment": env}
    local_service = ServiceBase({"service_host_connection": cl})
    local_service_thread = threading.Thread(target=local_service.run, daemon=True)
    local_service_thread.start()

    # environment
    env_rem = {"__class__": "Environment",
               "geomop_root": geomop_root_local,
               "geomop_analysis_workspace": REMOTE_WORKSPACE,
               "python": "python3"}

    # ConnectionSSH
    u, p = get_test_password()
    con = ConnectionSSH({"address": "localhost", "uid": u, "password": p, "environment": env_rem})
    con.set_local_service(local_service)
    con.connect()

    # get_delegator
    delegator_proxy = con.get_delegator()
    assert isinstance(delegator_proxy, ServiceProxy)

    # start process
    process_config = {"__class__": "ProcessExec",
                      "environment": env_rem,
                      "executable": {"__class__": "Executable", "path": "../testing/JobPanel/backend/t_process.py", "script": True}}
    answer = []
    delegator_proxy.call("request_process_start", process_config, answer)

    # wait for answer
    time.sleep(5)
    delegator_proxy._process_answers()
    process_id = answer[-1]["data"]

    # get status
    process_config = {"__class__": "ProcessExec", "process_id": process_id}
    answer = []
    delegator_proxy.call("request_process_status", process_config, answer)

    # wait for answer
    time.sleep(5)
    delegator_proxy._process_answers()
    assert answer[-1]["data"][process_id]["running"] is True

    # kill
    process_config = {"__class__": "ProcessExec", "process_id": process_id}
    answer = []
    delegator_proxy.call("request_process_kill", process_config, answer)

    # wait for answer
    time.sleep(5)
    delegator_proxy._process_answers()
    assert answer[-1]["data"] is True

    con.close_connections()

@pytest.mark.slow
def test_docker(request):
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

    # create analysis workspace
    os.makedirs(os.path.join(TEST_FILES, "workspace"), exist_ok=True)

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

    # service data
    cd = {"__class__": "ConnectionLocal",
          "address": "172.17.42.1",
          "environment": env,
          "name": "docker"}
    pd = {"__class__": "ProcessDocker",
          "executable": {"__class__": "Executable",
                         "path": os.path.join(this_source_dir, "t_service.py"),
                         "script": True}}
    service_data = {"service_host_connection": cd,
                    "process": pd,
                    "workspace": "",
                    "config_file_name": "t_service.conf"}

    # start test service
    local_service.request_start_child(service_data)
    test_service = local_service._child_services[1]

    # wait for test service running
    time.sleep(10)
    assert test_service._status == ServiceStatus.running

    # stop test service
    answer = []
    test_service.call("request_stop", None, answer)
    time.sleep(5)
    #assert len(answer) > 0


METACENTRUM_FRONTEND = "charon-ft.nti.tul.cz"
METACENTRUM_HOME = "/storage/liberec1-tul/home/"


@pytest.mark.slow
@pytest.mark.meta
def test_mc_get_delegator(request):
    local_service = None
    local_service_thread = None

    def finalizer():
        # stopping, closing
        if local_service_thread is not None:
            local_service._closing = True
            local_service_thread.join(timeout=5)
            assert not local_service_thread.is_alive()
    request.addfinalizer(finalizer)

    # metacentrum credentials
    mc_u, mc_p = get_passwords()["metacentrum"]

    # local service
    local_service = ServiceBase({})
    local_service_thread = threading.Thread(target=local_service.run, daemon=True)
    local_service_thread.start()

    # environment
    test_dir = METACENTRUM_HOME + "/" + mc_u + "/jenkins_test"
    env = {"__class__": "Environment",
           "geomop_root": test_dir + "/geomop",
           "python": test_dir + "/geomop/bin/python"}

    # ConnectionSSH
    con = ConnectionSSH({"address": METACENTRUM_FRONTEND, "uid": mc_u, "password": mc_p, "environment":env})
    con.set_local_service(local_service)
    con.connect()

    # get_delegator
    delegator_proxy = con.get_delegator()
    assert isinstance(delegator_proxy, ServiceProxy)

    con.close_connections()


@pytest.mark.slow
@pytest.mark.meta
def test_mc_delegator_pbs(request):
    local_service = None
    local_service_thread = None

    def finalizer():
        # stopping, closing
        if local_service_thread is not None:
            local_service._closing = True
            local_service_thread.join(timeout=5)
            assert not local_service_thread.is_alive()
    request.addfinalizer(finalizer)

    # metacentrum credentials
    mc_u, mc_p = get_passwords()["metacentrum"]

    # local service
    local_service = ServiceBase({})
    local_service_thread = threading.Thread(target=local_service.run, daemon=True)
    local_service_thread.start()

    # environment
    test_dir = METACENTRUM_HOME + "/" + mc_u + "/jenkins_test"
    env = {"__class__": "Environment",
           "geomop_root": test_dir + "/geomop",
           "geomop_analysis_workspace": test_dir + "/workspace",
           "python": test_dir + "/geomop/bin/python"}

    # ConnectionSSH
    con = ConnectionSSH({"address": METACENTRUM_FRONTEND, "uid": mc_u, "password": mc_p, "environment":env})
    con.set_local_service(local_service)
    con.connect()

    # get_delegator
    delegator_proxy = con.get_delegator()
    assert isinstance(delegator_proxy, ServiceProxy)

    # start process
    process_config = {"__class__": "ProcessPBS",
                      "executable": {"__class__": "Executable", "name": "sleep"},
                      "exec_args": {"__class__": "ExecArgs", "args": ["600"], "pbs_args": {"__class__": "PbsConfig", "dialect":{"__class__": "PbsDialectPBSPro"}}},
                      "environment": env}
    answer = []
    delegator_proxy.call("request_process_start", process_config, answer)

    # wait for answer
    def wait_for_answer(ans, t):
        for i in range(t):
            time.sleep(1)
            if len(ans) > 0:
                break

    wait_for_answer(answer, 60)
    process_id = answer[-1]

    # get status
    time.sleep(10)
    process_config = {"__class__": "ProcessPBS", "process_id": process_id}
    answer = []
    delegator_proxy.call("request_process_status", process_config, answer)

    # wait for answer
    wait_for_answer(answer, 60)
    status = answer[-1][process_id]["status"]
    assert status == ServiceStatus.queued or status == ServiceStatus.running

    # kill
    process_config = {"__class__": "ProcessPBS", "process_id": process_id}
    answer = []
    delegator_proxy.call("request_process_kill", process_config, answer)

    # wait for answer
    wait_for_answer(answer, 60)
    assert answer[-1] is True

    con.close_connections()
