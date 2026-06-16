Features
========

Natural Language Interface
--------------------------

Describe what you want to do in plain English, and EDAI's LLM agent
translates it into the appropriate EDA commands.

::

    >>  set up the design with liberty file and LEF/TECH files
    >>  initialize the floorplan with aspect ratio 1.0
    >>  run placement and show me the congestion report

The agent maintains conversation context, so you can refine requests
iteratively just as you would with a colleague.

Built-in Tcl Interpreter
------------------------

EDAI comes with a Tcl interpreter that understands **184 EDA commands**
organized across 19 subsystems. You can type Tcl commands directly
without any special prefix:

::

    >>  read_liberty -path ./lib/slow.lib
    >>  read_sdc -path ./constraints/top.sdc
    >>  run_placer -max_density 0.7

The interpreter supports Tcl variable substitution (``$var``),
command substitution (``[command]``), and built-in commands such as
``set``, ``puts``, and ``expr``.

Simulation Mode
---------------

No EDA tool license? No problem. EDAI includes a simulation backend
that produces realistic output for all supported commands. This lets
you:

* **Prototype and debug flows** without touching licensed tools.
* **Learn the tool command set** interactively.
* **Demonstrate and teach** in environments without tool access.
* **Test flow scripts** before running them on real tools.

When connected to a real EDA tool backend, the simulation layer is
transparently replaced with live execution.

IPython Shell
-------------

The full IPython experience is available alongside EDA commands:

* Python REPL with history, tab completion, and magic commands.
* Rich display of Python objects (DataFrames, arrays, plots).
* Access to the Tcl interpreter state from Python.
* Ability to write Python scripts that mix EDA commands with
  analysis code.

You can query simulation results, compute metrics, or generate
reports — all within the same terminal session.

180+ Commands Across the Full EDA Flow
---------------------------------------

The built-in command database covers the major stages of a digital
design flow:

+-------------------+---------------------------------------------+
| Subsystem         | Example Commands                            |
+===================+=============================================+
| **Config**        | ``flow_init``, ``db_init``, ``flow_config`` |
+-------------------+---------------------------------------------+
| **Database**      | ``idb_init``, ``tech_lef_init``,            |
|                   | ``def_init``, ``verilog_init``              |
+-------------------+---------------------------------------------+
| **Floorplan**     | ``floorplan_init``, ``set_die_area``        |
+-------------------+---------------------------------------------+
| **PDN**           | ``create_grid``, ``create_stripe``,         |
|                   | ``connect_macro_pdn``                       |
+-------------------+---------------------------------------------+
| **Placement**     | ``run_placer``, ``run_filler``,             |
|                   | ``placer_run_gp``, ``placer_run_dp``        |
+-------------------+---------------------------------------------+
| **CTS**           | ``run_cts``, ``cts_report``                 |
+-------------------+---------------------------------------------+
| **Routing**       | ``run_rt``, ``run_ert``,                    |
|                   | ``rt_get_congestion``                       |
+-------------------+---------------------------------------------+
| **STA**           | ``run_sta``, ``read_liberty``,              |
|                   | ``read_sdc``, ``report_timing``             |
+-------------------+---------------------------------------------+
| **Power Analysis**| ``run_power``, ``report_power``,            |
|                   | ``report_ir_drop``                          |
+-------------------+---------------------------------------------+
| **Timing Opt**    | ``run_to``, ``run_to_setup``,               |
|                   | ``run_to_hold``                             |
+-------------------+---------------------------------------------+
| **DRC**           | ``run_drc``, ``check_def``, ``save_drc``    |
+-------------------+---------------------------------------------+
| **ECO**           | ``eco_repair_via``                          |
+-------------------+---------------------------------------------+
| **GUI**           | ``gui_start``, ``gui_show``,                |
|                   | ``capture_design``                          |
+-------------------+---------------------------------------------+
| **Report**        | ``report_db``, ``report_wirelength``,       |
|                   | ``report_congestion``                       |
+-------------------+---------------------------------------------+

Tab Completion for Tcl Commands
-------------------------------

When typing in Tcl mode, you get context-aware tab completion:

* Command name completion — type ``pla`` + :kbd:`Tab` → ``run_placer``.
* Option completion — after a command, :kbd:`Tab` shows available
  flags like ``-path``, ``-max_density``.
* File path completion — for options expecting file paths.
* Duplicate option prevention — already-used options are filtered
  out.

Configurable LLM Backend
------------------------

EDAI works with any OpenAI-compatible API. Configure the model,
endpoint, and API key through environment variables:

* ``LLM_BASE_URL`` — API endpoint (defaults to DeepSeek).
* ``LLM_MODEL_ID`` — model identifier.
* ``LLM_API_KEY`` — your API key.

This makes it easy to switch between cloud providers or use a
locally-hosted model.

Extensible Tool System
----------------------

Behind the scenes, EDAI has a plugin-style tool architecture. The
tool system supports:

* **Bash execution** — run arbitrary shell commands.
* **REPL interaction** — interact with persistent subprocesses
  (Python, Tcl, or custom interpreters).
* **Named interpreters** — spawn and manage long-running language
  backends.

New tools can be added without modifying core code, making EDAI
adaptable to different EDA toolchains and workflows.
