# -*- coding: utf-8 -*-
"""
Created on Thu Aug  3 10:11:24 2023

@author: cca78

system.py

Under-the-hood functions which take user inputs from RedPitaya.py and modify the
system_config dictionary values accordingly
"""
from system_config import system_config

class system:

    def __init__(self):
        system = system_config()
