from ast import arg
import os
import sys
import shutil
import csv
import time;
import git
from git import RemoteProgress
from git import repo
import concurrent.futures
import threading
import subprocess

from inspect import getsourcefile
from os.path import abspath
from string import Template

import concurrent.futures

import logging
from MultiHandler import MultiHandler
from pathlib import Path



### Set up basic stderr logging; this is nothing fancy.
log_format = '%(relativeCreated)6.1f %(threadName)12s: %(levelname).1s %(module)8.8s:%(lineno)-4d %(message)s'
stderr_handler = logging.StreamHandler()
stderr_handler.setFormatter(logging.Formatter(log_format))
logging.getLogger().addHandler(stderr_handler)

_L = logging.getLogger("demo")

### Set default log level, log a message
_L.setLevel(logging.DEBUG)
_L.info("Run initiated")


mvn_command = "mvn package -f "

working_dir_path = abspath(getsourcefile(lambda:0))
working_dir_path = working_dir_path[0:working_dir_path.rindex("/")]


#repo_url = "https://github.com/sqshq/piggymetrics.git"
repo_url = "https://github.com/spring-projects/spring-petclinic.git"
app_name = "junit-java-example-master"
version_id_path = os.path.join(working_dir_path, "test_commits.txt")
#version_id_path = os.path.join(working_dir_path, "last_100_commits.txt")
#version_id_path = os.path.join(working_dir_path, "all_commits.txt")

app_mutation_folder_name = "{}_mutations".format(app_name)
ts = time.time()
app_mutation_folder_name += "_{}".format(ts)
mutations_base_path = os.path.join(working_dir_path, app_mutation_folder_name)

major_javac_path = working_dir_path + "/major/bin/javac"
major_export_dir_argument = "-J-Dmajor.export.directory="
major_arguments = "-J-Dmajor.export.mutants=true -XMutator:ALL"
major_command_template = major_javac_path + " " + major_export_dir_argument + "$major_mutants_folder" + " " + major_arguments

csv_file_path = mutations_base_path + "/mutation_survivors.csv"
logs_path = os.path.join(mutations_base_path, "logs")
commits_changes_path = os.path.join(mutations_base_path, "commits_changes")

piggymetrics_reference_checkout_folder_name = "piggymetrics_master_tmp"
piggymetrics_reference_checkout_path = os.path.join(mutations_base_path, piggymetrics_reference_checkout_folder_name)

class CloneProgress(RemoteProgress):
    def update(self, op_code, cur_count, max_count=None, message=''):
        if message:
            _L.info(message)

class Mutator:

    def _find_files(base_path, extension):
        files_to_ret = list()
        for root, dirs, files in os.walk(base_path):
            for file in files:
                if file.endswith(extension):
                    files_to_ret.append(os.path.join(root, file))
        return files_to_ret

    def clone(repo_url, dest_folder, commit = None):
        _L.info("Cloning {} into {}".format(repo_url,dest_folder))
        repo = git.Repo.clone_from(repo_url, dest_folder)#, branch="master")#, progress=CloneProgress())
        if commit is not None:
            _L.info("Checking out commit {}".format(commit))
            repo.git.checkout(commit)

    def fix_repo(repo_path):
        try:
            _L.info("Removing old, non working tests.")
            to_remove = os.path.join(repo_path, "statistics-service/src/test/java/com/piggymetrics/statistics/client/ExchangeRatesClientTest.java")
            os.remove(to_remove)
        except expression as identifier:
            _L.info("Removal failed, maybe the file does not exist")
            _L.info(expression)
        

    def _append_to_survivors_file(mutation_name, return_value):
        with open(csv_file_path, mode='a') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow([mutation_name, return_value])

    def validate_version(version_folder):
        version_name = version_folder[version_folder.rindex("/")+1:]
        _L.info("Validating version {} using maven".format(version_name))
        ret_value = os.system(mvn_command + " " + version_folder + "/pom.xml > " + version_folder + "/maven_output.txt")
        _L.info("Maven return code was {}".format(ret_value))
        if ret_value != 0:
            ## SECOND TRY
            _L.info("Retrying...")
            os.system("mvn clean -f " + " " + version_folder + "/pom.xml > /dev/null 2>&1")
            ret_value = os.system(mvn_command + " " + version_folder + "/pom.xml > " + version_folder + "/maven_output.txt")
            _L.info("Maven return code was {}".format(ret_value))
        Mutator._append_to_survivors_file(version_name, ret_value)
        os.system("mvn clean -f " + " " + version_folder + "/pom.xml > /dev/null 2>&1")
        return ret_value

    def _place_and_validate_mutant(src, mutation_name, original_file_path, mutated_file_path):
        shutil.copytree(src, mutation_name)
        new_path = original_file_path.replace(src, mutation_name)
        os.replace(mutated_file_path, new_path)
        Mutator.validate_version(mutation_name)

    def create_mutants_for_files(mutants_source, files_to_mutate):
        i = 0
        for file_to_mutate in files_to_mutate:
            _L.info("Mutating {}".format(file_to_mutate))
            file_to_mutate_full_path = os.path.join(mutants_source, file_to_mutate)
            simple_name = file_to_mutate[file_to_mutate.rindex("/")+1:file_to_mutate.rindex(".")]
            major_mutations = mutants_source + "_mutants_tmp"

            #major_command = Template(major_command_template)
            #major_command_string ="{} {} > {} 2>&1".format(major_command.substitute(major_mutants_folder = major_mutations), file_to_mutate_full_path, os.path.join(mutants_source, "major_output_{}.txt".format(simple_name)))
            #os.system(major_command_string)

            major_commands_arguments = [major_javac_path, major_export_dir_argument + major_mutations,"-J-Dmajor.export.mutants=true", "-XMutator:ALL", file_to_mutate_full_path]
            _L.info("Executing Major command: {}".format(major_commands_arguments))
            log = open(os.path.join(mutants_source, "major_output_{}.txt".format(simple_name)), 'a')
            p = subprocess.Popen(major_commands_arguments, cwd=mutants_source, stdout=log, stderr=log)
            p.wait()
            
            mutated_files = Mutator._find_files(major_mutations, ".java")
            _L.info("{} mutants were generated.".format(len(mutated_files)))
            for mutated_file in mutated_files:
                mutation_name = mutants_source + "_v{}".format(i)
                i += 1
                Mutator._place_and_validate_mutant(mutants_source, mutation_name, file_to_mutate_full_path, mutated_file)

    def _get_files_to_mutate(version):
        to_ret = list()
        git_output_file = os.path.join(commits_changes_path, "{}.txt".format(version))
        git_command = "git -C {} log -m -1 --name-only --pretty=\"format:\" {} > {}".format(piggymetrics_reference_checkout_path, version, git_output_file)
        os.system(git_command)
        with open(git_output_file) as f:
            commit_files = f.readlines()
            commit_files = [x.strip() for x in commit_files]
        for commit_file in commit_files:
            if (commit_file.endswith(".java") and "src/test" not in commit_file):
                to_ret.append(commit_file)
        return to_ret

    def _handle_version(version):
        _L.info("Run initiated for version {}".format(version))
        files_to_mutate = Mutator._get_files_to_mutate(version)
        if len(files_to_mutate) > 0:
            _L.info("Files to mutate: {}".format(str(files_to_mutate)))
            app_base_version_path = mutations_base_path + "/{}_{}".format(app_name, version)
            Mutator.clone(repo_url, app_base_version_path, version)
            Mutator.fix_repo(app_base_version_path)
            ret_value = Mutator.validate_version(app_base_version_path)
            if (ret_value == 0):
                Mutator.create_mutants_for_files(app_base_version_path, files_to_mutate)
        else:
            _L.info("Nothing to do for this version.")

    def _mutate_file_path(file_path):
        files_to_mutate = list()
        for path in Path(file_path + "/src").rglob('*.java'):
            abs_path = str(path)
            if "src/test" not in abs_path:
                print(abs_path)
                files_to_mutate.append(abs_path)
        Mutator.create_mutants_for_files(file_path, files_to_mutate)

    def _mutate_version(version):
        _L.info("Run initiated for version {}".format(version))
        app_base_version_path = mutations_base_path + "/{}_{}".format(app_name, version)
        Mutator.clone(repo_url, app_base_version_path, version)
        ret_value = Mutator.validate_version(app_base_version_path)
        if (ret_value == 0):
            Mutator._mutate_file_path(app_base_version_path)
        else:
            _L.info("Nothing to do for this version.")

    def thread_task(version):
        threading.current_thread().name = version
        Mutator._handle_version(version)
    
    def alt_thread_task(version):
        threading.current_thread().name = version
        Mutator._mutate_version(version)
    
    def mutate_specified_path_task(file_path):
        threading.current_thread().name = file_path
        Mutator._mutate_file_path(file_path)


    def __try_make_folder(folder_path):
        try:
            os.mkdir(folder_path)
        except OSError:
            _L.info ("Creation of the directory %s failed" % folder_path)
            raise SystemExit()
        else:
            _L.info ("Successfully created the directory %s " % folder_path)

    def _init_output_folder():
        Mutator.__try_make_folder(mutations_base_path)
        Mutator.__try_make_folder(logs_path)
        Mutator.__try_make_folder(commits_changes_path)

def main(argv):

    Mutator._init_output_folder()

    if len(argv) > 1:
        file_path = argv[1]
        Mutator._mutate_file_path(file_path)
    else:

        ### Set up a logger that creates one file per thread
        multi_handler = MultiHandler(logs_path)
        multi_handler.setFormatter(logging.Formatter(log_format))
        logging.getLogger().addHandler(multi_handler)

        with open(version_id_path) as f:
            versions_to_mutate = f.readlines()
            versions_to_mutate = [x.strip() for x in versions_to_mutate]
        
        _L.info("Checking out master for reference")
        if os.path.exists(piggymetrics_reference_checkout_path):
            shutil.rmtree(piggymetrics_reference_checkout_path)
        Mutator.clone(repo_url, piggymetrics_reference_checkout_path)

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            executor.map(Mutator.alt_thread_task, versions_to_mutate)

if __name__ == "__main__":
    main(sys.argv)