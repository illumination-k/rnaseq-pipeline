#!/usr/bin/python3

import os
import yaml
import argparse
import subprocess
import json
import shutil

import rnaseq_pipeline.utils

import logging
logger = logging.getLogger(__name__)

# set color logger
mapping = {
    "TRACE": "[ trace ]",
    "DEBUG": "[ \x1b[0;36mdebug\x1b[0m ]",
    "INFO": "[ \x1b[0;32minfo\x1b[0m ]",
    "WARNING": "[ \x1b[0;33mwarn\x1b[0m ]",
    "WARN": "[ \x1b[0;33mwarn\x1b[0m ]",
    "ERROR": "\x1b[0;31m[ error ]\x1b[0m",
    "ALERT": "\x1b[0;37;41m[ alert ]\x1b[0m",
    "CRITICAL": "\x1b[0;37;41m[ alert ]\x1b[0m",
}

class ColorfulHandler(logging.StreamHandler):
    def emit(self, record):
        record.levelname = mapping[record.levelname]
        super().emit(record)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--settings", type=str, required=True)
    parser.add_argument("--log_level", default="info", choices=["error", "warning", "warn", "info", "debug"])
    args = parser.parse_args()

    if args.log_level == "error":
        log_level = logging.ERROR
    elif args.log_level == "warning":
        log_level = logging.WARNING
    elif args.log_level == "info":
        log_level = logging.INFO
    else:
        log_level = logging.DEBUG

    fmt = "%(asctime)s %(levelname)s %(message)s"
    logging.basicConfig(handlers=[ColorfulHandler()], level=log_level, format=fmt)

    logger.info(f'Settings file: {args.settings}')

    with open(args.settings, 'r') as f:
        settings = yaml.safe_load(f)
    
    logger.info(f'JOB_NAME: {settings["name"]}')

    logger.info(f'ROOT_DIR: {settings["root_dir"]}')
    os.chdir(settings["root_dir"])
    
    logger.info(f'SRA_ID_LIST: {settings["sra_list"]}')
    sra_ids = []
    with open(settings['sra_list'], 'r') as f:
        for line in f:
            sra_ids.append(line.rstrip("\n"))
    
    logger.debug(sra_ids)
    logger.info(f'----- start processing {len(sra_ids)} ids... -----')

    threads = str(settings['num_threads'])
    logger.info(f'using {threads} threads...')
    
    container_command = [settings['container_tool'], 'run', '-v', os.getcwd() + ":/local_volume"]
    # if settings['container_tool'] == 'udocker':
    #     container_command.append("--quiet")

    preprocess_container = settings['containers']['preprocess']
    quant_container = settings['containers']['quant']

    result_dict = {}
    error_ids = []

    proceeded_ids = set([f.split("_")[0] for f in os.listdir(".") if f.endswith("_exp")])

    for sra_id in sra_ids:
        if sra_id in proceeded_ids:
            logger.warn(f'{sra_id} is already analyzed! skip this id...')
            continue

        logger.info(f'+++++ start {sra_id} +++++')
        
        sra_download_command = container_command + [settings['containers']['sra_tools'], 'fasterq-dump', sra_id, '-e', threads]
        logger.info("\tstart downloading...")
        logger.debug("fasterq command:", sra_download_command)
        try:
            subprocess.run(sra_download_command, stderr=subprocess.DEVNULL, check=True)
        except:
            logger.error("downloading proecess is failed!")
            
            fasterq_tmp_dirs = [d for d in os.listdir(".") if d.startswith("fasterq.tmp.")]
            if len(fasterq_tmp_dirs) == 0 or threads == "1":
                logger.error(f'Please check {sra_id} manually!')
            else:
                logger.error(f'Maybe fetching {sra_id} is failed because of Segmentation fault! Retry download single core mode...')
                sra_download_command = container_command + [settings['containers']['sra_tools'], 'fasterq-dump', sra_id, '-e', "1"]
                try:
                    subprocess.run(sra_download_command, stderr=subprocess.DEVNULL, check=True)
                except:
                    logger.error(f'Single core mode is also failed! Please check {sra_id} manually!')
                    logger.debug("remove tmpdir...")
                    fasterq_tmp_dirs = [d for d in os.listdir(".") if d.startswith("fasterq.tmp.")]
                    for fasterq_tmp_dir in fasterq_tmp_dirs:
                        shutil.rmtree(fasterq_tmp_dir)

        layout = rnaseq_pipeline.utils.select_layout(sra_id)

        if layout == 'SINGLE':
            fastp_command = container_command + [preprocess_container, "fastp", 
                                                        "-i", sra_id+".fastq", 
                                                        "-o", sra_id + "_trim.fastq.gz", 
                                                        "-w", threads, "-h", sra_id+".html"]

            salmon_command = container_command + [quant_container, "salmon", "quant", "-i", settings["index"], "-l", "A", 
                                                        "-r", sra_id + "_trim.fastq.gz",
                                                        "-p", threads, "--validateMappings", "--seqBias", "--gcBias", "--posBias", "-o", sra_id + "_exp"]
        elif layout == "PAIRED":
            fastp_command = container_command + [preprocess_container, "fastp", 
                                                        "-i", sra_id+"_1.fastq", "-I", sra_id+"_2.fastq", 
                                                        "-o", sra_id+"_1_trim.fastq.gz", "-O", sra_id + "_2_trim.fastq.gz", 
                                                        "-w", threads, "-h", sra_id+".html"]

            salmon_command = container_command + [quant_container, "salmon", "quant", "-i", settings["index"], "-l", "A", 
                                                        "-1", sra_id+"_1_trim.fastq.gz", "-2", sra_id + "_2_trim.fastq.gz", 
                                                        "-p", threads, "--validateMappings", "--seqBias", "--gcBias", "--posBias", "-o", sra_id + "_exp"]
        else:
            logger.error(f'no {id} file exists! skip this {id} ...')
            error_ids.append(sra_id)
            continue

        logger.debug("start processing...")
        
        logger.info("\trun fastp...")
        logger.debug("fastp command:", fastp_command)

        try:
            subprocess.run(fastp_command, stderr=subprocess.DEVNULL, check=True)
        except:
            error_ids.append(sra_id)
            logger.error(f'fastp process return non exit code 0! please confirm manually {sra_id}')
            remove_ext_files(".fastq")
            continue

        logger.debug("delete fastq files....")
        rnaseq_pipeline.utils.remove_ext_files(".fastq")

        logger.debug("salmon command", salmon_command)
        logger.info("\trun salmon...")

        try:
            subprocess.run(salmon_command, stderr=subprocess.DEVNULL, check=True)
        except:
            error_ids.append(sra_id)
            logger.error(f'salmon process return non exit code 0! please confrim manually {sra_id}')
            remove_ext_files(".fastq.gz")
            continue

        logger.debug("delete trim fastq files....")
        rnaseq_pipeline.utils.remove_ext_files(".fastq.gz")

        logger.info(f'+++++ end {sra_id} +++++\n')
    
    logger.info("all of preprocess steps are done!")
    
    logger.info("convert salmon quant.sf to tsv files...")
    tximport_command = container_command + [quant_container, "Rscript", "/workspace/quant2tsv.R"]
    try:
        subprocess.run(tximport_command, check=True)
    except:
        logger.error("convert salmon quant.sf step is failed!")
    
    logger.info("integrating reports...")
    multiqc_command = container_command + [settings['containers']['report'], "."]
    
    try:
        subprocess.run(multiqc_command, check=True)
    except:
        logger.error("Integrating reports step is failed!")

    
    rnaseq_pipeline.utils.get_result_summary(settings)


    with open(settings['name'] + "_error_ids.txt", "w") as f:
        f.write("\n".join(error_ids))

if __name__ == "__main__":
    main()
