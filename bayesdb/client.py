#
#   Copyright (c) 2010-2013, MIT Probabilistic Computing Project
#
#   Lead Developers: Jay Baxter and Dan Lovell
#   Authors: Jay Baxter, Dan Lovell, Baxter Eaves, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

import inspect
import pickle
import gzip
import prettytable
import re
import os
import time
import ast

import crosscat.utils.api_utils as au

import utils
from parser import Parser
from engine import Engine

class Client(object):
    def __init__(self, hostname=None, port=8008):
        if hostname is None or hostname=='localhost':
            self.online = False
            self.engine = Engine('local')
            self.parser = Parser(self.engine)
        else:
            self.online = True
            self.hostname = hostname
            self.port = port
            self.URI = 'http://' + hostname + ':%d' % port

    def call_bayesdb_engine(self, method_name, args_dict):
      if self.online:
        out, id = au.call(method_name, args_dict, self.URI)
      else:
        method = getattr(self.engine, method_name)
        argnames = inspect.getargspec(method)[0]
        args = [args_dict[argname] for argname in argnames if argname in args_dict]
        out = method(*args)
      return out

    def __call__(self, call_input, pretty=True, timing=False, wait=False, plots=None):
        return self.execute(call_input, pretty, timing, wait, plots)

    def execute(self, call_input, pretty=True, timing=False, wait=False, plots=None):
        if type(call_input) == file:
            bql_string = call_input.read()
            path = os.path.abspath(call_input.name)
            self.parser.set_root_dir(os.path.dirname(path))
        elif type(call_input) == str:
            bql_string = call_input
        else:
            print "Invalid input type: expected file or string."

        if plots is None:
            plots = 'DISPLAY' in os.environ.keys()

        if not pretty:
            return_list = []
            
        lines = self.parser.parse(bql_string)
        for line in lines:
            if type(call_input) == file:
                print '> %s' % line
            if wait:
                user_input = raw_input()
                if len(user_input) > 0 and (user_input[0] == 'q' or user_input[0] == 's'):
                    continue
            result = self.execute_line(line, pretty, timing)
            if not pretty:
                return_list.append(result)
            if type(call_input) == file:
                print

        self.parser.reset_root_dir()
        
        if not pretty:
            return return_list

    def execute_line(self, bql_string, pretty=True, timing=False, plots=True):
        if timing:
            start_time = time.time()

        result = self.parser.parse_line(bql_string) ## Calls Engine
        #result = self.call_bayesdb_engine('execute', dict(bql=bql_string))
        
        if timing:
            end_time = time.time()
            print 'Elapsed time: %.2f seconds.' % (end_time - start_time)

        if plots and bql_string.lower().strip().startswith('estimate'):
            utils.plot_feature_z(result['z_matrix_reordered'], result['column_names_reordered'], title=result['message'])
        elif pretty:
            if type(result) == dict and 'message' in result.keys():
                print result['message']
            pp = self.pretty_print(result)
            print pp
            return pp
        else:
            if type(result) == dict and 'message' in result.keys():
                print result['message']
            return result
        
    def pretty_print(self, query_obj):
        result = ""
        if type(query_obj) == dict and 'data' in query_obj and 'columns' in query_obj:
            pt = prettytable.PrettyTable()
            pt.field_names = query_obj['columns']
            for row in query_obj['data']:
                pt.add_row(row)
            result = pt
        elif type(query_obj) == list and type(query_obj[0]) == tuple:
            pt = prettytable.PrettyTable()
        elif type(query_obj) == dict and 'column_names_reordered' in query_obj:
            colnames = query_obj['column_names_reordered']
            zmatrix = query_obj['z_matrix_reordered']
            pt = prettytable.PrettyTable(hrules=prettytable.ALL, vrules=prettytable.ALL, header=False)
            pt.add_row([''] + list(colnames))
            for row, colname in zip(zmatrix, list(colnames)):
                pt.add_row([colname] + list(row))
            result = pt
        return result


