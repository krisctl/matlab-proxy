# Copyright (c) 2020-2023 The MathWorks, Inc.
# Script to help user troubleshoot common errors with the environment
import shutil

import subprocess
import os
import platform
from dataclasses import dataclass

GREEN_OK = "\033[32mOK\033[0m" if os.name != "nt" else "ok"
RED_X = "\033[31m X\033[0m" if os.name != "nt" else " X"


@dataclass
class Report:
    body: str
    recommendations: str
    has_error: bool

    def __str__(self) -> str:
        return "".join([self.body, self.recommendations])


def print_environment_info():
    """Printing output information for various commands
    # list the python environment
    which python pip python3

    # list the version of python & pip
    python --version
    pip --version
    python3 --version

    # list the packages installed
    python -m pip list | grep -E "jupyter|matlab-proxy|jupyter-matlab-proxy|notebook"

    # list the jupyter executable
    which jupyter

    # list the matlab-proxy-app on path
    which matlab-proxy-app

    # list whether the server extensions are enabled
    jupyter serverextension list
    jupyter nbextension list
    jupyter labextension list

    Returns:
        _type_: output for all the above-mentioned commands and logs from matlab-proxy log file
    """
    output: str = ""
    output += list_matlab()
    output += list_matlab_proxy_on_path()
    output += list_jupyter_executable()
    output += check_python_and_pip_installed()

    output += os_info()
    output += list_conda_related_information()
    output += list_installed_packages()

    output += list_server_extensions()
    output += list_env_vars()
    output += collect_logs_from_logfile()

    print(output)


@dataclass
class cmd_output:
    command: str
    output: str
    isError: bool

    def __str__(self) -> str:
        err_icon = RED_X if self.isError else GREEN_OK
        return f"{self.command} - {self.output} - {err_icon}\n"


@dataclass
class cmd_only_output(cmd_output):
    def __str__(self) -> str:
        return f"{self.output}\n"


def find_executable(*args):
    """Runs which command (or OS type equivalent of which) to find the executable on path

    Returns:
        output: A list of outputs of the executed commands
    """
    output: list = []
    for name in args:
        path = shutil.which(name)
        output.append(cmd_output(name, path, True if path is None else False))
    return output


def find_executable_and_version(cmd: str, suppress_suggestions: bool):
    """A helper function to execute which command along with --version option

    Args:
        cmd (str): command to be executed
        suppress_suggestions (bool): provides an option to suppress suggestions that are
        displayed to the user.

    Returns:
        list: containing which command output and the version information output
    """
    output: list = []
    version = ""
    rep = process_output(find_executable, suppress_suggestions, cmd)
    output.append(rep)
    if not rep.has_error:
        version = process_output(exec_command, suppress_suggestions, f"{cmd} --version")
        output.append(version)
    return output


def exec_command(*args):
    """A utility to run a custom command and gather output.

    Returns:
        list: of outputs that are returned by the function
    """
    output: list = []
    for cmd in args:
        try:
            completed_process = subprocess.run(
                cmd, shell=True, capture_output=True, timeout=10, text=True
            )
            output.append(
                cmd_only_output(
                    cmd,
                    completed_process.stdout.strip() + completed_process.stderr.strip(),
                    True if completed_process.stderr != "" else False,
                )
            )
        except TimeoutError:
            output.append(cmd_only_output(cmd, f"{cmd} command timed out!", True))
    return output


def generate_header(title: str):
    return (
        str(
            prettify(
                boundary_filler="-",
                text_arr=[f"{title}"],
            )
        )
        + "\n"
    )


def os_info():
    title = "OS information"
    header = generate_header(title)
    os_data = [
        platform.system(),
        platform.release(),
        platform.platform(),
    ]
    status = "\n".join(f"{cmd}" for cmd in os_data)
    uname_op = process_output(exec_command, False, "uname -v")
    return header + status + "\n" + uname_op.__str__()


def check_python_and_pip_installed():
    title = "Python and pip executables"
    header = generate_header(title)
    commands_to_execute = ["python", "pip", "python3"]
    outputs = [find_executable_and_version(cmd, False) for cmd in commands_to_execute]
    flat_outputs = [item for sublist in outputs for item in sublist]
    return header + "".join(op.__str__() for op in flat_outputs)


def list_matlab():
    title = "matlab executable"
    header = generate_header(title)
    rep = process_output(find_executable, False, "matlab")
    return header + rep.__str__()


def list_installed_packages():
    title = "Installed packages"
    header = generate_header(title)
    cmd_output = process_output(
        exec_command,
        True,
        'python -m pip list | grep -E "jupyter|matlab-proxy|jupyter-matlab-proxy|notebook"',
    )
    return header + cmd_output.__str__()


def list_jupyter_executable():
    title = "jupyter executable"
    header = generate_header(title)
    cmd_output = process_output(find_executable, False, "jupyter")
    return header + cmd_output.__str__()


def process_output(func, suppress_suggestions, *args):
    """Higher-order helper function that calls find_executable and primes the output for reporting


    Args:
        func (*args): Expects either of find_executable or exec_command functions as input
        suppress_suggestions (bool): option to suppress suggestions shown to the user

    Returns:
        Report: An object of dataclass Report that contains information like command output,
        errors, recommendations to be made to the users.
    """
    body: str = ""
    error: bool = False
    err_recommendation: str = ""
    for cmd_pair in func(*args):
        body = cmd_pair.__str__()
        if cmd_pair.output is None:
            error = True
        if error and suppress_suggestions != True:
            err_recommendation = f"Recommendation: {cmd_pair.command} is not installed. Please install {cmd_pair.command}.\n"
    rep = Report(body=body, recommendations=err_recommendation, has_error=error)
    return rep


def list_matlab_proxy_on_path():
    title = "matlab-proxy-app executable"
    header = generate_header(title)
    cmd_output = process_output(find_executable, False, "matlab-proxy-app")
    return header + cmd_output.__str__()


def list_env_vars():
    title = "Environment variables"
    header = generate_header(title)
    cmd_output = process_output(exec_command, True, 'env | grep -iE "matlab|mw|mwi"')
    return header + cmd_output.__str__()


def list_server_extensions():
    title = "Server extensions"
    header = generate_header(title)

    commands_to_execute = [
        "jupyter serverextension list",
        "jupyter nbextension list",
        "jupyter labextension list",
    ]
    outputs = [process_output(exec_command, False, cmd) for cmd in commands_to_execute]
    return header + "".join(op.__str__() for op in outputs)


def collect_logs_from_logfile():
    title = "matlab proxy logs"
    header = generate_header(title)
    log_file = os.environ.get("MWI_LOG_FILE")
    logs = []
    if log_file != None and os.path.exists(log_file):
        with open(log_file, "r") as lf:
            logs = lf.read().splitlines()

    return header + "\n".join(logs)


def list_conda_related_information():
    title = "Conda information"
    header = generate_header(title)
    outputs = find_executable_and_version("conda", True)

    # conda envs
    env_list = process_output(exec_command, True, "conda env list")
    return header + "".join(op.__str__() for op in outputs) + env_list.__str__()


def prettify(boundary_filler=" ", text_arr=[]):
    """Prettify array of strings with borders for stdout

    Args:
        boundary_filler (str, optional): Upper and lower border filler for text. Defaults to " ".
        text_arr (list, optional):The text array to prettify. Each element will be added to a newline. Defaults to [].

    Returns:
        [str]: Prettified String
    """

    import sys

    if not sys.stdout.isatty():
        return (
            "\n============================\n"
            + "\n".join(text_arr)
            + "\n============================\n"
        )

    size = os.get_terminal_size()
    cols, _ = size.columns, size.lines

    if any(len(text) > cols for text in text_arr):
        result = ""
        for text in text_arr:
            result += text + "\n"
        return result

    upper = "\n" + "".ljust(cols, boundary_filler) + "\n" if len(text_arr) > 0 else ""
    lower = "".ljust(cols, boundary_filler) if len(text_arr) > 0 else ""

    content = ""
    for text in text_arr:
        content += text.center(cols) + "\n"

    result = upper + content + lower

    return result


def main():
    print_environment_info()


if __name__ == "__main__":
    main()
