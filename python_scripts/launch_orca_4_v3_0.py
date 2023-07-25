""" 
This script iteratively creates .inp files for multiple .xyz files which all use the same orca keywords
each .xyz file should be named with the format {molecule_name}_{charge}_{spin}.xyz
for positive charges, use either the number or p (e.g. 1, 2, p1, p2)
for negative charges, use m (e.g. m1, m2)
the orca keywords will either be taken from a set of default files found at carrow_bin/python_scripts/orca_settings/ or a local file specified as an argument.
While creating the .inp files, this script renames the .xyz files to {molecule_name}_{charge}_{spin}_in.xyz
Lastly, this script creates a batch SLURM job using the memory and parallelization data  in the specified file.

This script takes up to three optional user-specified system arguments - the job time, the memory per core, and a settings file
This script requires no particular order for its three arguments
The shell script which launches this script passes the user email (sys.argv[4]) as well as the path to the carrow group bin (sys.argv[5]).
This script reads the working directory's name and uses it as a variable, along with the names of the .xyz files
"""

#####################
###Version Control###
#####################

#(since I will probably not convince the Carrow lab to use Github)
#Update this comment whenever edits are made.

edit_history = """
version Initials    Date            Summary
1.0     ARS         23-Jun-2023     First draft of entire codebase is written
2.0     ARS         25-Jun-2023     Restructured to create individual .inp files and launch them all from a common .sh file
2.1     ARS         25-Jun-2023     Streamlined code and incorporated ChatGPT reccomendations
2.2     ARS         25-Jun-2023     Further edits under the wise guidance of ChatGPT
2.3     ARS         26-Jun-2023     Moved constants to __main__ block per unquestionable tutelage of ChatGPT
2.4     ARS         27-Jun-2023     Debugged a few problems
3.0     ARS         20-Jul-2023     Added two optional arguemts for memory and settings file. Made time optional. Added a function for estimating memory cost. Changed way settings path is hard coded
"""
#note that the most recent version number is extracted when script is launched as version

import os
import sys
import math

def assign_arguments (arg_list):
    """determines which system argument is job_time, which is memory_per_core, and which is settings_path"""
    #TODO: error handling for format of memory_per_core and job_time
    
    job_time = None
    memory_per_core = None
    settings_path = None
    
    for arg in arg_list:
        if ':' in arg:
            job_time = arg
        elif arg.endswith('M'):
            memory_per_core = int(arg[:-1])
        elif os.path.exists(arg):
            settings_path = arg
        else:
            print(f'Error: {arg} not recognized')
            print('Usage: launch_orca_4 d:hh:mm:ss nM settings_file')
            exit(1)
            
    return job_time, memory_per_core, settings_path
            
def indent(n, string):
    """Indents single digit entries for cleanliness."""
    if n < 10:
        return(f' {string}')
    else:
        return(string)

def atom_count(file):
    """reads an xyz file and returns the number of atoms from each row of the periodic table.
    Atoms in rows 6 and 7 are both partitioned into n6"""

    atom_types = {
        'n1':('H', 'He'),
        'n2':('Li', 'Be', 'B', 'C', 'N', 'O', 'F', 'Ne'),
        'n3':('Na', 'Mg', 'Al', 'Si', 'P', 'S', 'Cl', 'Ar'),
        'n4':('K', 'Ca', 'Sc', 'Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn', 'Ga', 'Ge', 'As', 'Se', 'Br', 'Kr'),
        'n5':('Rb', 'Sr', 'Y', 'Zr', 'Nb', 'Mo', 'Tc', 'Ru', 'Rh', 'Pd', 'Ag', 'Cd', 'In', 'Sn', 'Sb', 'Te', 'I', 'Xe')}

    n_atoms = [0,0,0,0,0,0]
    
    with open(file, 'r') as f:
        inlines = f.readlines()
    
    for line in inlines[2:]:
        if len(line.split()) == 4:
            atom = line.split()[0]
            
            #mind the off by one
            if atom in atom_types['n1']:
                n_atoms[0] += 1
            elif atom in atom_types['n2']:
                n_atoms[1] += 1
            elif atom in atom_types['n3']:
                n_atoms[2] += 1
            elif atom in atom_types['n4']:
                n_atoms[3] += 1
            elif atom in atom_types['n5']:
                n_atoms[4] += 1
            else:
                n_atoms[5] += 1
                
    return n_atoms

def estimate_memory(atom_count):
    """takes a 6 element list which indicates the atom count from an xyz file
    then estimates the memory demands from this data in MB
    as of now, all jobs are assumed to use the opt orca_settings file"""
    
    MIN = 2
    def mem_model(data_subset):
        """model of the memory demand as a function of number of each atom type"""
        n1, n2, n3, n4, n5, n6 = data_subset
        return((0)*n1 + 100*n2 + 100*n3 + 100*n4 + 100*n5 + 100*n6 + 1000)
    
    memory_estimate = mem_model(atom_count)
    if memory_estimate < MIN:
        memory_estimate = MIN

    return memory_estimate

def get_subjob_properties(filename):
    """Extracts subjob name, charge, and spin from the filename."""
    #TODO: graceful error handling of improperly named jobs
    #TODO: handles jobs that already have the _in ending
    subjob_name = filename.split('.')[0]
    
    parts = filename[:-4].split('_')
    
    if parts[-2].startswith('m'):
        charge = -int(parts[-2][1:])
    elif parts[-2].startswith('p'):
        charge = int(parts[-2][1:])
    else:
        charge = int(parts[-2])

    spin = int(parts[-1])
    
    return subjob_name, charge, spin

def generate_orca_input(settings_lines, memory_per_core):
    """Generates Orca input files and renames xyz files."""
    for file in os.scandir('.'):
        if file.name.endswith('.xyz'):
            subjob_name, charge, spin = get_subjob_properties(file.name)

            with open(f'{subjob_name}.inp', 'w') as inp_file:
                inp_file.writelines(settings_lines)
                inp_file.write(f'%maxcore {memory_per_core}\n')
                inp_file.write(f'* xyzfile {charge} {spin} {subjob_name}_in.xyz\n\n')
                inp_file.write(f'# This input file was created with {os.path.basename(__file__)} version {version}\n')

            os.rename(file.name, f"{subjob_name}_in.xyz")
            
        else:
            print(f'Error! Skipping {file.name} because it is not an .xyz file.')

def generate_slurm_script(job_name, job_time, ncores, total_memory, email, version, slurm_subjobs):
    """Generates the SLURM .sh script."""
    slurm = f"""#!/bin/bash
#SBATCH -J {job_name}
#SBATCH -t {job_time}
#SBATCH -N 1
#SBATCH --ntasks-per-node={ncores}
#SBATCH --mem {total_memory}G
#SBATCH --mail-user={email}
#SBATCH --mail-type=all

# This shell file was created with {os.path.basename(__file__)} version {version}

# Unload all loaded modules and reset everything to the original state;
# then load ORCA binaries and set communication protocol
module purge
module use /project/carrow/downloads/apps/modules
module add orca

# Copy contents of the working directory to a temporary directory,
# launch the job, and copy results back to the working directory
cp * $TMPDIR/
cd $TMPDIR
ORCA=`which orca`
echo $ORCA

# Subjobs
{slurm_subjobs}

# Copy every file that doesn't contain ".tmp" in the filename
shopt -s extglob
cp !(*.tmp*) $SLURM_SUBMIT_DIR
shopt -u extglob

cd $SLURM_SUBMIT_DIR
"""

    with open(f'{job_name}.sh', 'w') as slurm_file:
        slurm_file.write(slurm)

def main():
    job_time, memory_per_core, settings_path = assign_arguments(arg_list)
    
    if job_time == None:
        print(f'No job time provided. Setting job time to {DEFAULT_TIME}')
        job_time = DEFAULT_TIME
    
    if settings_path == None:
        # selection menu of default orca settings
        settings = sorted(os.listdir(DEFAULT_PATH))
       
        print(f"""
Welcome to the Carrow Lab's interactive Orca input handler!
Default files can be found/edited at {DEFAULT_PATH}
Please use a number key to choose a setting.""")
        for index, option in enumerate(settings, start=1):
            print(indent(index, f'{index} {option}'))

        choice = int(input(' > ')) - 1
        if choice <= len(settings):
            settings_path = f'{DEFAULT_PATH}/{settings[choice]}'
        else:
            print('Invalid choice!')
            sys.exit(1)
    
    #loads settings and cleans them
    with open(settings_path, 'r') as file:
        settings_lines = file.readlines()
    print(settings_lines[0][:-1])
    if settings_lines[-1][-1] != '\n':
        settings_lines[-1] += '\n'
        
    #determines ncores from settings file
    ncores = None
    for line in settings_lines:
        if line.lower().startswith('%pal nprocs'):
            ncores = int(line.split()[-2])
    if ncores == None:
        print('Error! Settings file must contain %pal NPROCS')
        exit(1)
   
    #checks for .xyz files and throws error if there are none
    xyz_present = False
    for file in os.scandir('.'):
        if file.name.endswith('.xyz'):
            xyz_present = True
            break
    if xyz_present == False:
        print('There are no xyz files! Terminating the script.')
        sys.exit(1)
    
    #estimates memory demands based on xyz file contents if no memory was specified.
    if memory_per_core == None:
        memory_per_core = 0
        
        for file in os.scandir('.'):
            if file.name.endswith('.xyz'):
                memory_estimate = estimate_memory(atom_count(file))
                if memory_estimate > memory_per_core:
                    memory_per_core = memory_estimate
        
        print(f'memory per core estimated to be {memory_per_core}MB')
    
    total_memory = math.ceil(memory_per_core * ncores / 1000)
    if total_memory > MAX_ALLOWED_MEM:
        print(f'Error! excessive memory ({total_memory}G) requested!')
        print(f'Lower memory below {MAX_ALLOWED_MEM}G by lowering %pal nprocs or')
        print(f'specifying a lower memory_per_core on as an argument (e.g. launch_orca_4 2000M)')
        exit(1)

    # Generate Orca input files and rename xyz files
    generate_orca_input(settings_lines, memory_per_core)

    # Prepare SLURM subjobs
    slurm_subjobs = ''
    for file in os.scandir('.'):
        if file.name.endswith('.inp'):
            slurm_subjobs += f'$ORCA {file.name} >> $SLURM_SUBMIT_DIR/{file.name[:-4]}.out\n'

    # Generate the SLURM .sh script
    generate_slurm_script(job_name, job_time, ncores, total_memory, email, version, slurm_subjobs)

if __name__ == '__main__':
    arg_list = sys.argv[3:5]
    email = sys.argv[1]
    DEFAULT_PATH = f'{sys.argv[2]}/python_scripts/orca_settings/'
    DEFAULT_TIME = '1:00:00'
    MAX_ALLOWED_MEM = 120
    job_name = os.path.basename(os.getcwd())
    version = edit_history.strip().split('\n')[-1].split()[0]
    main()
