import os
import yaml
import logging as log


class ManifestParser(object):
    def __init__(self,
                 manifest_directory,
                 ui_forms_directory=None,
                 workflows_directory=None,
                 heat_templates_directory=None,
                 agent_templates_directory=None,
                 scripts_directory=None
                 ):

        if ui_forms_directory is None:
            ui_forms_directory = os.path.join(manifest_directory, "ui_forms")
        if workflows_directory is None:
            workflows_directory = os.path.join(manifest_directory, "workflows")
        if heat_templates_directory is None:
            heat_templates_directory = os.path.join(manifest_directory,
                                                    "heat_templates")
        if agent_templates_directory is None:
            agent_templates_directory = os.path.join(manifest_directory,
                                                     "agent_templates")
        if scripts_directory is None:
            scripts_directory = os.path.join(manifest_directory, "scripts")

        self.manifest_directory = manifest_directory
        self.directory_mapping = {"ui_forms": ui_forms_directory,
                                  "workflows": workflows_directory,
                                  "heat_templates_directory":
                                  heat_templates_directory,
                                  "agent_templates": agent_templates_directory,
                                  "scripts": scripts_directory
                                  }

    def parse(self):
        manifests = []
        for file in os.listdir(self.manifest_directory):
            if os.path.isfile(file):
                if not file.endswith(".yaml"):
                    log.warning("Extention of {0} file is not yaml. "
                                "Only yaml file supported for "
                                "service manifest files.".format(file))
                    continue

                service_file = os.path.join(self.manifest_directory, file)
                try:
                    with open(service_file) as stream:
                        service_manifest = yaml.load(stream)
                except yaml.YAMLError, exc:
                        log.warn("Failed to load manifest file. {0}. "
                                 "The reason: {1!s}".format(service_file,
                                                            exc))
                        continue
                for key, value in service_manifest.iteritems():
                    directory_location = self.directory_mapping.get(key)
                    if directory_location:
                        for i, filename in enumerate(value):
                            absolute_path = os.path.join(directory_location,
                                                         filename)
                            service_manifest[key][i] = absolute_path
                            if not os.path.exists(absolute_path):
                                log.warning(
                                    "File {0} specified in manifest {1} "
                                    "doesn't exist at {2}".format(filename,
                                                                  file,
                                                                  absolute_path
                                                                  ))

                manifests.append(service_manifest)
        return manifests


def main():
    ManifestParser(os.path.join(os.path.dirname(__file__), 'Services')).parse()


if __name__ == "__main__":
   main()