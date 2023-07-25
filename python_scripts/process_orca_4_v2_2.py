""" 
This script processes orca 4.2.1 .out files and creates a .csv file summarizing the results.
For each .out file, the following are tallied:
['molecule name', 'command line', 'job type', 'freq?', 'cost (cpu*hr)', 'E', 'H', 'G', 'neg freq', 'geom converged?']
This script creates a single .csv file with every result.
It also creates a shell script for visualizing the negative frequencies

This script takes no arguments, and operates on every file with the .out extension in a directory
It also reads the directory name and uses it as a constant.
"""

#####################
###Version Control###
#####################

#(since I will probably not convince the Carrow lab to use Github)
#Update this value whenever edits are made and add to the Edit History comment.

edit_history = """
Version Initials    Date            Summary
1.0     ARS         25-Jun-2023     First draft of entire codebase is written
1.1     ARS         26-Jun-2023     Extensive formatting and coding condensed
1.2     ARS         26-Jun-2023     Incorporated ChatGPT recommendations
2.0     ARS         26-Jun-2023     Now creates a .sh file for visualizing negative frequencies
2.1     ARS         29-Jun-2023     added case sensitivity as an option to the find_in function, minor debugging, cost is now properly in cpu*h instead of h
2.2     ARS         21-Jul-2023     neg_freq shell file now prevents very large jobs (excessive negative frequencies) from being run on the head node.
"""

#TODO: handle jobs that ran out of iterations (currently crashes)
#TODO: make sure to save files as out_file_n+1 in case out_file already exists

import os
import csv

def cut_section(inlines, start, start_shift, end, end_shift):
    """
    Slices a list of strings (inlines) based on start and end flags.
    The start flag is searched for from the bottom of the file.
    The start_shift and end_shift parameters allow shifting the slice inward or outward.
    """
    if start == '':
        i = 0
    else:
        i = len(inlines) - 1
        while i >= 0:
            if start in inlines[i]:
                break
            i -= 1

    if end == '':
        j = -1
    else:
        j = i
        while j < len(inlines):
            if end in inlines[j]:
                break
            j += 1

    return inlines[i - start_shift : j + end_shift]

def find_in(lines, starts_with, direction='', case=True):
    """
    Finds the first line in a set of lines (lines) that starts with a specified string (starts_with).
    By default, it searches in the forward direction, but setting direction='reverse' reverses the behavior.
    Returns None if the string is not found.
    """
    if case:
        if direction == '':
            for line in lines:
                if line.startswith(starts_with):
                    return line
        elif direction == 'reverse':
            for line in reversed(lines):
                if line.startswith(starts_with):
                    return line
    else:
        if direction == '':
            for line in lines:
                if line.lower().startswith(starts_with.lower()):
                    return line
        elif direction == 'reverse':
            for line in reversed(lines):
                if line.lower().startswith(starts_with.lower()):
                    return line
 
def extract_energy(lines, flag, index):
    """
    Extracts energy (E, H, or G) from lines using the specified flag and index.
    It searches in the reverse direction to get the most recent data.
    """
    energy_line = find_in(lines, flag, 'reverse')
    if energy_line == None:
        return None
    energy = energy_line.split()[index]
    return energy 

def neg_freq_file(neg_freq_info, job_name):
    """writes the .sh file for visualizing negative frequencies if there are any
    Will prevent running the file outside of sbatch if there are excessive negative frequencies"""
    
    MAX_LENGTH = 10    
          
    if len(neg_freq_info) < MAX_LENGTH:
        orca_pltvib = ''
        for row in neg_freq_info:
            orca_pltvib += f'orca_pltvib {row[0]}.hess {row[1]}\n'
        
        shell_file = f"""#!/bin/bash
module purge
module use /project/carrow/downloads/apps/modules
module add orca

echo "There are {len(neg_freq_info)} negative frequencies.
Executing neg_freqs.sh"

{orca_pltvib}
#This shell file was created with {os.path.basename(__file__)} and extracted from {job_name}/'
"""
    else:
        orca_pltvib = ''
        for row in neg_freq_info:
            orca_pltvib += f'    orca_pltvib job_files/{row[0]}.hess {row[1]}\n'
        orca_pltvib += '    mv job_files/*.hess.v* .'
    
        shell_file = f"""#!/bin/bash
#SBATCH -J neg_freqs
#SBATCH -t 1:00:00
#SBATCH -N 1
#SBATCH --ntasks-per-node=1

#checks if job is running through SLURM
if [ -n "$SLURM_JOB_ID" ]; then

    module purge
    module use /project/carrow/downloads/apps/modules
    module add orca

{orca_pltvib}
else
    echo "Warning: Excessive negative frequencies ({len(neg_freq_info)}) detected. 
Please run this job through SLURM with sbatch neg_freqs.sh"
    exit 0
fi
        
#This shell file was created with {os.path.basename(__file__)} and extracted from {job_name}/'
"""
    
    return shell_file

def process_out_files():
    """
    Processes Orca .out files in the current directory and creates a summary CSV file.
    Also creates a .sh file which will visualize the negative frequencies.
    """
    orca_outs = [entry.name for entry in os.scandir('.') if entry.name.endswith('.out')]
    
    #initializes results table
    script_info = [f'This table was compiled with {os.path.basename(__file__)} and extracted from {job_name}/']
    table_header = ['molecule name', 'command line', 'job type', 'freq?', 'cost (cpu*hr)', 'E (a.u.)', 'H (a.u.)', 'G (a.u.)', 'neg freq (cm^-1)', 'geom converged?']
    results_table = []
    neg_freq_info = []

    for filename in orca_outs:
        with open(filename, 'r') as file:
            inlines = file.readlines()

        #removes leading and trailing spaces
        inlines = [line.strip() + '\n' for line in inlines]

        #skips .out files with multiple jobs and slurm .out files
        multiple_jobs = any('$new_job' in line.lower() for line in inlines)
        if multiple_jobs:
            print(f'{filename} contains multiple jobs. Skipping this file.')
            continue
        if 'slurm' in filename:
            continue

        #slices inputs and removes the '|  #>'
        inputs = cut_section(inlines, 'INPUT FILE\n', -3, '****END OF INPUT****\n', 0)
        for i in range(len(inputs)):
            inputs[i] = inputs[i][inputs[i].index('>') + 2:]

        #finds molecule_name, commands, ncores
        molecule_name = filename.split('.')[0]
        commands = find_in(inputs, '!')[:-1].lower()
        ncores = find_in(inputs, '%pal nprocs', case=False).split()[2]

        #determines if job finished correctly and then slices results and timing accordingly
        if inlines[-2] == '****ORCA TERMINATED NORMALLY****\n':
            results = cut_section(inlines, '****END OF INPUT****\n', -3, '****ORCA TERMINATED NORMALLY****\n', 0)
            timing = inlines[-1].split()
            cost = int(ncores) * (24*float(timing[3]) + float(timing[5]) + float(timing[7])/60 + float(timing[9])/3600)
        else:
            results = cut_section(inlines, '****END OF INPUT****\n', -3, '', 0)
            cost = 'N/A'

        #finds job_type
        if 'opt'  in commands:
            job_type = 'opt'
        elif 'optts' in commands:
            job_type = 'optTS'
        else:
            job_type = 'SP'
        
        #Finds freq(bool) and E
        freq = ('freq' in commands)
        E = extract_energy(results, 'FINAL SINGLE POINT ENERGY', -1)
        
        #finds H, G, and neg_freqs if freq == True
        if freq:
            H = extract_energy(results, 'Total enthalpy', -2)
            G = extract_energy(results, 'Final Gibbs free energy', -2)

            frequencies = cut_section(results, 'Writing the Hessian file to the disk', -11, 'NORMAL MODES', -3)
            neg_freqs = []
            for line in frequencies:
                frequency = float(line.split()[1])
                if frequency < 0:
                    neg_freqs.append(frequency)
                    neg_freq_info.append([molecule_name, line.split()[0][:-1]])
        else:
            H, G, neg_freqs = '', '', ''
            
        #finds geom_converged if calculation is a type of optimization
        if job_type == 'opt' or job_type == 'optTS':
            geom_converged = any('***        THE OPTIMIZATION HAS CONVERGED     ***' in line for line in results)
        else:
            geom_converged = ''
        
        results_table.append([molecule_name, commands, job_type, freq, cost, E, H, G, neg_freqs, geom_converged])
    
    #writes the .csv file with results
    with open(f'{job_name}_summary.csv', 'w', newline='') as file1:
        writer = csv.writer(file1)
        writer.writerows([script_info, table_header] + results_table)
    print(f'Summary file {job_name}_summary.csv created.')
    
    #writes the .sh file for visualizing negative frequencies if there are any
    if neg_freq_info != []:
        shell_file = neg_freq_file(neg_freq_info, job_name)
        with open(f'neg_freqs.sh', 'w') as file2:
            file2.writelines(shell_file)
        
if __name__ == '__main__':
    job_name = os.path.basename(os.getcwd())
    process_out_files()
