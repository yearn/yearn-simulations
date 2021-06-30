from utils import dotdict

import importlib.util


def main():
    custom = dotdict({})
    custom.name = "ryan"
    custom.age = "32"
    print(custom)
    s = "0x6598d4366D5A45De4Bf2D2468D877E0b6436Ae76"
    s = f"s_{s}"
    print(s)
    spec = importlib.util.spec_from_file_location("module.name", f"./custom_scripts/{s}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data = "secret message"
    module.my_test(data)

