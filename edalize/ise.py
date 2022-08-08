# Copyright edalize contributors
# Licensed under the 2-Clause BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-2-Clause

import os.path

from edalize.edatool import Edatool


class Ise(Edatool):

    argtypes = ["vlogdefine", "vlogparam", "generic"]

    MAKEFILE_TEMPLATE = """#Auto generated by Edalize
include config.mk

all: $(TOPLEVEL).bit

$(TOPLEVEL).bit:  $(NAME)_run.tcl $(NAME).xise
	xtclsh $^

$(NAME).xise: $(NAME).tcl
	xtclsh $<
"""

    TCL_RUN_FILE_TEMPLATE = """#Auto generated by Edalize
project open $::argv
process run "Generate Programming File"
"""

    TCL_FILE_TEMPLATE = """#Auto generated by Edalize
proc project_new_exist_ok name {{
    if {{ [catch  {{ project new $name }}] }} {{
        project open $name
    }}
}}

proc xfile_add_exist_ok name {{
    if {{ [catch {{ xfile get [file tail $name] name }}] }} {{
        xfile add $name
    }}
}}

project_new_exist_ok {design}
project set family {family}
project set device {device}
project set package {package}
project set speed {speed}
project set "Generate Detailed MAP Report" true
"""

    PGM_FILE_TEMPLATE = """
# Batch script for programming the device using a JTAG interface.
# Used with:
# $ impact -batch {pgm_file}

setMode -bscan
setCable -port auto
identify
assignFile -p {board_device_index} -file {bit_file}
program -p {board_device_index}
saveCDF -file {cdf_file}
quit
"""

    @classmethod
    def get_doc(cls, api_ver):
        if api_ver == 0:
            return {
                "description": "Xilinx ISE Design Suite",
                "members": [
                    {
                        "name": "family",
                        "type": "String",
                        "desc": "FPGA family (e.g. spartan6)",
                    },
                    {
                        "name": "device",
                        "type": "String",
                        "desc": "FPGA device (e.g. xc6slx45)",
                    },
                    {
                        "name": "package",
                        "type": "String",
                        "desc": "FPGA package (e.g. csg324)",
                    },
                    {
                        "name": "speed",
                        "type": "String",
                        "desc": "FPGA speed grade (e.g. -2)",
                    },
                    {
                        "name": "board_device_index",
                        "type": "String",
                        "desc": "Specifies the FPGA's device number in the JTAG chain, starting at 1",
                    },
                ],
            }

    def configure_main(self):
        for i in ["family", "device", "package", "speed"]:
            if not i in self.tool_options:
                raise RuntimeError("Missing required option '{}'".format(i))
        self._write_tcl_file()
        with open(os.path.join(self.work_root, "Makefile"), "w") as f:
            f.write(self.MAKEFILE_TEMPLATE)
        with open(os.path.join(self.work_root, "config.mk"), "w") as f:
            f.write("NAME     := {}\n".format(self.name))
            f.write("TOPLEVEL := {}\n".format(self.toplevel))
        with open(os.path.join(self.work_root, self.name + "_run.tcl"), "w") as f:
            f.write(self.TCL_RUN_FILE_TEMPLATE)

    def _write_tcl_file(self):
        tcl_file = open(os.path.join(self.work_root, self.name + ".tcl"), "w")

        tcl_file.write(
            self.TCL_FILE_TEMPLATE.format(
                design=self.name,
                family=self.tool_options["family"],
                device=self.tool_options["device"],
                package=self.tool_options["package"],
                speed=self.tool_options["speed"],
            )
        )

        if self.vlogdefine:
            s = 'project set "Verilog Macros" "{}" -process "Synthesize - XST"\n'
            tcl_file.write(
                s.format(
                    "|".join(
                        [
                            k + "=" + self._param_value_str(v)
                            for k, v in self.vlogdefine.items()
                        ]
                    )
                )
            )

        if self.vlogparam or self.generic:
            genparam = self.vlogparam.copy()
            genparam.update(self.generic)
            s = 'project set "Generics, Parameters" "{}" -process "Synthesize - XST"\n'
            tcl_file.write(
                s.format(
                    "|".join(
                        [
                            k + "=" + self._param_value_str(v, '\\"')
                            for k, v in genparam.items()
                        ]
                    )
                )
            )

        (src_files, incdirs) = self._get_fileset_files(
            force_slash=True
        )  # ISE tcl doesn't like '\', so '/' is forced

        if incdirs:
            tcl_file.write(
                'project set "Verilog Include Directories" "{}" -process "Synthesize - XST"\n'.format(
                    "|".join(incdirs)
                )
            )

        _libraries = []
        for f in src_files:
            if f.file_type == "tclSource":
                tcl_file.write("source {}\n".format(f.name))
            elif f.file_type.startswith("verilogSource"):
                tcl_file.write("xfile add {}\n".format(f.name))
            elif f.file_type == "UCF":
                tcl_file.write("xfile_add_exist_ok {}\n".format(f.name))
            elif f.file_type == "BMM":
                tcl_file.write("xfile add {}\n".format(f.name))
            elif f.file_type.startswith("vhdlSource"):
                if f.logical_name:
                    if not f.logical_name in _libraries:
                        tcl_file.write("lib_vhdl new {}\n".format(f.logical_name))
                        _libraries.append(f.logical_name)
                    _s = "xfile add {} -lib_vhdl {}\n"
                    tcl_file.write(_s.format(f.name, f.logical_name))
                else:
                    tcl_file.write("xfile add {}\n".format(f.name))
            elif f.file_type == "user":
                pass

        tcl_file.write('project set top "{}"\n'.format(self.toplevel))
        tcl_file.close()

    def run_main(self):
        pgm_file_name = os.path.join(self.work_root, self.name + ".pgm")
        self._write_pgm_file(pgm_file_name)
        self._run_tool("impact", ["-batch", pgm_file_name])

    def _write_pgm_file(self, pgm_file_name):
        pgm_file = open(pgm_file_name, "w")
        pgm_file.write(
            self.PGM_FILE_TEMPLATE.format(
                pgm_file=pgm_file_name,
                bit_file=os.path.join(self.work_root, self.toplevel + ".bit"),
                cdf_file=os.path.join(self.work_root, self.toplevel + ".cdf"),
                board_device_index=self.tool_options.get("board_device_index", "1"),
            )
        )
        pgm_file.close()
