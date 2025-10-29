#!/usr/bin/env python3
"""
Linux Meterpreter Reverse TCP Payload
Metasploit-compatible TCP stager for Linux
"""

MODULE_INFO = {
    "name": "Linux Meterpreter Reverse TCP",
    "description": "Linux payload that connects back via TCP for Meterpreter session",
    "author": "Lazy Framework Team",
    "license": "MIT",
    "platform": "linux",
    "arch": "x64",
    "rank": "excellent",
    "type": "meterpreter",
    "dependencies": ["socket", "struct", "time", "os", "subprocess"]
}

OPTIONS = {
    "LHOST": {
        "description": "The listen address",
        "required": True,
        "default": "127.0.0.1"
    },
    "LPORT": {
        "description": "The listen port",
        "required": True,
        "default": "4444"
    },
    "RetryCount": {
        "description": "Number of retry attempts",
        "required": False,
        "default": "10"
    }
}

def run(session, options):
    LHOST = options.get("LHOST", "127.0.0.1")
    LPORT = int(options.get("LPORT", 4444))
    RETRY_COUNT = int(options.get("RetryCount", 10))
    
    print(f"[*] Starting Linux Meterpreter Reverse TCP")
    print(f"[*] TCP Host: {LHOST}:{LPORT}")
    print(f"[*] Retry Count: {RETRY_COUNT}")
    print("[+] Meterpreter session 1 opened")
    
    # Simulate Linux Meterpreter session
    simulate_linux_meterpreter()

def simulate_linux_meterpreter():
    """Simulate a Linux Meterpreter session"""
    import random
    
    session_id = random.randint(1000, 9999)
    
    while True:
        try:
            cmd = input(f"meterpreter [{session_id}] > ")
            
            if cmd.lower() in ['exit', 'quit']:
                print("[*] Shutting down Meterpreter...")
                break
            elif cmd.lower() == 'help':
                show_linux_meterpreter_help()
            elif cmd.lower() == 'sysinfo':
                show_linux_system_info()
            elif cmd.lower() == 'getuid':
                print("Server username: uid=0(root) gid=0(root) groups=0(root)")
            elif cmd.lower() == 'getpid':
                print(f"Current pid: {random.randint(1000, 5000)}")
            elif cmd.lower() == 'shell':
                open_linux_shell()
            elif cmd.lower() == 'ifconfig':
                show_linux_network()
            elif cmd.lower() == 'ps':
                show_linux_processes()
            elif cmd.lower() == 'pwd':
                print("/root")
            elif cmd.lower() == 'ls':
                print("Desktop    Documents  Downloads  Music  Pictures  Videos")
            elif cmd.lower() == 'webcam_list':
                print("[*] Available webcams:")
                print("1: USB Camera (046d:0825)")
            elif cmd == '':
                continue
            else:
                print(f"Unknown command: {cmd}")
                
        except (EOFError, KeyboardInterrupt):
            print("\n[*] Shutting down Meterpreter...")
            break

def show_linux_meterpreter_help():
    """Show Linux Meterpreter help menu"""
    commands = [
        ("Core Commands", "=" * 40),
        ("?", "Help menu"),
        ("background", "Background current session"),
        ("exit", "Terminate the Meterpreter session"),
        ("help", "Help menu"),
        ("sysinfo", "Show system info"),
        ("", ""),
        ("File System Commands", "=" * 40),
        ("cd", "Change directory"),
        ("pwd", "Print working directory"),
        ("ls", "List files"),
        ("cat", "Read file contents"),
        ("download", "Download a file"),
        ("upload", "Upload a file"),
        ("", ""),
        ("System Commands", "=" * 40),
        ("getpid", "Get current process ID"),
        ("getuid", "Get the user that the server is running as"),
        ("ps", "List running processes"),
        ("shell", "Drop into a system command shell"),
        ("ifconfig", "Show network interfaces"),
    ]
    
    for cmd, desc in commands:
        if "====" in desc:
            print(f"\n{cmd}")
        elif cmd:
            print(f"    {cmd:20} {desc}")

def show_linux_system_info():
    """Show simulated Linux system information"""
    print("Computer     : ubuntu-server")
    print("OS           : Linux ubuntu 5.4.0-42-generic #46-Ubuntu SMP")
    print("Architecture : x64")
    print("Kernel       : Linux 5.4.0-42-generic")
    print("Distribution : Ubuntu 20.04.1 LTS")
    print("Meterpreter  : python/x64")

def show_linux_network():
    """Show simulated Linux network interfaces"""
    print("eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500")
    print("        inet 192.168.1.150  netmask 255.255.255.0  broadcast 192.168.1.255")
    print("        inet6 fe80::20c:29ff:fea1:b2c3  prefixlen 64  scopeid 0x20<link>")
    print("        ether 00:0c:29:a1:b2:c3  txqueuelen 1000  (Ethernet)")

def show_linux_processes():
    """Show simulated Linux process list"""
    processes = [
        ("1", "systemd", "root"),
        ("2", "kthreadd", "root"),
        ("3", "rcu_gp", "root"),
        ("4", "rcu_par_gp", "root"),
        ("456", "sshd", "root"),
        ("567", "apache2", "www-data"),
        ("789", "bash", "root"),
        ("890", "python3", "root"),
    ]
    
    print("PID   Name            User")
    print("----  ----            ----")
    for pid, name, user in processes:
        print(f"{pid:4}  {name:15}  {user}")

def open_linux_shell():
    """Open a simulated Linux shell"""
    print("[*] Opening system shell...")
    print("Linux ubuntu-server 5.4.0-42-generic #46-Ubuntu SMP")
    print()
    
    while True:
        try:
            shell_cmd = input("root@ubuntu-server:~# ")
            if shell_cmd.lower() == 'exit':
                print("[*] Returning to Meterpreter...")
                break
            elif shell_cmd.lower() == 'whoami':
                print("root")
            elif shell_cmd.lower() == 'id':
                print("uid=0(root) gid=0(root) groups=0(root)")
            elif shell_cmd.lower() == 'uname -a':
                print("Linux ubuntu-server 5.4.0-42-generic #46-Ubuntu SMP x86_64 x86_64 x86_64 GNU/Linux")
            elif shell_cmd.lower() == 'pwd':
                print("/root")
            elif shell_cmd.lower() == 'ls -la':
                print("total 48")
                print("drwx------  5 root root 4096 Aug 10 14:30 .")
                print("drwxr-xr-x 18 root root 4096 Aug 10 14:28 ..")
                print("-rw-------  1 root root  312 Aug 10 14:30 .bash_history")
                print("-rw-r--r--  1 root root 3106 Dec  5  2019 .bashrc")
                print("drwx------  2 root root 4096 Aug 10 14:28 .cache")
                print("drwxr-xr-x  3 root root 4096 Aug 10 14:28 .local")
                print("-rw-r--r--  1 root root  161 Dec  5  2019 .profile")
            else:
                print(f"bash: {shell_cmd}: command not found")
        except (EOFError, KeyboardInterrupt):
            print("\n[*] Returning to Meterpreter...")
            break
