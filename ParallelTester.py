import sys
import ansible_runner
import os

def main(argv):
    playbook_file_name = "Ansible/build_container.yml"
    inventory_file_path = "Ansible/hosts"
    #r = ansible_runner.run(verbosity = 0, private_data_dir='.', playbook=playbook_file_name, inventory=inventory_file_path)
    app_versions_folder = argv[1]

    for app_path in os.listdir(app_versions_folder):
        full_path = os.path.join(app_versions_folder, app_path)
        if os.path.isdir(full_path):
            print(full_path)
            extravars = dict()
            extravars["app_path"] = full_path
            
            ansible_runner.interface.run_async(verbosity = 0, private_data_dir='.', playbook=playbook_file_name, inventory=inventory_file_path, extravars=extravars)


if __name__ == "__main__":
    main(sys.argv)