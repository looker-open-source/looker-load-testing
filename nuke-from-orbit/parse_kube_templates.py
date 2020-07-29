import os
from jinja2 import Template
import json
import configparser
from pathlib import Path


def combine_tf_outputs():

    files = Path("terraform").glob("**/output.json")
    output_dict = {}
    for file in files:
        section = json.loads(file.read_text())
        output_dict = {**output_dict, **section}

    flattened = {k: v["value"] for k, v in output_dict.items()}

    # set env variables for future kubernetes secrets
    os.environ["LOOKER_USER"] = flattened["user"]
    os.environ["LOOKER_PASS"] = flattened["pass"]

    return flattened


def add_aws_creds(profile):
    aws_path = Path(Path.home().joinpath(".aws", "credentials"))
    assert aws_path.exists(), "Couldn't find AWS credentials file! Make sure it exists"

    config = configparser.ConfigParser()
    config.read(str(aws_path))
    target_profile = config[profile]

    os.environ["AWS_ACCESS_KEY"] = target_profile["aws_access_key_id"]
    os.environ["AWS_SECRET_KEY"] = target_profile["aws_secret_access_key"]

    # aws_session_token is optional
    if target_profile.get("aws_session_token"):
        os.environ["AWS_SESSION_TOKEN"] = target_profile["aws_session_token"]


def render_kubernetes_templates(values_dict):
    files = Path("kubernetes-config/templates").glob("*.yaml")
    for file in files:
        dest_file = Path(file.parent.parent.joinpath(file.name))
        template = file.read_text()
        rendered = Template(template).render(**values_dict)

        with open(dest_file, "w") as f:
            f.write(rendered)


def main():
    values_dict = combine_tf_outputs()
    add_aws_creds(values_dict["aws_profile"])
    render_kubernetes_templates(values_dict)


if __name__ == "__main__":
    main()
