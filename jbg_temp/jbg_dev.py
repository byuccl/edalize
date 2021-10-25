import sys
import pathlib
import os

TEST_DIR = pathlib.Path(__file__).absolute().parent
sys.path.append(str(TEST_DIR.parent))

import edalize

BFASST_EXAMPLES_PATH = pathlib.Path.home() / "bfasst" / "examples"

ADD8_PATH = BFASST_EXAMPLES_PATH / "basic" / "add8_r_rst" / "add8.v"
ADD8_XDC = TEST_DIR / "constraints.xdc"


work_root = pathlib.Path("build")
work_root_vtr = pathlib.Path("build_vtr")

tool_vivado = "vivado"
tool_vtr = "vtr"

vtr_path = pathlib.Path("/home/jgoeders/vtr")

files = [
    {"name": str(ADD8_PATH), "file_type": "verilogSource"},
    {"name": str(ADD8_XDC), "file_type": "xdc"},
    {
        # "name": "timing/k4_N4_90nm.xml",
        "name": str(vtr_path / "vtr_flow" / "arch" / "timing" / "k4_N4_90nm.xml"),
        "file_type": "vtr_arch",
    },
]

tool_options_vivado = {"part": "xc7a35tcpg236-1"}

TRY_PATH = 1
if TRY_PATH:
    os.environ["PATH"] += os.pathsep + "/home/jgoeders/vtr/vtr_flow/scripts"
    tool_options_vtr = { "route_chan_width": 16}
else:
    tool_options_vtr = {"vtr_path": "/home/jgoeders/vtr", "route_chan_width": 16}

edam = {
    "files": files,
    "name": "add8",
    "toplevel": "add8",
    "tool_options": {"vivado": tool_options_vivado, "vtr": tool_options_vtr},
}

backend_vivado = edalize.get_edatool(tool_vivado)(edam=edam, work_root=work_root)
backend_vtr = edalize.get_edatool(tool_vtr)(edam=edam, work_root=str(work_root_vtr))

work_root.mkdir(exist_ok=True)
work_root_vtr.mkdir(exist_ok=True)

backend_vtr.configure()
backend_vtr.build()


backend_vivado.configure()
# backend_vivdao.build()
