import glob
import os
import re
import shlex
from collections.abc import Iterable
from typing import Any, cast

from IPython.core.interactiveshell import InteractiveShell
from IPython.core.magic import Magics, line_magic, magics_class
from IPython.terminal.interactiveshell import TerminalInteractiveShell
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document

from edai.tool.interpreter import Interpreter
from edai.tool.repl import MockBackend

# =============================================================================
# 1. RainaSynth Tcl 命令数据库
#    从 C++ 注册代码 (tcl_register_*.h) 中提取的完整命令列表
# =============================================================================

# 命令信息结构:
#   options:         所有可识别的选项名（含 -help）
#   switch_options:  布尔开关（不跟值）
#   category:        子系统分类

TCL_COMMANDS: dict[str, dict[str, Any]] = {
    # === config / flow ===
    "flow_init": {"options": ["-config", "-help"], "switch_options": []},
    "db_init": {"options": ["-config", "-help"], "switch_options": []},
    "flow_exit": {"options": [], "switch_options": []},
    "flow_config": {"options": ["-config", "-help"], "switch_options": []},
    # === database (idb) ===
    "idb_init": {"options": ["-config", "-help"], "switch_options": []},
    "tech_lef_init": {"options": ["-path", "-help"], "switch_options": []},
    "lef_init": {"options": ["-path", "-help"], "switch_options": []},
    "def_init": {"options": ["-path", "-help"], "switch_options": []},
    "verilog_init": {"options": ["-path", "-top", "-help"], "switch_options": []},
    "def_save": {"options": ["-name", "-path", "-help"], "switch_options": []},
    "lef_save": {"options": ["-path", "-help"], "switch_options": []},
    "netlist_save": {
        "options": ["-name", "-path", "-exclude_cell_names", "-add_space", "-help"],
        "switch_options": ["-add_space"],
    },
    "gds_save": {"options": ["-name", "-path", "-help"], "switch_options": []},
    "json_save": {"options": ["-name", "-path", "-discard", "-help"], "switch_options": []},
    "aimp_random": {"options": ["-dir", "-name", "-number", "-help"], "switch_options": []},
    # === database operations ===
    "set_net": {"options": ["-net_name", "-type", "-help"], "switch_options": []},
    "merge_nets": {"options": [], "switch_options": []},
    "remove_except_pg_net": {"options": [], "switch_options": []},
    "clear_blockage": {"options": ["-type", "-help"], "switch_options": []},
    "idb_get": {"options": ["-type", "-help"], "switch_options": []},
    "delete_inst": {"options": ["-name", "-help"], "switch_options": []},
    "delete_net": {"options": ["-name", "-help"], "switch_options": []},
    "create_inst": {"options": ["-name", "-help"], "switch_options": []},
    "create_net": {"options": ["-name", "-help"], "switch_options": []},
    "place_instance": {"options": ["-config", "-help"], "switch_options": []},
    # === PDN ===
    "add_pdn_io": {"options": ["-help"], "switch_options": []},
    "global_net_connect": {"options": ["-help"], "switch_options": []},
    "place_pdn_port": {"options": ["-help"], "switch_options": []},
    "create_grid": {"options": ["-help"], "switch_options": []},
    "create_stripe": {"options": ["-help"], "switch_options": []},
    "connect_two_layer": {"options": ["-help"], "switch_options": []},
    "connect_macro_pdn": {"options": ["-help"], "switch_options": []},
    "connect_io_pin_to_pdn": {"options": ["-help"], "switch_options": []},
    "connect_pdn_stripe": {"options": ["-help"], "switch_options": []},
    "add_segment_stripe": {"options": ["-help"], "switch_options": []},
    "add_segment_via": {"options": ["-help"], "switch_options": []},
    # === placer (iPL) ===
    "run_placer": {"options": ["-config", "-json", "-help"], "switch_options": ["-json"]},
    "run_filler": {"options": ["-config", "-help"], "switch_options": []},
    "run_incremental_flow": {"options": ["-config", "-help"], "switch_options": []},
    "run_incremental_lg": {"options": [], "switch_options": []},
    "placer_check_legality": {"options": [], "switch_options": []},
    "placer_report": {"options": [], "switch_options": []},
    "init_pl": {"options": ["-config", "-help"], "switch_options": []},
    "destroy_pl": {"options": [], "switch_options": []},
    "placer_run_mp": {"options": [], "switch_options": []},
    "placer_run_gp": {"options": [], "switch_options": []},
    "placer_run_lg": {"options": [], "switch_options": []},
    "placer_run_dp": {"options": [], "switch_options": []},
    "pl_config": {"options": ["-config", "-help"], "switch_options": []},
    # === CTS ===
    "run_cts": {"options": ["-config", "-help"], "switch_options": []},
    "cts_report": {"options": [], "switch_options": []},
    "cts_save_tree": {"options": ["-path", "-help"], "switch_options": []},
    "cts_config": {"options": ["-config", "-help"], "switch_options": []},
    # === Router (iRT) ===
    "init_rt": {"options": ["-config", "-help"], "switch_options": []},
    "run_ert": {"options": ["-config", "-help"], "switch_options": []},
    "run_rt": {"options": ["-config", "-help"], "switch_options": []},
    "destroy_rt": {"options": [], "switch_options": []},
    "rt_clean_def": {"options": [], "switch_options": []},
    "rt_fix_fanout": {"options": ["-help"], "switch_options": []},
    "rt_get_congestion": {"options": ["-help"], "switch_options": []},
    # === STA (iSTA) ===
    "run_sta": {"options": ["-config", "-help"], "switch_options": []},
    "init_sta": {"options": ["-config", "-help"], "switch_options": []},
    "report_sta": {"options": [], "switch_options": []},
    "build_clock_tree": {"options": [], "switch_options": []},
    "set_design_workspace": {"options": ["-path", "-help"], "switch_options": []},
    "read_netlist": {"options": ["-help"], "switch_options": []},
    "read_lef_def": {"options": ["-path", "-help"], "switch_options": []},
    "read_liberty": {"options": ["-path", "-help"], "switch_options": []},
    "link_design": {"options": ["-help"], "switch_options": []},
    "read_spef": {"options": ["-path", "-help"], "switch_options": []},
    "read_sdc": {"options": ["-path", "-help"], "switch_options": []},
    "report_timing": {"options": ["-help"], "switch_options": []},
    "report_constraint": {"options": ["-help"], "switch_options": []},
    "def_to_verilog": {"options": ["-help"], "switch_options": []},
    "verilog_to_def": {"options": ["-help"], "switch_options": []},
    "get_libs": {"options": ["-help"], "switch_options": []},
    "test_string_list_list": {"options": [], "switch_options": []},
    # === Power (iPA) ===
    "run_power": {"options": ["-config", "-help"], "switch_options": []},
    "set_pwr_design_workspace": {"options": ["-path", "-help"], "switch_options": []},
    "report_power": {"options": [], "switch_options": []},
    "read_pg_spef": {"options": ["-path", "-help"], "switch_options": []},
    "report_ir_drop": {"options": [], "switch_options": []},
    # === Timing Optimization (iTO) ===
    "run_to": {"options": ["-config", "-help"], "switch_options": []},
    "run_to_drv": {"options": ["-config", "-help"], "switch_options": []},
    "run_to_drv_special_net": {"options": ["-config", "-help"], "switch_options": []},
    "run_to_hold": {"options": ["-config", "-help"], "switch_options": []},
    "run_to_setup": {"options": ["-config", "-help"], "switch_options": []},
    "run_to_buffering": {"options": ["-config", "-help"], "switch_options": []},
    "to_config": {"options": ["-config", "-help"], "switch_options": []},
    # === Net Optimizer (iNO) ===
    "run_no_fixfanout": {"options": ["-config", "-help"], "switch_options": []},
    "run_no_fixIO": {"options": ["-config", "-help"], "switch_options": []},
    "no_config": {"options": ["-config", "-help"], "switch_options": []},
    # === DRC (iDRC) ===
    "check_def": {"options": ["-path", "-help"], "switch_options": []},
    "destroy_drc": {"options": [], "switch_options": []},
    "init_drc": {"options": ["-config", "-help"], "switch_options": []},
    "drc_cmp_violation": {"options": ["-help"], "switch_options": []},
    "run_drc": {"options": ["-config", "-help"], "switch_options": []},
    "save_drc": {"options": ["-path", "-help"], "switch_options": []},
    # === Evaluation ===
    "run_timing_eval": {"options": ["-config", "-help"], "switch_options": []},
    "run_wirelength_eval": {"options": ["-config", "-help"], "switch_options": []},
    "run_density_eval": {"options": ["-config", "-help"], "switch_options": []},
    "egr_config": {"options": ["-config", "-help"], "switch_options": []},
    # === Feature ===
    "feature_summary": {"options": ["-help"], "switch_options": []},
    "feature_tool": {"options": ["-help"], "switch_options": []},
    "feature_eval_map": {"options": ["-help"], "switch_options": []},
    "feature_route": {"options": ["-help"], "switch_options": []},
    "feature_route_read": {"options": ["-path", "-help"], "switch_options": []},
    "feature_cong_map": {"options": ["-help"], "switch_options": []},
    # === ECO ===
    "eco_repair_via": {"options": ["-config", "-help"], "switch_options": []},
    # === GUI ===
    "gui_start": {"options": ["-help"], "switch_options": []},
    "gui_show": {"options": ["-help"], "switch_options": []},
    "gui_hide": {"options": ["-help"], "switch_options": []},
    "gui_show_drc": {"options": ["-help"], "switch_options": []},
    "gui_show_cts": {"options": ["-help"], "switch_options": []},
    "gui_show_pl": {"options": ["-help"], "switch_options": []},
    "gui_show_graph": {"options": ["-help"], "switch_options": []},
    "capture_design": {"options": ["-help"], "switch_options": []},
    # === Report ===
    "report_db": {"options": ["-help"], "switch_options": []},
    "report_wirelength": {"options": ["-help"], "switch_options": []},
    "report_congestion": {"options": ["-help"], "switch_options": []},
    "report_route": {"options": ["-help"], "switch_options": []},
    "report_inst_distro": {"options": ["-help"], "switch_options": []},
    "report_prefixed_instance": {"options": ["-help"], "switch_options": []},
    # === Vectorization ===
    "layout_patchs": {"options": ["-help"], "switch_options": []},
    "layout_graph": {"options": ["-help"], "switch_options": []},
    "generate_vectors": {"options": ["-help"], "switch_options": []},
    "read_vectors_nets": {"options": ["-help"], "switch_options": []},
    "read_vectors_nets_patterns": {"options": ["-help"], "switch_options": []},
    # === PNP ===
    "run_pnp": {"options": ["-config", "-help"], "switch_options": []},
    "add_via1": {"options": ["-help"], "switch_options": []},
    # === Notification ===
    "init_notification": {"options": ["-config", "-help"], "switch_options": []},
    # === Contest ===
    "run_contest": {"options": ["-config", "-help"], "switch_options": []},
    "run_contest_evaluation": {"options": ["-config", "-help"], "switch_options": []},
}

ALL_COMMANDS = frozenset(TCL_COMMANDS.keys())

# 选项名 → 是否期望路径参数
PATH_OPTIONS = frozenset(
    {
        "-path",
        "-dir",
        "-config",
        "-output",
        "-work_dir",
    }
)


# =============================================================================
# 2. Tcl 解释器 — 模拟 Tcl 变量替换和命令执行
# =============================================================================


# Tcl 内建命令（非 RainaSynth 命令，但应被识别为 Tcl）
TCL_BUILTINS = frozenset({"set", "puts", "expr", "list_vars"})


class TclInterpreter(Interpreter):
    """轻量级 Tcl 解释器，用于模拟 Tcl 命令行为。

    支持:
      - 变量赋值:  set var value
      - 变量读取:  $var
      - 命令替换:  [command]
      - 内建命令:  set / puts / expr
      - 所有已注册的 Tcl 命令仿真执行
    """

    def __init__(self) -> None:
        super().__init__()
        self.variables: dict[str, str] = {}

    # ---- 变量操作 ----

    def set_var(self, name: str, value: str) -> str:
        self.variables[name] = value
        return value

    def get_var(self, name: str) -> str:
        """获取变量值，不存在时模拟 Tcl 报错。"""
        if name not in self.variables:
            raise TclError(f'can\'t read "{name}": no such variable')
        return self.variables[name]

    def unset_var(self, name: str) -> None:
        self.variables.pop(name, None)

    def clear_vars(self) -> None:
        self.variables.clear()

    def list_vars(self) -> dict[str, str]:
        return dict(self.variables)

    # ---- 替换引擎 ----

    VAR_RE = re.compile(r"\$(?:{(\w+)}|(\w+))")
    CMD_SUBST_RE = re.compile(r"\[([^\]]+)\]")

    def subst(self, text: str) -> str:
        """递归执行 $var 和 [command] 替换。"""
        text = self._subst_commands(text)
        text = self._subst_vars(text)
        return text

    def _subst_vars(self, text: str) -> str:
        def _repl(m: re.Match[str]) -> str:
            name = m.group(1) or m.group(2)
            return self.get_var(name)

        return self.VAR_RE.sub(_repl, text)

    def _subst_commands(self, text: str) -> str:
        def _repl(m: re.Match[str]) -> str:
            result = self.execute(m.group(1))
            return str(result) if result is not None else ""

        return self.CMD_SUBST_RE.sub(_repl, text)

    # ---- 入口 ----

    def execute(
        self,
        action: str = "",
        interpreter: str = "",
        args: list[str] | None = None,
        input_text: str = "",
        timeout: float = 10.0,
        **kwargs: Any,
    ) -> Any:
        """执行一行 Tcl 命令，或委托给父类处理 interpreter tool 动作。"""
        if (
            action in {"start", "input", "stop"}
            or interpreter
            or args is not None
            or input_text
            or kwargs
        ):
            return super().execute(
                action=action,
                interpreter=interpreter,
                args=args,
                input_text=input_text,
                timeout=timeout,
                **kwargs,
            )

        line = action
        if not line:
            return None

        line = line.strip()
        if not line:
            return None

        # 先做替换（命令名中不会出现 $ 或 [，安全）
        substituted = self.subst(line)
        args = shlex.split(substituted)
        if not args:
            return None

        cmd_name = args[0]
        cmd_args = args[1:]

        handler = {
            "set": self._cmd_set,
            "puts": self._cmd_puts,
            "expr": self._cmd_expr,
            "list_vars": self._cmd_list_vars,
        }.get(cmd_name)

        if handler is not None:
            return handler(cmd_args)

        if cmd_name in ALL_COMMANDS:
            return self._tcl_exec(cmd_name, cmd_args)

        return f'unknown command: "{cmd_name}"'

    def dispatch_agent_choice(self, choice: str | dict[str, Any]) -> str | None:
        """Dispatch agent-selected Tcl command text or structured payload."""
        if isinstance(choice, str):
            normalized = choice.strip()
            if not normalized:
                return None
            return cast(str | None, self.execute(normalized))

        cmd_name, tokens = self._normalize_agent_choice(choice)
        command_line = self._build_command_line(cmd_name, tokens)
        return cast(str | None, self.execute(command_line))

    # ---- 内建命令 ----

    def _cmd_set(self, args: list[str]) -> str:
        if not args:
            raise TclError('wrong # args: should be "set varName ?newValue?"')
        if len(args) == 1:
            return self.get_var(args[0])
        value = " ".join(args[1:])
        self.set_var(args[0], value)
        return value

    def _cmd_puts(self, args: list[str]) -> str:
        text = self._subst_vars(" ".join(args))
        return text

    def _cmd_list_vars(self, args: list[str]) -> str:
        if args:
            raise TclError('wrong # args: "list_vars" takes no arguments')
        if not self.variables:
            return "(no variables set)"
        lines = [f"{name} = {value}" for name, value in sorted(self.variables.items())]
        return "\n".join(lines)

    def _cmd_expr(self, args: list[str]) -> str:
        """简易算术 —— 通过 Python eval 模拟。"""
        if not args:
            return "0"
        expr_str = " ".join(args)
        expr_str = self._subst_vars(expr_str)
        safe_globals: dict[str, dict[str, Any]] = {"__builtins__": {}}
        try:
            val = eval(expr_str, safe_globals, {})
            return str(val)
        except Exception as e:
            raise TclError(f"can't interpret expression: {e}")

    # ---- TCL 自定义命令仿真 ----

    def _start(self, interpreter: str, args: list[str], timeout: float) -> dict[str, Any]:
        if interpreter and interpreter not in {"tcl", "tclsh"}:
            return super()._start(interpreter, args, timeout)

        if self._backend is not None and self._backend.is_running:
            return {"error": "interpreter already running — stop first"}

        backend = MockBackend(
            ["tclsh", *args],
            evaluator=self._mock_tcl_backend_eval,
        )
        backend.start()

        output = ""
        try:
            output = backend.read_output(timeout=timeout)
        except TimeoutError:
            pass

        stderr = backend.flush_error()
        self._backend = cast(Any, backend)

        return {"status": "started", "interpreter": "tclsh", "output": output, "stderr": stderr}

    def _tcl_exec(self, cmd: str, args: list[str]) -> str:
        backend = self._backend
        if backend is None or not backend.is_running:
            start_result = super().execute(action="start", interpreter="tcl", timeout=1.0)
            if "error" in start_result:
                raise TclError(str(start_result["error"]))

        command_line = self._build_command_line(cmd, args)
        repl_result = super().execute(action="input", input_text=command_line, timeout=1.0)
        if "error" in repl_result:
            raise TclError(str(repl_result["error"]))

        stderr = repl_result.get("stderr", "")
        if stderr:
            raise TclError(stderr.strip())
        return str(repl_result.get("output", "")).strip()

    def _mock_tcl_backend_eval(self, line: str) -> str:
        args = shlex.split(line)
        if not args:
            return ""

        cmd = args[0]
        cmd_args = args[1:]
        info = TCL_COMMANDS.get(cmd, {})
        valid_opts = set(info.get("options", []))
        switch_opts = set(info.get("switch_options", []))
        parsed_opts, pos_args = self._split_args(cmd_args, valid_opts, switch_opts)

        cat = self._categorize(cmd)

        lines = [f"    TCL cmd[{cat}]: {cmd}"]

        if parsed_opts:
            for k, v in sorted(parsed_opts.items()):
                if v is True:
                    lines.append(f"    option: {k}")
                else:
                    lines.append(f"    option: {k} = {v}")
        if pos_args:
            lines.append(f"    args: {' '.join(pos_args)}")

        lines.append(self._sim_result(cmd))
        return "\n".join(lines) + "\n"

    def _normalize_agent_choice(self, choice: dict[str, Any]) -> tuple[str, list[str]]:
        cmd_name_raw = choice.get("command") or choice.get("name")
        if not isinstance(cmd_name_raw, str) or not cmd_name_raw.strip():
            raise TclError("agent choice must include a command name")

        cmd_name = cmd_name_raw.strip()
        if cmd_name not in ALL_COMMANDS and cmd_name not in TCL_BUILTINS:
            raise TclError(f'unknown command: "{cmd_name}"')

        tokens: list[str] = []

        raw_args = choice.get("args", [])
        if raw_args is None:
            raw_args = []
        if not isinstance(raw_args, list):
            raise TclError("agent choice args must be a list")
        tokens.extend(str(arg) for arg in raw_args)

        raw_options = choice.get("options", {})
        if raw_options is None:
            raw_options = {}
        if not isinstance(raw_options, dict):
            raise TclError("agent choice options must be a dict")

        valid_opts = set(TCL_COMMANDS.get(cmd_name, {}).get("options", []))
        switch_opts = set(TCL_COMMANDS.get(cmd_name, {}).get("switch_options", []))
        for opt_name, opt_value in raw_options.items():
            option = str(opt_name)
            if cmd_name in ALL_COMMANDS and option not in valid_opts:
                raise TclError(f'unknown option for {cmd_name}: "{option}"')
            if option in switch_opts:
                if bool(opt_value):
                    tokens.append(option)
                continue
            tokens.append(option)
            if opt_value is not None:
                tokens.append(str(opt_value))

        return cmd_name, tokens

    @staticmethod
    def _build_command_line(cmd: str, args: list[str]) -> str:
        return " ".join([shlex.quote(cmd), *(shlex.quote(arg) for arg in args)])

    @staticmethod
    def _split_args(
        args: list[str], valid: set[str], switches: set[str]
    ) -> tuple[dict[str, bool | str], list[str]]:
        opts: dict[str, bool | str] = {}
        pos: list[str] = []
        i = 0
        while i < len(args):
            a = args[i]
            if a in valid:
                if a in switches:
                    opts[a] = True
                    i += 1
                else:
                    opts[a] = args[i + 1] if i + 1 < len(args) else True
                    i += 2
            else:
                pos.append(a)
                i += 1
        return opts, pos

    @staticmethod
    def _categorize(cmd: str) -> str:
        for cat, cmds in COMMAND_CATEGORIES.items():
            if cmd in cmds:
                return cat
        return "RainaSynth"

    @staticmethod
    def _sim_result(cmd: str) -> str:
        data_cmds = {
            "read_liberty",
            "read_netlist",
            "read_lef_def",
            "read_spef",
            "read_sdc",
            "lef_init",
            "def_init",
            "tech_lef_init",
            "read_pg_spef",
            "idb_init",
            "verilog_init",
            "feature_route_read",
        }
        run_cmds = {
            "run_placer",
            "run_cts",
            "run_rt",
            "run_sta",
            "run_power",
            "run_drc",
            "run_to",
            "run_pnp",
            "run_ert",
            "run_contest",
            "flow_init",
            "db_init",
            "run_filler",
            "run_incremental_flow",
            "run_incremental_lg",
            "run_timing_eval",
            "run_wirelength_eval",
            "run_density_eval",
            "placer_run_mp",
            "placer_run_gp",
            "placer_run_lg",
            "placer_run_dp",
            "run_no_fixfanout",
            "run_no_fixIO",
            "run_to_drv",
            "run_to_drv_special_net",
            "run_to_hold",
            "run_to_setup",
            "run_to_buffering",
            "run_contest_evaluation",
            "eco_repair_via",
        }
        save_cmds = {
            "def_save",
            "lef_save",
            "netlist_save",
            "gds_save",
            "json_save",
            "cts_save_tree",
            "save_drc",
        }
        report_cmds = {
            "report_timing",
            "report_sta",
            "report_power",
            "report_wirelength",
            "report_congestion",
            "report_route",
            "report_inst_distro",
            "report_db",
            "report_prefixed_instance",
            "report_constraint",
            "report_ir_drop",
            "placer_report",
            "cts_report",
            "feature_summary",
            "feature_cong_map",
        }
        if cmd in data_cmds:
            return "    [simulated] Data loaded successfully."
        if cmd in run_cmds:
            return "    [simulated] Run completed successfully."
        if cmd in save_cmds:
            return "    [simulated] File saved successfully."
        if cmd in report_cmds:
            return "    [simulated] Report generated."
        if cmd == "link_design":
            return "    [simulated] Design linked: top_module"
        if cmd in ("init_pl", "init_sta", "init_rt", "init_drc"):
            return "    [simulated] Module initialized."
        if cmd in ("destroy_pl", "destroy_rt", "destroy_drc"):
            return "    [simulated] Module destroyed."
        return "    [simulated] OK."


class TclError(Exception):
    """Tcl 运行时错误。"""

    pass


# 全局解释器实例
_interp = TclInterpreter()


# =============================================================================
# 3. 文件路径补全辅助函数
# =============================================================================


def _file_completions(pattern: str = "*") -> list[str]:
    """根据 glob 模式返回匹配的文件路径。"""
    d = os.path.dirname(pattern)
    if d and not os.path.exists(d):
        return []
    b = os.path.basename(pattern)
    sp = os.path.join(d, f"{b}*") if d else f"{b}*"
    return sorted(glob.glob(sp))


# =============================================================================
# 4. Tcl 补全器（prompt_toolkit Completer 接口）
# =============================================================================


def _looks_like_tcl(text: str) -> bool:
    """判断输入行是否看起来像 Tcl 命令（支持部分命令名匹配）。

    为避免与 Python 补全冲突:
      - 精确匹配命令名 → Tcl 模式
      - 部分匹配命令名且前缀 ≥ 2 字符 → Tcl 模式
      - 否则 → Python 模式
    """
    s = text.strip()
    if not s:
        return False
    if s.startswith("%tcl"):
        return True
    fw = s.split()[0] if s.split() else ""
    if fw in ALL_COMMANDS or fw in TCL_BUILTINS:
        return True
    # 前缀 ≥ 2 字符时才触发部分匹配，避免 'r' 等短前缀误判
    return len(fw) >= 2 and (
        any(c.startswith(fw) for c in ALL_COMMANDS) or any(c.startswith(fw) for c in TCL_BUILTINS)
    )


class TclCompleter(Completer):
    """prompt_toolkit 补全器：支持 Tcl 命令/选项/路径补全。

    可识别 %tcl 前缀，并保留原始补全器作为非 Tcl 行的回退。
    """

    def __init__(self, original_completer: Completer | None = None):
        super().__init__()
        self.original = original_completer

    def get_completions(self, document: Document, complete_event: Any) -> Iterable[Completion]:
        text = document.text_before_cursor

        # 剥离 %tcl 前缀
        if text.strip().startswith("%tcl"):
            text = re.sub(r"^\s*%tcl\s*", "", text)

        # 不是 Tcl 行 → 委托给原始补全器
        if not _looks_like_tcl(text):
            if self.original is not None:
                yield from self.original.get_completions(document, complete_event)
            return

        words = text.split()
        at_end = text.endswith(" ")
        last = words[-1] if words and not at_end else ""

        # ---- CASE 1: 补全命令名（RainaSynth 命令 + Tcl 内建） ----
        if not words or (len(words) == 1 and not at_end):
            all_cmds = sorted(ALL_COMMANDS) + sorted(TCL_BUILTINS)
            for cmd in all_cmds:
                if cmd.startswith(last):
                    yield Completion(
                        cmd,
                        start_position=-len(last),
                        display=cmd,
                        display_meta=self._category(cmd),
                    )
            return

        cmd = words[0]
        if cmd not in ALL_COMMANDS and cmd not in TCL_BUILTINS:
            return

        info = TCL_COMMANDS.get(cmd, {})
        valid = set(info.get("options", []))
        switches = set(info.get("switch_options", []))

        # 已经用过的选项
        used: set[str] = set()
        i = 1
        while i < len(words):
            w = words[i]
            if w in valid:
                used.add(w)
                i += 2 if (w not in switches and i + 1 < len(words)) else 1
            else:
                i += 1

        if at_end:
            # ---- CASE 2a: 光标在末尾 → 建议可用选项 + 文件路径 ----
            for opt in sorted(valid - used):
                kind = "switch" if opt in switches else "option"
                yield Completion(opt, start_position=0, display=opt, display_meta=kind)
            for p in _file_completions():
                yield Completion(
                    p,
                    start_position=0,
                    display=os.path.basename(p) if os.path.isfile(p) else p + "/",
                    display_meta="file",
                )
        else:
            # ---- CASE 2b: 正在输入词中 ----
            prev = words[-2] if len(words) >= 2 else None

            if prev in valid and prev not in switches and prev in PATH_OPTIONS:
                # 上一个选项是路径选项，补全路径
                for p in _file_completions(last):
                    yield Completion(
                        p,
                        start_position=-len(last),
                        display=os.path.basename(p) if os.path.isfile(p) else p + "/",
                        display_meta="file",
                    )
            else:
                # 补全选项名 + 路径
                for opt in sorted(valid - used):
                    if opt.startswith(last):
                        kind = "switch" if opt in switches else "option"
                        yield Completion(
                            opt, start_position=-len(last), display=opt, display_meta=kind
                        )
                for p in _file_completions(last):
                    yield Completion(
                        p,
                        start_position=-len(last),
                        display=os.path.basename(p) if os.path.isfile(p) else p + "/",
                        display_meta="file",
                    )

    @staticmethod
    def _category(cmd: str) -> str:
        if cmd in TCL_BUILTINS:
            return "Tcl"
        for cat, cmds in COMMAND_CATEGORIES.items():
            if cmd in cmds:
                return cat
        return "RainaSynth"


# 命令 → 分类映射
COMMAND_CATEGORIES: dict[str, set[str]] = {
    "Config": {"flow_init", "db_init", "flow_exit", "flow_config"},
    "DB": {
        "idb_init",
        "tech_lef_init",
        "lef_init",
        "def_init",
        "verilog_init",
        "def_save",
        "lef_save",
        "netlist_save",
        "gds_save",
        "json_save",
        "aimp_random",
        "set_net",
        "merge_nets",
        "remove_except_pg_net",
        "clear_blockage",
        "idb_get",
        "delete_inst",
        "delete_net",
        "create_inst",
        "create_net",
        "place_instance",
    },
    "PDN": {
        "add_pdn_io",
        "global_net_connect",
        "place_pdn_port",
        "create_grid",
        "create_stripe",
        "connect_two_layer",
        "connect_macro_pdn",
        "connect_io_pin_to_pdn",
        "connect_pdn_stripe",
        "add_segment_stripe",
        "add_segment_via",
    },
    "Placer": {
        "run_placer",
        "run_filler",
        "run_incremental_flow",
        "run_incremental_lg",
        "placer_check_legality",
        "placer_report",
        "init_pl",
        "destroy_pl",
        "placer_run_mp",
        "placer_run_gp",
        "placer_run_lg",
        "placer_run_dp",
        "pl_config",
    },
    "CTS": {"run_cts", "cts_report", "cts_save_tree", "cts_config"},
    "Router": {
        "init_rt",
        "run_ert",
        "run_rt",
        "destroy_rt",
        "rt_clean_def",
        "rt_fix_fanout",
        "rt_get_congestion",
    },
    "STA": {
        "run_sta",
        "init_sta",
        "report_sta",
        "build_clock_tree",
        "set_design_workspace",
        "read_netlist",
        "read_lef_def",
        "read_liberty",
        "link_design",
        "read_spef",
        "read_sdc",
        "report_timing",
        "report_constraint",
        "def_to_verilog",
        "verilog_to_def",
        "get_libs",
    },
    "Power": {
        "run_power",
        "set_pwr_design_workspace",
        "report_power",
        "read_pg_spef",
        "report_ir_drop",
    },
    "TimingOpt": {
        "run_to",
        "run_to_drv",
        "run_to_drv_special_net",
        "run_to_hold",
        "run_to_setup",
        "run_to_buffering",
        "to_config",
    },
    "NetOpt": {"run_no_fixfanout", "run_no_fixIO", "no_config"},
    "DRC": {"check_def", "destroy_drc", "init_drc", "drc_cmp_violation", "run_drc", "save_drc"},
    "Eval": {"run_timing_eval", "run_wirelength_eval", "run_density_eval", "egr_config"},
    "Feature": {
        "feature_summary",
        "feature_tool",
        "feature_eval_map",
        "feature_route",
        "feature_route_read",
        "feature_cong_map",
    },
    "ECO": {"eco_repair_via"},
    "GUI": {
        "gui_start",
        "gui_show",
        "gui_hide",
        "gui_show_drc",
        "gui_show_cts",
        "gui_show_pl",
        "gui_show_graph",
        "capture_design",
    },
    "Report": {
        "report_db",
        "report_wirelength",
        "report_congestion",
        "report_route",
        "report_inst_distro",
        "report_prefixed_instance",
    },
    "Vectorization": {
        "layout_patchs",
        "layout_graph",
        "generate_vectors",
        "read_vectors_nets",
        "read_vectors_nets_patterns",
    },
    "PNP": {"run_pnp", "add_via1"},
    "Notification": {"init_notification"},
    "Contest": {"run_contest", "run_contest_evaluation"},
}


# =============================================================================
# 5. IPython 魔术命令 — %tcl
# =============================================================================


@magics_class
class TclMagics(Magics):
    """向 IPython 注册 %tcl 行魔术。"""

    def __init__(self, shell: Any) -> None:
        super().__init__(shell)  # type: ignore[no-untyped-call]
        if isinstance(shell, TerminalInteractiveShell):
            self._setup_completer(shell)

    @staticmethod
    def _setup_completer(shell: TerminalInteractiveShell) -> None:
        try:
            if shell.pt_app is not None:
                original = getattr(shell.pt_app, "completer", None)
                shell.pt_app.completer = TclCompleter(original_completer=original)
        except Exception:
            pass  # 非终端环境静默跳过

    @line_magic  # type: ignore[untyped-decorator]
    def tcl(self, line: str) -> None:
        """执行 RainaSynth Tcl 命令（支持变量/命令替换）。

        Tcl 内建:
          set var value     — 赋值变量
          puts text         — 打印
          expr expression   — 算术计算
          list_vars         — 列出所有变量（非 Tcl 内建，仅供调试）

        变量替换:
          $var    — 读取变量值

        命令替换:
          [command] — 执行命令并嵌入结果

        自动识别:
          输入 RainaSynth 命令时无需 %tcl 前缀（输入转换器会自动添加）。
        """
        try:
            result = _interp.execute(line)
        except TclError as e:
            print(f"Tcl 错误: {e}")
            return
        except Exception as e:
            print(f"错误: {e}")
            return

        # Log to agent context if an agent is available in the shell namespace
        agent = self.shell.user_ns.get("agent")  # type: ignore[attr-defined]
        if agent is not None and result is not None:
            try:
                agent.context.append({"role": "user", "content": f"[Tcl] {line}"})
                agent.context.append({"role": "system", "content": f"[Output] {result}"})
            except Exception:
                pass

        if result is not None and result != "":
            # 确保输出显示在 IPython 中
            try:
                from IPython.display import Pretty, display

                display(Pretty(str(result)))  # type: ignore[no-untyped-call]
            except ImportError:
                print(result)


# =============================================================================
# 6. 输入转换器 — 自动识别 Tcl 命令并添加 %tcl 前缀
# =============================================================================


def tcl_auto_transformer(line: str | list[str]) -> str | list[str]:
    """输入转换器：自动将 Tcl 命令转为 Python 代码调用 %tcl 魔法。

    不用 %tcl 前缀（因为 input_transformers_post 运行时魔数检测已过），
    改为生成合法的 Python 表达式，在代码中显式调用 run_line_magic。

    兼容 IPython 传入 str 或 list[str] 两种格式。
    """
    # IPython 的 input_transformers_post 可能传 str 或 list
    if isinstance(line, list):
        raw = line[0]
    else:
        raw = line

    stripped = raw.strip()

    # 跳过空行、系统命令、IPython 魔术、注释
    if not stripped or stripped[0] in ("%", "!", "?", "#", ";"):
        return line

    first = stripped.split()[0] if stripped.split() else ""
    if first in ALL_COMMANDS or first in TCL_BUILTINS:
        # 用 repr() 安全地转义为 Python 字符串字面量
        safe_cmd = repr(stripped)
        modified = 'get_ipython().run_line_magic("tcl", ' + safe_cmd + ")"
        if isinstance(line, list):
            return [modified] + line[1:]
        return modified

    return line


# =============================================================================
# 7. IPython 扩展加载入口
# =============================================================================


def load_ipython_extension(ipython: InteractiveShell) -> None:
    """加载 Tcl 模拟扩展。

    用法（在 IPython 中）:
      %load_ext tcl_test

    或从 Python 脚本:
      from tcl_test import load_ipython_extension
      load_ipython_extension(get_ipython())
    """
    ipython.register_magics(TclMagics)
    ipython.input_transformers_post.append(tcl_auto_transformer)

    n = len(ALL_COMMANDS)
    print("[OK] Tcl mock extension loaded")
    print("   - Direct Tcl command:  read_liberty -path ./file.lib")
    print("   - Or use %tcl:         %tcl read_liberty -path ./file.lib")
    print("   - Tab completion:      commands / options / file paths")
    print("   - Variable subst:      set d ./data ; read_liberty -path $d")
    print("   - Command subst:       set x [expr 1 + 2]")
    print(f"   - Registered Tcl commands: {n}")
