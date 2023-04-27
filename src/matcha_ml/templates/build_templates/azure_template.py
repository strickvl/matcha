"""Build a template for provisioning resources on Azure using terraform files."""
import dataclasses
import glob
import json
import os
from shutil import copy, rmtree
from typing import List, Optional

import typer

from matcha_ml.cli.ui.print_messages import print_status
from matcha_ml.cli.ui.status_message_builders import (
    build_resource_confirmation,
    build_status,
    build_step_success_status,
    build_substep_success_status,
)
from matcha_ml.errors import MatchaPermissionError

SUBMODULE_NAMES = [
    "aks",
    "resource_group",
    "mlflow_module",
    "storage",
    "seldon",
    "zenml_storage",
    "zen_server",
    "azure_container_registry",
    "zen_server/zenml_helm",
    "zen_server/zenml_helm/templates",
]
ALLOWED_EXTENSIONS = ["tf", "yaml", "tpl"]


@dataclasses.dataclass
class TemplateVariables:
    """Terraform template variables."""

    # Azure location in which all resources will be provisioned
    location: str

    # Prefix used for all resources
    prefix: str

    # Password for ZenServer
    password: str


def reuse_configuration(path: str) -> bool:
    """Check if a configuration already exists, and prompt user to override or reuse it.

    Args:
        path (str): path to the infrastructure configuration

    Returns:
        bool: decision to reuse the existing configuration
    """
    if os.path.exists(path):
        confirmation_message = build_resource_confirmation(
            "Matcha has detected that the following resources have already been configured for provisioning",
            [
                ("Resource group", "A resource group"),
                ("Azure Kubernetes Service (AKS)", "A kubernetes cluster"),
                (
                    "Two Storage Containers",
                    "A storage container for experiment tracking artifacts and a second for model training artifacts",
                ),
                (
                    "Seldon Core",
                    "A framework for model deployment on top of a kubernetes cluster",
                ),
                (
                    "Azure Container Registry",
                    "A container registry for storing docker images",
                ),
                ("ZenServer", "A zenml server required for remote orchestration"),
            ],
        )

        print_status(confirmation_message)

        return not typer.confirm(
            "If you choose to override the existing configuration, the existing configuration will be deleted. Otherwise, the configuration will be reused.\n\nDo you want to override the existing configuration?"
        )
    else:
        return False


def build_template_configuration(
    location: str, prefix: str, password: str
) -> TemplateVariables:
    """Ask for variables and build the configuration.

    Args:
        location (str): Azure location in which all resources will be provisioned.
        prefix (str): Prefix used for all resources.
        password (str): Password for ZenServer.

    Returns:
        TemplateVariables: Terraform variables required by a template
    """
    return TemplateVariables(location=location, prefix=prefix, password=password)


def copy_files(files: List[str], destination: str, sub_folder_path: str = "") -> None:
    """Copy files from folders and sub folders to the destination directory.

    Args:
        files (List[str]): List of all allowed file paths in the folder/sub-folder to copy to destination.
        destination (str): destination path to write template to.
        sub_folder_path (str): Path to sub folder to create in destination. Defaults to "".
    """
    for source_path in files:
        filename = os.path.basename(source_path)

        if sub_folder_path:
            destination_path = os.path.join(destination, sub_folder_path, filename)
        else:
            destination_path = os.path.join(destination, filename)
        copy(source_path, destination_path)


def build_template(
    config: TemplateVariables,
    template_src: str,
    destination: str = ".matcha/infrastructure",
    verbose: Optional[bool] = False,
) -> None:
    """Build and copy the template to the project directory.

    Args:
        config (TemplateVariables): variables to apply to the template
        template_src (str): path of the template to use
        destination (str): destination path to write template to. Defaults to ".matcha/infrastructure".
        verbose (bool, optional): additional output is shown when True. Defaults to False.

    Raises:
        MatchaPermissionError: when there are no write permissions on the configuration destination
    """
    try:
        print_status(build_status("\nBuilding configuration template..."))

        # Override configuration if it already exists
        if os.path.exists(destination):
            rmtree(destination)

        os.makedirs(destination, exist_ok=True)
        if verbose:
            print_status(
                build_substep_success_status(
                    f"Ensure template destination directory: {destination}"
                )
            )

        # Define additional non-tf files that are needed from the main module
        main_module_filenames = [
            ".gitignore",
            ".terraform.lock.hcl",
        ]

        for filename in main_module_filenames:
            source_path = os.path.join(template_src, filename)
            destination_path = os.path.join(destination, filename)
            copy(source_path, destination_path)

        files = glob.glob(os.path.join(template_src, "*.tf"))
        copy_files(files, destination)

        for submodule_name in SUBMODULE_NAMES:
            os.makedirs(os.path.join(destination, submodule_name), exist_ok=True)
            for ext in ALLOWED_EXTENSIONS:
                files = glob.glob(
                    os.path.join(template_src, submodule_name, f"*.{ext}")
                )
                sub_folder_path = submodule_name
                copy_files(files, destination, sub_folder_path)

            if verbose:
                print_status(
                    build_substep_success_status(
                        f"{submodule_name} module configuration was copied"
                    )
                )

        if verbose:
            print_status(build_substep_success_status("Configuration was copied"))

        configuration_destination = os.path.join(destination, "terraform.tfvars.json")
        with open(configuration_destination, "w") as f:
            json.dump(dataclasses.asdict(config), f)

        if verbose:
            print_status(build_substep_success_status("Template variables were added."))

    except PermissionError:
        raise MatchaPermissionError(
            f"Error - You do not have permission to write the configuration. Check if you have write permissions for '{destination}'."
        )

    if verbose:
        print_status(
            build_substep_success_status("Template configuration has finished!")
        )

    print_status(
        build_step_success_status(
            f"The configuration template was written to {destination}"
        )
    )
