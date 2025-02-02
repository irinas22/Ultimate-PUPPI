
# read hyperparameters list from file and give out the best losses
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


with open('home_path.txt', 'r') as f:
    home_path = f.readlines()[0].strip()

file_loc = home_path + 'hyperparameter_list.txt'

# open file
with open(file_loc, 'r') as f:
    lines = f.readlines()
    # process to convert the string to a list of dictionaries
    list_as_str = [line.strip() for line in lines][0]
    list_as_str = list_as_str.split('},')
    list_as_str[0] = list_as_str[0][1:]
    list_as_str[-1] = list_as_str[-1][:-1]
    for i in range(len(list_as_str)-1):
        list_as_str[i] = list_as_str[i] + '}'
    list_of_dict = [eval(x) for x in list_as_str]
    # convert to pandas dataframe
    df = pd.DataFrame(list_of_dict)
    # sort by loss
    df = df.sort_values(by='loss')
    # select optimizer
    df = df[df['optimizer'] != 'sgd']
    # select epoch 9
    df = df[df['epoch'] == 9]
    # select where dropout is 0.25
    # df = df[df['dropout'] == 0.0]
    # df = df[df['hidden_dim'] == 100]
    print(df)
