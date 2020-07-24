import os

import logging
logger = logging.getLogger(__name__)


def make_container_commands(settings):
    if settings['container_tool'] == 'docker' or settings['container_tool'] == 'udocker':
        return [settings['container_tool'], 'run', '-v', os.getcwd() + ":/local_volume"]
    elif settings['container_tool'] == 'singularity':
        return [settings['container_tool'], 'exec']
    elif settings['container_tool'] == 'none':
        return []
    else:
        raise ValueError("The container tool is invalid! Please select from docker, udocker, singularity or none")

def select_layout(id):
    files = [f for f in os.listdir(".") if f.startswith(id) and f.endswith(".fastq")]
    length = len(files)
    if length == 0:
        return "INVALID"
    elif length == 1:
        return "SINGLE"
    elif length == 2:
        return "PAIRED"
    else:
        return "INVALID"

def remove_ext_files(ext):
    files = [f for f in os.listdir(".") if f.endswith(ext)]
    for f in files:
        os.remove(f)

def get_result_summary(settings):
    dirs = [d for d in os.listdir(".") if os.path.isdir(d) and d.endswith("_exp")]
    result_dict = {}
    for d in dirs:
        path = os.path.join(d, "aux_info", "meta_info.json")
        if os.path.exists(path):
            with open(path, "r") as f:
                result = json.load(f)
                result_dict[d.split("_")[0]] = str(result["percent_mapped"])
        else:
            logger.error(f'meta info does not exist in {d}, please check manually...')

    with open(settings["name"] + "_result.csv", "w") as f:
        L = ["SRA_ID", "MappingPercentage"]
        for k, v in result_dict.items():
            L.append(k + "," + v)
        f.write("\n".join(L))
