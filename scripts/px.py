from argparse import ArgumentParser
from subprocess import Popen
from pathlib import Path
from urllib.parse import urlsplit, SplitResult
from typing import List
from types import CodeType
from types import ModuleType
from marshal import dumps
import sys

_Path = Path

def Path(p):
    return _Path(p).resolve()

def dump2bytecode(cobj: CodeType) -> bytes:
    data = bytearray()
    bytecode = dumps(cobj)
    data.extend(bytecode)
    return data

def emit_code(module_name: str, module_doc: str,
              code: bytes) -> str:
    return f"{module_name!s} = ModuleType({module_name!r}, {module_doc!r})\n" + \
        f"{module_name!s}.__path__ = None\n" + \
        f"{module_name!s}.__package__ = {module_name!r}\n" + \
        f"exec(loads({code!r}), {module_name!s}.__dict__)\n"


def emit_string(s: str) -> str:
    return s + "\n"

def packing(files: List[Path], output: Path) -> None:
    main_module = output.stem
    code = bytearray()
    code.extend(emit_string("from marshal import loads")
                .encode("utf-8"))
    code.extend(emit_string("from types import ModuleType")
                .encode("utf-8"))
    submodules = []
    for file in files:
        with file.open(encoding="utf8") as f:
            data = f.read()
        cobj = compile(data, file.name, 'exec')
        module_name = file.stem
        submodules.append(module_name)
        module_doc = f"Sub-Module {module_name} of {main_module}"
        tmp = emit_code( module_name, module_doc,
                         dump2bytecode(cobj) )
        code.extend(tmp.encode("utf8"))
    code.extend(emit_string(f"__all__ = {submodules!r}")
                .encode("utf8"))
    code.extend(emit_string("__dir__ = lambda: __all__")
                .encode("utf8"))
    output.write_bytes(code)

def main():
    parser = ArgumentParser(
        description="NOTE: require command {git, rm, tree} be installed"
    )
    parser.add_argument("--pkgs", type=Path, default=Path("./.pkgs"),
                        help="third-part package store")

    sub_parser = parser.add_subparsers(dest='namespace')

    install_parser = sub_parser.add_parser("install", help='install help')
    install_parser.add_argument("install.uri", type=urlsplit,
                                metavar="uri",
                                help="install package [uri] to [pkgs]")
    install_parser.add_argument('--scheme',
                                dest='install.scheme',
                                type=str,
                                choices=('http', 'https'),
                                default='https',
                                metavar="scheme",
                                help='install package schema://uri')

    run_parser = sub_parser.add_parser("run", help='run help')
    run_parser.add_argument("run.entry", type=Path,
                            metavar="program",
                            help="proxy run program with [pkgs] package")

    uninstall_parser = sub_parser.add_parser("uninstall",
                                             help='uninstall help')
    uninstall_parser.add_argument("uninstall.uri",
                                  type=urlsplit,
                                  metavar="uri",
                                  help="uninstall package uri from [pkgs]")

    pack_parser = sub_parser.add_parser("pack", help="pack help")
    pack_parser.add_argument("pack.files", type=Path, nargs="+",
                             metavar="files",
                             help="packing files")
    pack_parser.add_argument("-o", "--output", type=Path,
                             required=True,
                             dest="pack.output",
                             metavar="output",
                             help="output module file")

    list_parser = sub_parser.add_parser("list", help="list help")

    init_parser = sub_parser.add_parser("init", help="init help")
    init_parser.add_argument("init.template", type=urlsplit,
                             metavar="template",
                             help="template uri")

    args = dict(parser.parse_args(sys.argv[1:]).__dict__)
    if not args:
        parser.print_help()
    print( "Arguments:", args )

    pkgs = args["pkgs"]
    if not pkgs.is_dir():
         sys.stderr.write(f"{pkgs!s} is not directory or not exists\n")
         sys.exit(1)

    namespace = args['namespace']
    if namespace == 'install':
        install_uri = args['install.uri']
        install_scheme = args['install.scheme']
        if install_uri.scheme == '':
            install_uri = urlsplit(
                install_scheme + "://" + install_uri.geturl()
            )
        if install_uri.netloc != '' or install_uri.path != '':
            pkg_url = install_uri.geturl()
            pkg_dest = pkgs.joinpath(Path(install_uri.path)
                                     .relative_to("/"))
            git_dest = pkg_dest.joinpath(".git")
            cmd = ["git", "clone", "--quiet", "-j 4",
                   pkg_url, str(pkg_dest)]
            if not pkg_dest.is_dir():
                sub_process = Popen(cmd)
                sub_process.wait()
                if sub_process.returncode == 0:
                    cmd = ["rm", "-rf", str(git_dest)]
                    sub_process = Popen(cmd)
                    sub_process.wait()
                sys.exit(sub_process.returncode)
            else:
                sys.stderr.write(f"'{install_uri.netloc}{install_uri.path}' exists on '{pkgs!s}'\n")
                sys.exit(1)
    elif namespace == 'uninstall':
        uninstall_uri = args['uninstall.uri']
        if uninstall_uri.scheme == '':
            uninstall_uri = urlsplit(
                "https://" + uninstall_uri.geturl()
            )
        if uninstall_uri.netloc != '' or uninstall_uri.path != '':
            pkg_dest = pkgs.joinpath(Path(uninstall_uri.path)
                                     .relative_to("/"))
            if pkg_dest.is_dir():
                sub_process = Popen(["rm", "-rf", pkg_dest])
                sub_process.wait()
                sys.exit(sub_process.returncode)
            else:
                sys.stderr.write(f"'{uninstall_uri.netloc}{uninstall_uri.path}' non-install at '{pkgs!s}'\n")
                sys.exit(1)
    elif namespace == 'run':
        entry_point = args["run.entry"]
        if entry_point.is_file():
            env = {
                "PYTHONPATH": ":".join([
                    str(pkgs),
                ]),
            }
            sub_process = Popen(["python", entry_point], env=env)
            sub_process.wait()
            sys.exit(sub_process.returncode)
    elif namespace == 'pack':
        pack_files = args["pack.files"]
        pack_output = args["pack.output"]
        for file in pack_files:
            if not file.is_file():
                sys.stderr.write(f"files {file.name} is not exists\n")
                sys.exit(1)
        if pack_output.is_file():
            (sys
             .stdout
             .write(f"warnning: {file.name} is exists will rewrite\n")
            )
        return packing(pack_files, pack_output)
    elif namespace == 'list':
        sub_process = Popen(["tree", str(pkgs)])
        sub_process.wait()
        sys.exit(sub_process.returncode)
    else: # namespace is None
        parser.print_help()

if __name__ == '__main__':
    main()
