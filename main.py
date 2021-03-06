import argparse
import os
import sys
import time
import threading
import _thread

from http.server import BaseHTTPRequestHandler,HTTPServer
import json

import torch
import torch.optim as optim
import torch.multiprocessing as mp
import torch.nn as nn
import torch.nn.functional as F

from model import Model, Shared_grad_buffers, Shared_obs_stats
from train import trainer
from test import test
from chief import chief
from utils import TrafficLight, Counter,AtomicInteger

dispatch_table = {}


class RequestHandler(BaseHTTPRequestHandler):

    def __init__(self,req,client,server):
        BaseHTTPRequestHandler.__init__(self,req,client,server)
    
    def log_message(self, format, *args):
        #silent
        return
            
    def do_GET(self):
        
        request_path = self.path
        
        print("\ndo_Get it should not happen\n")
        
        self.send_response(200)
        
    def do_POST(self):

        _debug = False
        
        request_path = self.path
        
        request_headers = self.headers
        content_length = request_headers.get_all('content-length')
        length = int(content_length[0]) if content_length else 0
        content = self.rfile.read(length)

        if _debug:
            print("\n----- Request Start ----->\n")
            print(request_path)
            print(request_headers)
            print(content)
            print("<----- Request End -----\n")
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(self.dispatch(content.decode("ascii")).encode("ascii"))

    def get_target(self,msg):
        obj = json.loads(msg)
        return obj["state"]["side"] , obj

    def dispatch(self,msg):
        target , json_obj = self.get_target(msg)
        agent = dispatch_table[target]
        st = json_obj
        raw_act = agent.step((st["state"],float(st["reward"]),st["done"] == "true"))
        return "%f %f"%(raw_act[0] * 1000,raw_act[1] * 1000)

    do_PUT = do_POST
    do_DELETE = do_GET

def start_env():
    port = 8080
    print('Listening on localhost:%s' % port)
    server = HTTPServer(('', port), RequestHandler)
    server.serve_forever()



class Params():
    def __init__(self):
        self.batch_size = 200
        self.lr = 3e-4
        self.gamma = 0.8
        self.gae_param = 0.95
        self.clip = 0.2
        self.ent_coeff = 0.
        self.num_epoch = 100
        self.num_steps = 20000
        self.exploration_size = 50#make it small
        self.num_processes = 4
        self.update_treshold = 2 - 1
        self.max_episode_length = 100
        self.seed = int(time.time())
        self.num_inputs = {"self_input":13,"ally_input":7}
        self.num_outputs = 2

if __name__ == '__main__':
    #os.environ["NO_CUDA"] = "1"
    params = Params()
    torch.manual_seed(params.seed)

    traffic_light = TrafficLight()
    counter = Counter()

    shared_model = Model(params.num_inputs, params.num_outputs)
    shared_model.share_memory()
    shared_grad_buffers = Shared_grad_buffers(shared_model)
    #shared_grad_buffers.share_memory()
    shared_obs_stats = Shared_obs_stats(params.num_inputs)
    #shared_obs_stats.share_memory()
    optimizer = optim.Adam(shared_model.parameters(), lr=params.lr)
    test_n = torch.Tensor([0])
    test_n.share_memory_()

    atomic_counter = AtomicInteger()
    CommonConV = threading.Condition()

    rad_trainer = trainer(params,
    shared_model,shared_grad_buffers,shared_obs_stats,
    atomic_counter,CommonConV)

    dire_trainer = trainer(params,
    shared_model,shared_grad_buffers,shared_obs_stats,
    atomic_counter,CommonConV)

    dispatch_table["Radiant"] = rad_trainer
    dispatch_table["Dire"] = dire_trainer

    _thread.start_new_thread(chief,
    (params,CommonConV,atomic_counter,
    shared_model,shared_grad_buffers,optimizer))

    _thread.start_new_thread(rad_trainer.loop,())
    _thread.start_new_thread(dire_trainer.loop,())

    start_env()
