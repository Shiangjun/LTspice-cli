from subprocess import call
import os
from tempfile import mkstemp
from shutil import move
import numpy as np
import matplotlib.pyplot as plt

import config

def simulate(spice_exe_path, file_path):
    file_name = str(file_path.split('\\')[-1])
    print('Simulation starting: ' + file_name + '.asc')
    call('"' + spice_exe_path + '" -netlist "' + file_path + '.asc"')
    call('"' + spice_exe_path + '" -b -ascii "' + file_path + '.net"')
    size = os.path.getsize(file_path + '.raw')
    print('Simulation finished: ' + file_name + '.raw created (' + str(size/1000) + ' kB)')

def clean_raw_file(spice_exe_path, file_path, output_path, output_header):

    file_name = file_path
    try:
        f = open(file_path + '.raw', 'r')
    except IOError:
        print('File not found: ' + file_name + '.raw')
        simulate(spice_exe_path, file_path)
        f = open(file_path + '.raw', 'r')

    print('Cleaning up file: ' + file_name + '.raw')

    reading_header = True
    preffered_sorting = [0, 1, 5, 4, 2, 6, 3]
    variable_numbering = {'time': 0, 'V(n_upper)': 2, 'V(n_out)': 5, 'I(snubber_lower)': 19, 'I(snubber_upper)': 20, 'I(upper)': 40, 'I(lower)': 41}
    data = []
    data_line = []

    for line_num, line in enumerate(f):

        if reading_header:
            if line_num == 4:
                number_of_vars = int(line.split(' ')[-1])
            if line_num == 5:
                number_of_points = int(line.split(' ')[-1])
            if line[:7] == 'Values:':
                reading_header = False
                header_length = line_num + 1
                continue
        else:
            data_line_num = (line_num - header_length) % number_of_vars
            if data_line_num in variable_numbering.values():
                data_line.append(line.split('\t')[-1].split('\n')[0])
            if data_line_num == number_of_vars - 1:
                data.append(data_line)
                data_line = []

    f.close()

    # Rearrange data
    variables = sorted(variable_numbering, key=variable_numbering.__getitem__)
    variables = np.array(variables)[preffered_sorting].tolist()
    data = np.array(data)[:, preffered_sorting]

    # Write data to file
    f = open(output_path, 'w+')
    f.write(output_header)
    f.write('\t'.join(variables) + '\n')
    for line in data:
        f.write('\t'.join(line) + '\n')
    f.close()

    size = os.path.getsize(output_path)
    print('CSV file created: ' + output_path + ' (' + str(size/1000) + ' kB)')

    return data

def set_params(file_path, param, param_val, overwrite=False):
    # Create temp file
    f, abs_path = mkstemp()
    with open(abs_path,'w') as new_file:
        with open(file_path) as old_file:
            for line in old_file:
                line_list = line.split(' ')
                if line_list[0] == 'TEXT':
                    for element_num, element in enumerate(line_list):
                        if element.split('=')[0] == param:
                            line_list[element_num] = param + '=' + str(param_val)
                    if line_list[-1][-1] != '\n':
                        line_list[-1] = line_list[-1] + '\n'
                    new_file.write(' '.join(line_list))
                else:
                    new_file.write(line)
    os.close(f)
    if overwrite:
        os.remove(file_path)
        move(abs_path, file_path)
    else:
        move(abs_path, file_path[:-4] + '_new.asc')

def get_params(file_path):
    output_list = []
    f = open(file_path, 'r')
    for line in f:
        line_list = line.split()
        if line_list[0] == 'TEXT' and '!.param' in line_list:
            output_list.extend(line_list[line_list.index('!.param') + 1:])
    f.close()
    return output_list

def run_tests(param, param_value_list, run_simulation=True):

    file_path = config.LTSpice_asc_filename[:-4] # Use .asc file specified in config, but remove file ending
    file_path_new = file_path + '_new'
    spice_exe_path = config.LTSpice_executable_path

    for i, param_value in enumerate(param_value_list):

        output_path = config.output_data_path + param + '=' + str(param_value) + '.txt'

        print('\nStarting simulation with param ' + param + '=' + str(param_value))
        set_params(file_path + '.asc', param, param_value)
        if run_simulation:
            simulate(spice_exe_path, file_path_new)

        output_header = 'SPICE simulation result. Parameters: ' + ', '.join(get_params(file_path_new + '.asc')) + '\n' # Maybe not add the time variables
        clean_raw_file(spice_exe_path, file_path_new, output_path, output_header)
