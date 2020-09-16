from jinja2 import Template
import json
import configparser
import argparse
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parent


def combine_tf_outputs():

    print("Combining outputs")
    files = SCRIPT_PATH.joinpath("..", "terraform").glob("**/output.json")
    output_dict = {}
    for file in files:
        section = json.loads(file.read_text())
        output_dict = {**output_dict, **section}

    flattened = {k: v["value"] for k, v in output_dict.items()}

    return flattened


def add_aws_creds(values_dict):

    print("Adding user creds")
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

    return combined


def add_user_params(values_dict):
    user_config = SCRIPT_PATH.joinpath("..", "config.json")
    if user_config.exists():
        with open(user_config) as f:
            user_dict = json.load(f)

        combined = {**values_dict, **user_dict}

        return combined


def export_params(values_dict):
    # export file for future use
    with open(SCRIPT_PATH.joinpath("..", ".self_contained_params.json"), "w") as f:
        json.dump(values_dict, f)


def render_kubernetes_templates(values_dict, files):
    for file in files:
        print(f"Rendering {file}")
        dest_file = SCRIPT_PATH.joinpath(file.name)
        template = file.read_text()
        rendered = Template(template).render(**values_dict)

        with open(dest_file, "w") as f:
            f.write(rendered)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only-user-config", action="store_true", help="Only parse user config")
    parser.add_argument("--image-tag", default="latest", help="Tag to use for locust test image")
    args = parser.parse_args()

    if args.only_user_config:
        files = [
            SCRIPT_PATH.joinpath("templates", "loadtest-cert.yaml"),
            SCRIPT_PATH.joinpath("templates", "loadtest-ingress.yaml"),
            SCRIPT_PATH.joinpath("templates", "locust-controller.yaml"),
            SCRIPT_PATH.joinpath("templates", "locust-worker-controller.yaml"),
            SCRIPT_PATH.joinpath("templates", "config-default.yaml")
        ]
        values_dict = {}
        user_dict = add_user_params(values_dict)
        user_dict["image_tag"] = args.image_tag
        user_dict["external"] = True
        render_kubernetes_templates(user_dict, files)
    else:
        files = SCRIPT_PATH.joinpath("templates").glob("*.yaml")
        values_dict = combine_tf_outputs()
        aws_dict = add_aws_creds(values_dict)
        combined_dict = add_user_params(aws_dict)
        combined_dict["image_tag"] = args.image_tag
        export_params(combined_dict)
        render_kubernetes_templates(combined_dict, files)


if __name__ == "__main__":
    main()
