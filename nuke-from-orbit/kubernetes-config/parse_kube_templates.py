from jinja2 import Template
import json
import configparser
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parent


def combine_tf_outputs():

    files = SCRIPT_PATH.joinpath("..", "terraform").glob("**/output.json")
    output_dict = {}
    for file in files:
        section = json.loads(file.read_text())
        output_dict = {**output_dict, **section}

    flattened = {k: v["value"] for k, v in output_dict.items()}

    return flattened


def add_other_creds(values_dict):
    aws_path = Path(Path.home().joinpath(".aws", "credentials"))
    assert aws_path.exists(), "Couldn't find AWS credentials file! Make sure it exists"

    profile = values_dict["aws_profile"]
    config = configparser.ConfigParser()
    config.read(str(aws_path))
    target_profile = config[profile]

    aws_dict = {
        "aws_access_key": target_profile["aws_access_key_id"],
        "aws_secret_access_key": target_profile["aws_secret_access_key"],
    }

    # aws_session_token is optional
    if target_profile.get("aws_session_token"):
        aws_dict["aws_session_token"] = target_profile["aws_session_token"]

    combined = {**values_dict, **aws_dict}

    user_config = SCRIPT_PATH.joinpath("..", "user_params.json")
    if user_config.exists():
        with open(user_config) as f:
            user_dict = json.load(f)

        combined = {**combined, **user_dict}

    # export file for future use
    with open(SCRIPT_PATH.joinpath("..", "params.json"), "w") as f:
        json.dump(combined, f)


def render_kubernetes_templates(values_dict):
    files = Path("templates").glob("*.yaml")
    for file in files:
        dest_file = SCRIPT_PATH.joinpath(file.name)
        template = file.read_text()
        rendered = Template(template).render(**values_dict)

        with open(dest_file, "w") as f:
            f.write(rendered)


def main():
    values_dict = combine_tf_outputs()
    add_other_creds(values_dict)
    render_kubernetes_templates(values_dict)


if __name__ == "__main__":
    main()
