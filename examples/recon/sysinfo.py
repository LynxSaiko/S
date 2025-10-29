import platform
MODULE_INFO={"name":"recon/sysinfo","description":"Print local system info"}
OPTIONS={"VERBOSE":{"required":False,"default":"true","description":"Verbose output"}}
def run(session, options):
    print("System info:");print("  User:",session.get("user"));print("  Platform:",platform.platform())