#!/usr/bin/env python
import socket
from multiprocessing import Process, Queue
import time
import sys
import re
import paramiko
from paramiko.ssh_exception import AuthenticationException, SSHException, BadHostKeyException

subnet = "10.128.4"

def check_server(address, port, queue):
    """
    Check an IP and port for it to be open, store result in queue.
    Based on https://stackoverflow.com/a/32382603
    """
    # Create a TCP socket
    s = socket.socket()
    try:
        s.connect((address, port))
        print("Connection open to %s on port %s" % (address, port))
        queue.put((True, address, port))
    except socket.error as e:
        print("Connection to %s on port %s failed: %s" % (address, port, e))
        queue.put((False, address, port))


def check_subnet_for_open_port(subnet, port, timeout=3.0):
    """
    Check the subnet for open port IPs.
    :param subnet str: Subnet as "192.168.1".
    :param port int: Port as 22.
    :returns [str]: List of IPs with port open found.
    """
    q = Queue()
    processes = []
    for i in range(1, 255):
        ip = subnet + '.' + str(i)
        print("Checking ip: " + str(ip))
        p = Process(target=check_server, args=[ip, port, q])
        processes.append(p)
        p.start()
    # Give a bit of time...
    time.sleep(timeout)

    found_ips = []
    for idx, p in enumerate(processes):
        # If not finished in the timeout, kill the process
        if p.exitcode is None:
            p.terminate()
        else:
            # If finished check if the port was open
            open_ip, address, port = q.get()
            if open_ip:
                found_ips.append(address)

    #  Cleanup processes
    for idx, p in enumerate(processes):
        p.join()

    return found_ips


def ap_ssh(ip, mp_queue):
    """
    Attempt to log into APs using default credentials
    """
    success = 0 
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        #print ("Establishing Connection with ",ip)
        ssh.connect(ip,username = 'admin' , password = 'admin123', timeout=10)
        chan = ssh.invoke_shell()
    except AuthenticationException:
        print("Authentication failed on " + ip + ", skipping device")
        sys.stdout.flush()
    except SSHException as sshException:
        print("Unable to establish SSH connection on " + ip + ": %s" % sshException)
        sys.stdout.flush()
    except BadHostKeyException as badHostKeyException:
        print("Unable to verify server's host key on " + ip + ": %s" % badHostKeyException)
        sys.stdout.flush()
    except Exception as e:
        print("Operation error on " + ip + ": %s" % e)
        sys.stdout.flush()
    else:
        outputs = []
        time.sleep(1)
        resp = chan.recv(9999)
        resp = (resp.decode('ascii','ignore').splitlines())
        version = (resp[5].split()[1])
        if "To cancel and boot in Standalone mode, type (s):" in resp[-1]:
            chan.send(chr(3))
            time.sleep(4)
            if chan.recv_ready():
                change = chan.recv(9999)
                outputs += (change.decode('ascii','ignore').splitlines())
            # 7-bit C1 ANSI sequences
            ansi_escape = re.compile(r'''
                \x1B  # ESC
                (?:   # 7-bit C1 Fe (except CSI)
                    [@-Z\\-_]
                |     # or [ for CSI, followed by a control sequence
                    \[
                    [0-?]*  # Parameter bytes
                    [ -/]*  # Intermediate bytes
                    [@-~]   # Final byte
                )
            ''', re.VERBOSE)
            result = ansi_escape.sub('', outputs[-1]).strip()
            if '#' == result[-1]:
                versions = version.split(".")
                if int(versions[0]) == 7 and int(versions[1]) > 5:
                    print("Resetting " + ip + " to xiq-cloud")
                    sys.stdout.flush()
                    chan.sendall('cset operational-mode xiq-cloud\n')
                    time.sleep(10)
                    try:
                        outputs = []
                        chan.send("show \n") 
                        if chan.recv_ready():
                            change = chan.recv(9999)
                            outputs += (change.decode('ascii','ignore').splitlines())
                        print(outputs)
                    except BrokenPipeError as e:
                        print("Connection lost to " + ip + ": %s" %e)
                    except Exception as e:
                        print("Connection lost to " + ip + ": %s" %e)
                elif int(versions[0]) == 7 and int(versions[1]) <= 5:
                    mp_queue.put(ip)
        ssh.close()
def main():
    port = 22
    ips = (check_subnet_for_open_port(subnet, port))
    sizeofbatch = 50
    for i in range(0, len(ips), sizeofbatch):
        batch = ips[i:i+sizeofbatch]
        NONE = ''
        mp_queue = Queue()
        processes = []
        for ip in batch:
            print("Connecting to", ip)
            p = Process(target=ap_ssh,args=(ip,mp_queue))
            processes.append(p)
            p.start()
    for p in processes:
        try:
            p.join()
            p.terminate()
        except:
            print("error occured in thread")
    mp_queue.put('STOP')
    legacy_list = []
    for line in iter(mp_queue.get, 'STOP'):
        legacy_list.append(line)
    if legacy_list:
        print("\n\n")
        print("The following devices will need to be logged into, converted to WiNG Distributed, and then converted to XIQ-cloud")
        print(" - SSH into the devices with admin/admin123, escape out of the discovery process, end run 'cset personality distributed'")
        print(" - Wait for AP to boot in distributed mode")
        print(" NOTE: IP addresses of devices may change in this process")
        print(" - log into WiNG AP with admin/admin123, enter a new password (admin1234), and run operational-mode xiq-cloud force")
        print("List of Devices:")
        if len(legacy_list) > 1:
            for ip in legacy_list:
                print(ip)
        elif len(legacy_list) == 1:
            print(ip)
if __name__ == '__main__':
    main()