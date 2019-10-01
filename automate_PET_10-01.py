#!/usr/bin/python
# ^ won't be needed with _install_PET.py file 

"""-----------INFORMATION FOR USER: 
# PET file must have multiple (6) frames. MRI file has already been run on CIVET
# You can adjust defaults on the configuration json file.
# Example bash input: python automate_PET_10-01.py 102.0 8.4 "ROYM"
# Weight and dose inputted are float (must have a decimal). 
# Blur will be done at 4, 6, and 8 mm. 
# Assumes you are in a directory containing patients' folders. Keep the py script, installer script, and json file in the larger directory.
"""

from pathlib import Path
from copy import deepcopy
import argparse
import subprocess
import os
from importlib import import_module
import json
import glob

newest_minctools = max(glob.glob("/opt/minc/1.9.*"))
MINC_DIR = Path(newest_minctools)
DEFAULT_MINC_CONFIG = MINC_DIR / 'minc-toolkit-config.sh'
DEFAULT_MINC_BEST_LIN = MINC_DIR.joinpath('bin/bestlinreg_s')

parser = argparse.ArgumentParser('image processing inputs')
parser.add_argument('weight', type=float)
parser.add_argument('dose', type=float)
parser.add_argument('folder')    

args = parser.parse_args()

def splice(path: Path, modifier) -> Path:
    # ISSUE 1: some file paths have dots other than the extension), causing this splice function to do nothing. 
    # Remove dots from the path aside from the final one for extension - an idea but a problem if the dots are anywhere aside from the file name
    # Might have to use a more brute function (remove dots aside from final one)
    # Change any backslashes to forward slashes (unlikely to be problem for user,but useful for my debugging on Windows computer)
    return path.parent.joinpath(path.stem + modifier).with_suffix(path.suffix)

def main(weight, dose, folder):
    workdir = Path(os.getcwd())
    patient_dir = Path(os.getcwd()).joinpath(folder)
    if patient_dir.exists() == False:  
        print("problem with locating patient directory")
        # In my case, patient folder path doesn't build on cwd - I assume that this problem will go away with installer file?
        # It is likely that people will store patient files on a shared drive on virtual machine. This setup should be able to accommodate that. 
        raise SystemExit()
    json_path = Path(os.getcwd(), 'config.json')

    if json_path.exists():
        config = json.load(json_path.open())
        PETsuffix = config['PET_SUFFIX']
        MRIsuffix = config['MRI_SUFFIX']
        talsuffix = config['TAL_SUFFIX']
        ITsuffix = config['IT_SUFFIX']
        MNItemplatepath = config['MNI_TEMPLATE_PATH']
        maskpath = config['MASK_PATH']
        maskbinvalue = config['MASK_BIN_VALUE']
        mincconfigpath = config['MINC_CONFIG_PATH']
        mincbestlinregpath = config['MINC_BEST_LIN_REG_PATH']
    else:
        PETsuffix = "4D_MC01.mnc" 
        MRIsuffix = "_t1.mnc"   
        talsuffix = "t1_tal.xfm"
        ITsuffix = "_It.xfm"
        MNItemplatepath = workdir / "mni_icbm152_t1_tal_nlin_sym_09c.mnc"
        maskpath = workdir / "WM_0.99_new.mnc"
        maskbinvalue = 1
        mincconfigpath = DEFAULT_MINC_CONFIG
        mincbestlinregpath = DEFAULT_MINC_BEST_LIN

        PETpath = []
        MRIpath = []
        talpath = []
        ITpath = []

    for root, dirs, files in os.walk(patient_dir): #Max depth 3 - add 
        PETpath = glob.glob("*"+PETsuffix)
        MRIpath = glob.glob("*"+MRIsuffix)
        talpath = glob.glob("*"+talsuffix)
        ITpath = glob.glob("*"+ITsuffix)
    print(patient_dir)
    print(PETpath, MRIpath, talpath, ITpath)

    if len(PETpath) == 1:
        return
    elif len(PETpath) > 1: 
        print("Multiple PET files ending in", PETsuffix, ". Check that there is only one patient's files in this patient folder.")
        raise SystemExit(0)
    else:
        print("No file found. Please check that your PETfile ends in", PETsuffix)
        raise SystemExit(0)
    if len(MRIpath) == 1:
        return
    elif len(MRIpath) > 1: 
        print("Multiple PET files ending in", MRIsuffix, "check that there is only one patient's files in this patient folder!")
        raise SystemExit(0)
    else:
        print("No file found. Please check that your PETfile ends in", MRIsuffix)
        raise SystemExit(0)
    if len(PETpath) == 1:
        return
    elif len(talpath) > 1: 
        print("Multiple PET files ending in", talsuffix, "check that there is only one patient's files in this patient folder!")
        raise SystemExit(0)
    else:
        print("No file found. Please check that your PETfile ends in", talsuffix)
        raise SystemExit(0)
    if len(ITpath) == 1:
        return
    elif len(ITpath) > 1: 
        print("Multiple PET files ending in", ITsuffix, "check that there is only one patient's files in this patient folder!")
        raise SystemExit(0)
    else:
        print("No file found. Please check that your PETfile ends in", ITsuffix)
        raise SystemExit(0)

    PETpath = Path(PETpath[0])
    MRIpath = Path(MRIpath[0])
    talpath = Path(talpath[0])
    ITpath= Path(ITpath[0])

    #subject_code = os.path.basename(PETpath)
    #subject_code = subject_code[:6]

    with open('output' + folder + '.txt', 'w') as f: # I want this to be written into patient folder
        def bash_command(*args):
            bash_output = subprocess.check_output([str(c) for c in args])
            print(bash_output)
            f.write(bash_output)

        mylist = []
        xfmlist = []
        mylist.append(PETpath)
        outputPETpath = mylist[-1]
        outputPETpath_xfm = outputPETpath.with_suffix('xfm')
        xfmlist.append(outputPETpath_xfm)
        """ 
        (Not needed unless dealing with .v files)
        # 1. Change the file extension from .v to .mnc
        outputPETpath = PETpath.with_suffix('mnc')
        mylist.append(outputPETpath)
        bash_command('ecattominc', '-short', PETpath, outputPETpath)
        """
        # 2. Average the PET frames
        outputPETpath = splice(outputPETpath, '_avg')
        mylist.append(outputPETpath)
        bash_command('mincaverage', mylist[-2], outputPETpath, '-avgdim', 'time')

        # 3. Take the SUV
        constant = dose * 1000 / weight
        print("dose * 1000 / weight = " + str(constant))
        outputPETpath = splice(outputPETpath, "_suv")
        mylist.append(outputPETpath)
        outputPETpath.unlink()
        bash_command('mincmath', '-div', mylist[-2], '-const', constant, outputPETpath)

        # 4. Automatic coregistration of subject PET to subject MRI to obtain .xfm files
        xfmlist.append(outputPETpath_xfm)
        outputPETpath = splice(outputPETpath, "_autoreg")
        mylist.append(outputPETpath)
        bash_command('source', mincconfigpath)
        bash_command(mincbestlinregpath, '–nmi', '–lsq6', mylist[-2], MRIpath, outputPETpath_xfm, outputPETpath)
        # Bash/Minc error: source

        # 5. Linear and non-linear transformations to put the PET file into MNI space (toST = to Standard Template)
        outputPETpath_xfm = splice(outputPETpath_xfm, '_toST').with_suffix('xfm')
        xfmlist.append(outputPETpath_xfm)
        bash_command('xfmconcat', xfmlist[-2], talpath, ITpath, outputPETpath_xfm)
        outputPETpath = splice(outputPETpath, "_ST")
        mylist.append(outputPETpath)
        bash_command('mincresample', mylist[-2], '-like', MNItemplatepath, '-transform', outputPETpath_xfm,
                     outputPETpath)

        # 6A. Take the SUVR in MNIspace
        mylist_patient = deepcopy(mylist)  # Divergence in image processing (template space versus patient space)
        mask_SUV = subprocess.run(
            ['mincstats', '-mask', maskpath, '-mask_binvalue', maskbinvalue, outputPETpath, '-mean'], capture_output=True,
            stdout=f, check=True)
        outputPETpath = splice(outputPETpath, '_SUVR')
        mylist.append(outputPETpath)
        bash_command('mincmath', '-div', '-const', mask_SUV, mylist[-2], outputPETpath)

        # 6B - Take the SUVR in patient space
        PET_subjectmask = subject_code + "_subjectmask.mnc"
        bash_command('mincresample', '–like', mylist[-3], '–nearest', '–transform', outputPETpath_xfm,
                     '–invert_transformation', maskpath, PET_subjectmask)
        outputPETpath_patient = splice(outputPETpath, '_patient_SUVR')
        mylist_patient.append(outputPETpath_patient)
        mask_SUV_patient = subprocess.run(
            ['mincstats', '–mask', PET_subjectmask, '–mask_binvalue', mylist[-3], mylist_patient[-2], '–mean'],
            capture_output=True, stdout=f, check=True)
        bash_command('mincmath', '-div', '-const', mask_SUV_patient, mylist_patient[-2], outputPETpath_patient)

        # 7A. Blur PET in 4, 6, and 8mm
        blurlist = [4, 6, 8]
        for i in blurlist:
            blur_word = "_blur_" + str(i)
            outputBlurPath = splice(outputPETpath, blur_word)
            bash_command('mincblur', '-fwhm', i, mylist[-2], outputBlurPath)
            #Note: Camille says minc automatically adds mnc extension here; should have extension removed from outputBlurPath

        # 7B. Blur PET in 4, 6, and 8 mm for patient space image
        blurlist = [4, 6, 8]
        for i in blurlist: 
            blur_word = "_blur_" + str(i)
            outputBlurPath_patient = splice(outputPETpath_patient, blur_word)
            bash_command('mincblur', '-fwhm', i, mylist[-2], outputBlurPath_patient)
            #Note: Camille says minc automatically adds mnc extension here; should have extension removed from outputBlurPath

        # 8. Finished. Show the subject's PET file on MNI template
        bash_command('register', outputPETpath, MNItemplatepath)

main(**vars(args))

