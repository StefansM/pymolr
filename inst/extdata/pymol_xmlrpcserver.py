from pymol import cmd, util, keywords
import xmlrpclib
from SimpleXMLRPCServer import SimpleXMLRPCServer
import argparse
import sys

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument('--rpc-host', default="localhost", type=str)
arg_parser.add_argument('--rpc-port', default=9123, type=int)
arg_parser.add_argument('--rpc-bg', action='store_true', default=False)

# Current rpc server
server = None

class PymolServer(SimpleXMLRPCServer) :
    def __init__ (self, *args) :
        SimpleXMLRPCServer.__init__(self, *args)

    def _dispatch (self, method, params) :
        args = []
        kwargs = {}
        for param in params:
            if isinstance(param, dict):
                kwargs.update(param)
            else:
                args.append(param)

        func = None
        # Look up method from keywords first
        if method in keywords.get_command_keywords():
            func = keywords.get_command_keywords()[method][0]
        elif hasattr(cmd, method) :
            func = getattr(cmd, method)
        if not callable(func) :
            raise ValueError("{} is not callable".format(method))

        result = func(*args, **kwargs)
        if result is None :
            result = -1
        return result

def background(server):
    thread = threading.Thread(target=server.serve_forever)
    thread.setDaemon(1)
    thread.start()

def foreground(server):
    server.serve_forever()

if __name__ == "pymol":
    args = arg_parser.parse_known_args(sys.argv)
    server = PymolServer((args[0].rpc_host, args[0].rpc_port))
    if args[0].rpc_bg:
        background(server)
    else:
        foreground(server)
