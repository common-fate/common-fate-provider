import os
from commonfate_provider import loader
from commonfate_provider.provider import DictLoader
from commonfate_provider.runtime import AWSLambdaRuntime
import importlib.resources
import json
import importlib
import pkgutil


def import_submodules(package, recursive=True):
    """Import all submodules of a module, recursively, including subpackages

    :param package: package (name or actual module)
    :type package: str | module
    :rtype: dict[str, types.ModuleType]
    """
    if isinstance(package, str):
        package = importlib.import_module(package)
    results = {}
    for loader, name, is_pkg in pkgutil.walk_packages(package.__path__):
        full_name = package.__name__ + "." + name
        results[full_name] = importlib.import_module(full_name)
        if recursive and is_pkg:
            results.update(import_submodules(full_name))
    return results


# this package is generated by the PDK packaging process,
# and will exist in the AWS Lambda deployment zip file.
try:
    import commonfate_provider_dist

    import_submodules(commonfate_provider_dist)
except ImportError:
    raise ImportError(
        "commonfate_provider_dist didn't exist. Usually this means that the Provider has been incorrectly packaged. Please report this issue to the provider developer."
    )


def to_camel_case(snake_str):
    """
    Split each word by seperator "_" and capitalize the
    first letter of each component with '.title()' method and join the result.

    For example, `snake_case` will be converted to `SnakeCase`
    """
    components = snake_str.split("_")

    return "".join(x.title() for x in components)


def load_metadata_value(provider_data: dict, key: str):
    try:
        val = provider_data[key]
        return val
    except KeyError:
        raise KeyError(
            f"{key} was not found in the manifest.json file. Usually this means that the provider has been incorrectly packaged. Please report this issue to the provider developer."
        )


(Provider, Args) = loader.load_provider_from_subclass()

config_dict = {}
for key in Provider.export_schema():
    config_dict[key] = os.getenv(to_camel_case(key))

config_loader = DictLoader(config_dict=config_dict)
provider = Provider(config_loader)

with importlib.resources.open_text("commonfate_provider_dist", "manifest.json") as file:
    provider_data = json.load(file)


runtime = AWSLambdaRuntime(
    provider,
    Args,
    name=load_metadata_value(provider_data, "name"),
    version=load_metadata_value(provider_data, "version"),
    publisher=load_metadata_value(provider_data, "publisher"),
)


def lambda_handler(event, context):
    return runtime.handle(event, context)
